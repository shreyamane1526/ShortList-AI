"""
Email service for sending emails via SendGrid or SMTP.
Supports both SendGrid API and SMTP (Gmail, etc.)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
) -> bool:
    """
    Send an email using SendGrid API or SMTP.
    
    Priority:
    1. Try SendGrid if SENDGRID_API_KEY is set
    2. Fall back to SMTP if SMTP_* vars are set
    3. Log error if neither is configured
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body_html: HTML body content
        body_text: Plain text body (optional, will strip HTML if not provided)
        from_email: Sender email (defaults to env var)
        from_name: Sender name (defaults to "ShortlistAI")
    
    Returns:
        True if email sent successfully, False otherwise
    """
    
    # Default sender
    if not from_email:
        from_email = os.getenv("FROM_EMAIL", "noreply@shortlistai.com")
    if not from_name:
        from_name = os.getenv("FROM_NAME", "ShortlistAI")
    
    # Try SendGrid first
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
    if sendgrid_api_key:
        return _send_via_sendgrid(
            to_email=to_email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            from_email=from_email,
            from_name=from_name,
            api_key=sendgrid_api_key,
        )
    
    # Fall back to SMTP
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    
    if smtp_host and smtp_port and smtp_user and smtp_pass:
        return _send_via_smtp(
            to_email=to_email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            from_email=from_email,
            from_name=from_name,
            smtp_host=smtp_host,
            smtp_port=int(smtp_port),
            smtp_user=smtp_user,
            smtp_pass=smtp_pass,
        )
    
    # No email service configured
    logger.warning(
        "Email service not configured. Set SENDGRID_API_KEY or SMTP_* environment variables. "
        f"Would have sent email to {to_email} with subject: {subject}"
    )
    return False


def _send_via_sendgrid(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str],
    from_email: str,
    from_name: str,
    api_key: str,
) -> bool:
    """Send email via SendGrid API."""
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content
        
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        
        from_email_obj = Email(from_email, from_name)
        to_email_obj = To(to_email)
        
        # Use HTML content, fall back to text
        if body_html:
            content = Content("text/html", body_html)
        else:
            content = Content("text/plain", body_text or "")
        
        mail = Mail(from_email_obj, to_email_obj, subject, content)
        
        # Add plain text version if HTML is provided
        if body_html and body_text:
            mail.add_content(Content("text/plain", body_text))
        
        response = sg.send(mail)
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Email sent successfully via SendGrid to {to_email}")
            return True
        else:
            logger.error(f"SendGrid API error: {response.status_code} - {response.body}")
            return False
            
    except ImportError:
        logger.error("SendGrid library not installed. Run: pip install sendgrid")
        return False
    except Exception as e:
        logger.error(f"Failed to send email via SendGrid: {e}")
        return False


def _send_via_smtp(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str],
    from_email: str,
    from_name: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
) -> bool:
    """Send email via SMTP (Gmail, etc.)."""
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        
        # Add plain text version
        if body_text:
            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)
        
        # Add HTML version
        if body_html:
            part2 = MIMEText(body_html, "html")
            msg.attach(part2)
        
        # Connect to SMTP server
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_email, msg.as_string())
        
        logger.info(f"Email sent successfully via SMTP to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email via SMTP: {e}")
        return False


def send_message_notification(
    recipient_email: str,
    recipient_name: str,
    sender_name: str,
    message_subject: str,
    message_body: str,
    portal_url: str = "https://shortlistai.com",
) -> bool:
    """
    Send a notification email when a user receives a new message.
    
    Args:
        recipient_email: Email of the message recipient
        recipient_name: Name of the recipient
        sender_name: Name of the message sender
        message_subject: Subject of the message
        message_body: Body of the message
        portal_url: URL to the portal (defaults to env var or shortlistai.com)
    
    Returns:
        True if email sent successfully
    """
    
    portal_url = os.getenv("PORTAL_URL", portal_url)
    messages_url = f"{portal_url}/messages"
    
    # HTML email template
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">ShortlistAI</h1>
        </div>
        
        <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px;">
            <h2 style="color: #1f2937; margin-top: 0;">New Message from {sender_name}</h2>
            
            <p style="color: #4b5563; font-size: 16px;">Hi {recipient_name},</p>
            
            <p style="color: #4b5563; font-size: 16px;">You have received a new message on ShortlistAI:</p>
            
            <div style="background: white; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0 0 10px 0; font-weight: 600; color: #1f2937;">Subject: {message_subject}</p>
                <p style="margin: 0; color: #4b5563; white-space: pre-wrap;">{message_body[:500]}{"..." if len(message_body) > 500 else ""}</p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{messages_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">
                    View Message
                </a>
            </div>
            
            <p style="color: #6b7280; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                This email was sent because you have an account on ShortlistAI. If you did not expect this message, please ignore it.
            </p>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
            <p>© 2026 ShortlistAI. All rights reserved.</p>
            <p>
                <a href="{portal_url}" style="color: #667eea; text-decoration: none;">Visit Portal</a> · 
                <a href="{portal_url}/settings" style="color: #667eea; text-decoration: none;">Settings</a>
            </p>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_body = f"""
    ShortlistAI - New Message
    
    Hi {recipient_name},
    
    You have received a new message from {sender_name}:
    
    Subject: {message_subject}
    
    {message_body[:500]}{"..." if len(message_body) > 500 else ""}
    
    View and reply to this message: {messages_url}
    
    ---
    © 2026 ShortlistAI
    """
    
    return send_email(
        to_email=recipient_email,
        subject=f"New message from {sender_name}",
        body_html=html_body,
        body_text=text_body,
    )
