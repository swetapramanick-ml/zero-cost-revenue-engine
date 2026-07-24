import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from db import get_setting

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email using standard SMTP.
    Retrieves SMTP settings dynamically from DB/environment.
    """
    host = get_setting("SMTP_HOST")
    port_str = get_setting("SMTP_PORT")
    user = get_setting("SMTP_USER")
    password = get_setting("SMTP_PASSWORD")
    from_email = get_setting("SMTP_FROM_EMAIL")
    from_name = get_setting("SMTP_FROM_NAME", "Zero-Cost Revenue Engine")

    if not all([host, port_str, user, password, from_email]):
        raise ValueError("SMTP configuration is incomplete. Please set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM_EMAIL.")

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
