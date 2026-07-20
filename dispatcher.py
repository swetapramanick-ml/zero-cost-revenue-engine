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

    try:
        # Connect to server
        if port == 465:
            # SSL
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            # STARTTLS for 587 or other ports
            server = smtplib.SMTP(host, port, timeout=15)
            server.ehlo()
            if server.has_extn("STARTTLS"):
                server.starttls()
                server.ehlo()
                
        # Login and send
        server.login(user, password)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        raise Exception(f"SMTP Error: {str(e)}")

if __name__ == "__main__":
    # Test script if called directly
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
        
    print("SMTP dispatcher module loaded. Ready to dispatch.")
