import socket
import smtplib
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from db import get_setting

# Monkey-patch socket.getaddrinfo to always use IPv4 (AF_INET)
# This fixes the "[Errno -9] Address family for hostname not supported" error on platforms like Render that have IPv6 issues.
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email using standard SMTP or HTTP API fallback.
    Retrieves settings dynamically from DB/environment.
    """
    host = get_setting("SMTP_HOST", "")
    port_str = get_setting("SMTP_PORT", "587")
    user = get_setting("SMTP_USER", "")
    password = get_setting("SMTP_PASSWORD", "")
    from_email = get_setting("SMTP_FROM_EMAIL", "")
    from_name = get_setting("SMTP_FROM_NAME", "Zero-Cost Revenue Engine")

    if not all([host, password, from_email]):
        raise ValueError("Email configuration is incomplete. Please set Host, Password/API Key, and From Email.")

    # 1. HTTP API Fallbacks (Bypasses Render SMTP port blocking)
    host_lower = host.lower()
    
    if "api.sendgrid.com" in host_lower:
        headers = {"Authorization": f"Bearer {password}", "Content-Type": "application/json"}
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email, "name": from_name},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}]
        }
        r = httpx.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers, timeout=15)
        if not r.is_success:
            raise Exception(f"SendGrid API Error: {r.text}")
        return True

    elif "api.brevo.com" in host_lower or "api.sendinblue.com" in host_lower:
        headers = {"api-key": password, "Content-Type": "application/json", "accept": "application/json"}
        payload = {
            "sender": {"name": from_name, "email": from_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "textContent": body
        }
        r = httpx.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=15)
        if not r.is_success:
            raise Exception(f"Brevo API Error: {r.text}")
        return True

    elif "api.resend.com" in host_lower:
        headers = {"Authorization": f"Bearer {password}", "Content-Type": "application/json"}
        payload = {
            "from": f"{from_name} <{from_email}>",
            "to": [to_email],
            "subject": subject,
            "text": body
        }
        r = httpx.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=15)
        if not r.is_success:
            raise Exception(f"Resend API Error: {r.text}")
        return True

    # 2. Standard SMTP Fallback
    try:
        port = int(port_str)
    except ValueError:
        raise ValueError(f"Invalid SMTP port: {port_str}. Must be an integer.")

    # Create message
    msg = MIMEMultipart()
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    
    # Body
    msg.attach(MIMEText(body, "plain"))

    server = None
    try:
        # Validate host resolution before SMTP connect
        try:
            socket.getaddrinfo(host, port)
        except socket.gaierror as e:
            raise Exception(f"SMTP Error: cannot resolve host '{host}'. Check SMTP_HOST and network connectivity. {e}")

        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=15, source_address=("0.0.0.0", 0))
        else:
            server = smtplib.SMTP(host, port, timeout=15, source_address=("0.0.0.0", 0))
            server.ehlo()
            if server.has_extn("STARTTLS"):
                server.starttls()
                server.ehlo()

        server.login(user, password)
        server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        raise Exception("SMTP Authentication failed. Check SMTP_USER and SMTP_PASSWORD.")
    except (socket.timeout, socket.gaierror, OSError) as e:
        raise Exception(f"SMTP Network Error connecting to {host}:{port} - {str(e)}. Verify network access, firewall rules, and SMTP host/port settings.")
    except smtplib.SMTPException as e:
        raise Exception(f"SMTP protocol error: {str(e)}")
    except Exception as e:
        raise Exception(f"SMTP Error: {str(e)}")
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                server.close()

if __name__ == "__main__":
    # Test script if called directly
    try:
        # optional dependency: python-dotenv may not be installed in all environments
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        # provide a no-op fallback so module can be imported without dotenv
        def load_dotenv():
            return None
    # call (real or no-op) to load environment variables if available
    load_dotenv()
        
    print("SMTP dispatcher module loaded. Ready to dispatch.")
