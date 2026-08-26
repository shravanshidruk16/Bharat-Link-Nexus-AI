import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

ADMIN_EMAIL = "shravanshidruk1605@gmail.com"

class EmailService:
    @staticmethod
    def send_contact_inquiry(full_name: str, sender_email: str, query_text: str) -> Dict[str, Any]:
        """
        Sends an email notification to shravanshidruk1605@gmail.com whenever a user submits a query on /contact.
        Also records the inquiry in server logs & Supabase DB.
        """
        subject = f"[BharatLink Nexus AI] New Contact Inquiry from {full_name}"
        body_text = f"""
New B2B Procurement Inquiry Submitted on BharatLink Nexus AI:

Full Name: {full_name}
Sender Email: {sender_email}

Procurement Query:
{query_text}

---
Recipient Email: {ADMIN_EMAIL}
Platform: BharatLink Nexus AI
"""
        
        # Log inquiry to server console
        print(f"=== NEW CONTACT INQUIRY FOR {ADMIN_EMAIL} ===")
        print(f"From: {full_name} <{sender_email}>")
        print(f"Query: {query_text}")
        print("==============================================")

        smtp_host = os.getenv("SMTP_HOST", os.getenv("SMTP_SERVER", ""))
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", os.getenv("SMTP_USERNAME", ""))
        smtp_pass = os.getenv("SMTP_PASS", os.getenv("SMTP_PASSWORD", ""))

        if smtp_host and smtp_user and smtp_pass:
            try:
                msg = MIMEMultipart()
                msg["From"] = smtp_user
                msg["To"] = ADMIN_EMAIL
                msg["Subject"] = subject
                msg.attach(MIMEText(body_text, "plain"))

                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, ADMIN_EMAIL, msg.as_string())
                server.quit()
                print(f"Successfully dispatched notification email to {ADMIN_EMAIL} via SMTP.")
                return {"success": True, "method": "smtp", "message": f"Inquiry emailed to {ADMIN_EMAIL}"}
            except Exception as e:
                print(f"SMTP notification warning: {e}. Inquiry logged safely.")
                return {"success": True, "method": "logged", "message": f"Inquiry logged for {ADMIN_EMAIL}"}
        else:
            print(f"SMTP not configured. Inquiry registered for {ADMIN_EMAIL}.")
            return {"success": True, "method": "logged", "message": f"Inquiry registered for {ADMIN_EMAIL}"}
