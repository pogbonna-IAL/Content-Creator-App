"""
Email Provider Service
Adapter pattern for sending emails (dev logging vs production SMTP)
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Email message structure"""
    to: str
    subject: str
    html_body: str
    text_body: Optional[str] = None
    from_address: Optional[str] = None


class EmailProvider(ABC):
    """
    Abstract email provider interface
    
    Implementations:
    - DevEmailProvider: Logs emails to console (development)
    - SMTPEmailProvider: Sends via SMTP (production)
    """
    
    @abstractmethod
    def send(self, message: EmailMessage) -> bool:
        """
        Send an email
        
        Args:
            message: Email message to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if email provider is available/configured
        
        Returns:
            True if ready to send emails
        """
        pass


class DevEmailProvider(EmailProvider):
    """
    Development email provider - logs emails instead of sending
    
    Perfect for local development and testing
    """
    
    def send(self, message: EmailMessage) -> bool:
        """Log email to console instead of sending"""
        logger.info("=" * 60)
        logger.info("📧 EMAIL (DEV MODE - NOT ACTUALLY SENT)")
        logger.info("=" * 60)
        logger.info(f"To: {message.to}")
        logger.info(f"From: {message.from_address or 'noreply@example.com'}")
        logger.info(f"Subject: {message.subject}")
        logger.info("-" * 60)
        logger.info(f"HTML Body:\n{message.html_body}")
        if message.text_body:
            logger.info("-" * 60)
            logger.info(f"Text Body:\n{message.text_body}")
        logger.info("=" * 60)
        return True
    
    def is_available(self) -> bool:
        """Always available"""
        return True


class SMTPEmailProvider(EmailProvider):
    """
    SMTP email provider for production
    
    Configured via environment variables:
    - SMTP_HOST
    - SMTP_PORT
    - SMTP_USER
    - SMTP_PASSWORD
    - SMTP_FROM_ADDRESS
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_address: str,
        use_tls: bool = True
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_address = from_address
        self.use_tls = use_tls
    
    def send(self, message: EmailMessage) -> bool:
        """Send email via SMTP"""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = message.subject
            msg['From'] = message.from_address or self.from_address
            msg['To'] = message.to
            
            # Add text and HTML parts
            if message.text_body:
                part1 = MIMEText(message.text_body, 'plain')
                msg.attach(part1)
            
            part2 = MIMEText(message.html_body, 'html')
            msg.attach(part2)
            
            # Send email
            if self.use_tls:
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.host, self.port)
            
            server.login(self.user, self.password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✓ Email sent to {message.to}: {message.subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {message.to}: {e}", exc_info=True)
            return False
    
    def is_available(self) -> bool:
        """Check if SMTP is configured"""
        return all([
            self.host,
            self.port,
            self.user,
            self.password,
            self.from_address
        ])


# Singleton instance
_email_provider: Optional[EmailProvider] = None


def get_email_provider() -> EmailProvider:
    """
    Get or create email provider singleton
    
    Returns DevEmailProvider in development, SMTPEmailProvider in production
    
    Returns:
        EmailProvider instance
    """
    global _email_provider
    
    if _email_provider is None:
        import os
        from ..config import config
        
        # Check if SMTP is configured
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port_str = os.getenv("SMTP_PORT", "587")
        try:
            smtp_port = int(smtp_port_str)
        except ValueError:
            logger.warning(f"Invalid SMTP_PORT value: {smtp_port_str}, using default 587")
            smtp_port = 587
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from = os.getenv("SMTP_FROM_ADDRESS", "noreply@example.com")
        
        # Check which environment variables are missing
        missing_vars = []
        if not smtp_host:
            missing_vars.append("SMTP_HOST")
        if not smtp_user:
            missing_vars.append("SMTP_USER")
        if not smtp_password:
            missing_vars.append("SMTP_PASSWORD")
        
        if smtp_host and smtp_user and smtp_password:
            # Production: Use SMTP
            logger.info(f"✓ Email provider: SMTP ({smtp_host}:{smtp_port})")
            logger.info(f"  From address: {smtp_from}")
            _email_provider = SMTPEmailProvider(
                host=smtp_host,
                port=smtp_port,
                user=smtp_user,
                password=smtp_password,
                from_address=smtp_from,
                use_tls=True
            )
        else:
            # Development: Use dev logger
            # Use info level instead of warning - this is expected in development
            logger.info("📧 Email provider: DevEmailProvider (logs to console only - expected in development)")
            if missing_vars:
                logger.info(f"  Missing SMTP configuration: {', '.join(missing_vars)}")
                logger.info("  To enable email sending in production, set these environment variables:")
                logger.info("    - SMTP_HOST (e.g., smtp.gmail.com)")
                logger.info("    - SMTP_PORT (e.g., 587)")
                logger.info("    - SMTP_USER (your email)")
                logger.info("    - SMTP_PASSWORD (your email password or app password)")
                logger.info("    - SMTP_FROM_ADDRESS (optional, defaults to noreply@example.com)")
            _email_provider = DevEmailProvider()
    
    return _email_provider


def send_verification_email(email: str, verification_url: str) -> bool:
    """
    Send email verification email
    
    Args:
        email: User's email address
        verification_url: Full verification URL with token
    
    Returns:
        True if sent successfully
    """
    provider = get_email_provider()
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ 
                display: inline-block; 
                padding: 12px 24px; 
                background-color: #3b82f6; 
                color: white; 
                text-decoration: none; 
                border-radius: 5px; 
                margin: 20px 0;
            }}
            .footer {{ margin-top: 40px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Verify Your Email Address</h2>
            <p>Thank you for signing up! Please verify your email address to activate your account.</p>
            <p>Click the button below to verify your email:</p>
            <a href="{verification_url}" class="button">Verify Email Address</a>
            <p>Or copy and paste this link into your browser:</p>
            <p><a href="{verification_url}">{verification_url}</a></p>
            <div class="footer">
                <p>If you didn't create an account, you can safely ignore this email.</p>
                <p>This link will expire in 24 hours.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    Verify Your Email Address
    
    Thank you for signing up! Please verify your email address to activate your account.
    
    Click the link below to verify your email:
    {verification_url}
    
    If you didn't create an account, you can safely ignore this email.
    This link will expire in 24 hours.
    """
    
    message = EmailMessage(
        to=email,
        subject="Verify Your Email Address",
        html_body=html_body,
        text_body=text_body
    )
    
    return provider.send(message)

