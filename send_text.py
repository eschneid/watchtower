import argparse
import smtplib
import sys
from email.message import EmailMessage

# Import configuration
try:
    from config import SMTP_SERVER, SMTP_PORT, EMAIL_FROM, EMAIL_PASSWORD, SMS_RECIPIENTS, SMS_SEND_MODE
except ImportError:
    print("ERROR: config.py not found!")
    print("Please copy .env.example to .env and fill in your SMS credentials.")
    exit(1)

def send_text(message):
    """Send SMS via email gateway to one or more recipients"""
    print("📩 Sending text message...")
    
    # Handle single number or comma-separated list
    if isinstance(SMS_RECIPIENTS, str):
        recipients = [num.strip() for num in SMS_RECIPIENTS.split(',') if num.strip()]
    elif isinstance(SMS_RECIPIENTS, list):
        recipients = SMS_RECIPIENTS
    else:
        recipients = [SMS_RECIPIENTS]
    
    if not recipients:
        print("❌ No recipients configured")
        return
    
    send_mode = SMS_SEND_MODE.lower() if SMS_SEND_MODE else "individual"
    
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        
        if send_mode == "group":
            # Group mode: All recipients see each other (like group text)
            msg = EmailMessage()
            msg["From"] = EMAIL_FROM
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = ""
            msg.set_content(message)
            smtp.send_message(msg)
            print(f"✅ Text sent to {len(recipients)} recipient(s) [GROUP MODE - all visible]")
        
        else:
            # Individual mode: Send separately (BCC-style, recipients hidden)
            for recipient in recipients:
                msg = EmailMessage()
                msg["From"] = EMAIL_FROM
                msg["To"] = recipient
                msg["Subject"] = ""
                msg.set_content(message)
                smtp.send_message(msg)
            print(f"✅ Text sent to {len(recipients)} recipient(s) [INDIVIDUAL MODE - hidden from each other]")

def main():
    print("📩 Preparing to send text message...")
    
    parser = argparse.ArgumentParser(
        description="Send an SMS via email-to-SMS gateway (supports multiple carriers)"
    )
    parser.add_argument(
        "message",
        nargs="?",
        help="Text message to send (optional if piping from stdin)"
    )
    args = parser.parse_args()
    
    if args.message:
        message = args.message
    else:
        message = sys.stdin.read().strip()
    
    if not message:
        print("❌ No message provided", file=sys.stderr)
        sys.exit(1)
    
    # Keep SMS short
    message = message[:160]
    
    send_text(message)

if __name__ == "__main__":
    main()