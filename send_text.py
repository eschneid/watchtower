import argparse
import smtplib
import sys
from email.message import EmailMessage

# ================= CONFIG =================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

EMAIL_FROM = ""
EMAIL_PASSWORD = ""
VERIZON_NUMBER = "######@vtext.com"

# =========================================

def send_text(message):
    #debug 
    print("📩 Sending text message...")

    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = VERIZON_NUMBER
    msg["Subject"] = ""   # blank = cleaner SMS
    msg.set_content(message)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.send_message(msg)

    print('Sent...')


def main():

    # debug
    print("📩 Preparing to send text message...")

    parser = argparse.ArgumentParser(
        description="Send an SMS via Verizon email gateway"
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
    print("✅ Text sent")


if __name__ == "__main__":
    main()

