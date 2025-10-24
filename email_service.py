"""
Enhanced email service for sending all types of emails via SMTP.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import config
from models import Recipe

logger = logging.getLogger(__name__)


class EmailService:
    """Handles all email operations via SMTP."""
    
    def __init__(self):
        """Initialize email service with configuration."""
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.username = config.SMTP_USERNAME
        self.password = config.SMTP_PASSWORD
        self.use_tls = config.SMTP_USE_TLS
        self.sender_email = config.SENDER_EMAIL
        self.sender_name = config.SENDER_NAME
        self.base_url = getattr(config, 'BASE_URL', 'http://localhost:5000')
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.smtp_server and self.username and self.password and self.sender_email)
    
    # ============================================================================
    # CORE EMAIL SENDING METHOD
    # ============================================================================
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str = "",
        text_content: str = "",
        to_name: str = ""
    ) -> tuple[bool, str]:
        """
        Send any email with HTML and text content.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email content
            text_content: Plain text email content
            to_name: Optional recipient name
        
        Returns:
            (success, error_message)
        """
        if not self.is_configured():
            error_msg = "Email service is not configured. Please set SMTP environment variables."
            logger.error(error_msg)
            return False, error_msg
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            
            if to_name:
                msg['To'] = f"{to_name} <{to_email}>"
            else:
                msg['To'] = to_email
            
            # Add HTML content if provided
            if html_content:
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
            
            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Send email
            logger.info(f"Connecting to SMTP server {self.smtp_server}:{self.smtp_port}")
            
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Successfully sent email to {to_email}")
            return True, ""
            
        except smtplib.SMTPAuthenticationError:
            error_msg = "SMTP authentication failed. Check your username and password."
            logger.error(error_msg)
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error sending email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    # ============================================================================
    # SPECIALIZED EMAIL METHODS
    # ============================================================================
    
    def send_verification_email(
        self,
        user_email: str,
        user_name: str,
        verification_token: str
    ) -> tuple[bool, str]:
        """Send email verification link to user."""
        verification_url = f"{self.base_url}/verify-email/{verification_token}"
        
        subject = "Verify Your Recipe Editor Account"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f8f9fa;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #3498db;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 0.9em;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Welcome to Recipe Editor!</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                <p>Thank you for registering with Recipe Editor. To complete your registration and start using your account, please verify your email address by clicking the button below:</p>
                
                <div style="text-align: center;">
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </div>
                
                <p><strong>Important:</strong> This verification link will expire in 24 hours.</p>
                
                <p>If you didn't create this account, please ignore this email.</p>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background-color: #e9ecef; padding: 10px; border-radius: 3px;">
                    {verification_url}
                </p>
            </div>
            <div class="footer">
                <p>This email was sent from Recipe Editor</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Recipe Editor!
        
        Hello {user_name}!
        
        Thank you for registering with Recipe Editor. To complete your registration and start using your account, please verify your email address by visiting this link:
        
        {verification_url}
        
        Important: This verification link will expire in 24 hours.
        
        If you didn't create this account, please ignore this email.
        
        ---
        This email was sent from Recipe Editor
        """
        
        return self.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            to_name=user_name
        )
    
    def send_welcome_email(
        self,
        user_email: str,
        user_name: str
    ) -> tuple[bool, str]:
        """Send welcome email after successful verification."""
        subject = "Welcome to Recipe Editor - Account Verified!"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #27ae60;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f8f9fa;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #3498db;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Account Verified!</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                <p>Congratulations! Your Recipe Editor account has been successfully verified and is now active.</p>
                
                <h3>What you can do now:</h3>
                <ul>
                    <li>Create and manage your personal recipe collection</li>
                    <li>Import recipes from URLs, text files, or PDFs using AI</li>
                    <li>Organize recipes with custom tags</li>
                    <li>Share recipes with friends and family</li>
                    <li>Print recipes in a beautiful format</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="{self.base_url}/login" class="button">Log In to Recipe Editor</a>
                </div>
                
                <p>Happy cooking!</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Account Verified!
        
        Hello {user_name}!
        
        Congratulations! Your Recipe Editor account has been successfully verified and is now active.
        
        What you can do now:
        - Create and manage your personal recipe collection
        - Import recipes from URLs, text files, or PDFs using AI
        - Organize recipes with custom tags
        - Share recipes with friends and family
        - Print recipes in a beautiful format
        
        Log in to Recipe Editor: {self.base_url}/login
        
        Happy cooking!
        """
        
        return self.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            to_name=user_name
        )
    
    def send_password_reset_email(
        self,
        user_email: str,
        user_name: str,
        reset_token: str
    ) -> tuple[bool, str]:
        """Send password reset email to user."""
        reset_url = f"{self.base_url}/reset-password/{reset_token}"
        
        subject = "Reset Your Recipe Editor Password"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #e74c3c;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f8f9fa;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #e74c3c;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                <p>We received a request to reset your password for your Recipe Editor account.</p>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </div>
                
                <div class="warning">
                    <strong>Important:</strong> This password reset link will expire in 1 hour for security reasons.
                </div>
                
                <p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background-color: #e9ecef; padding: 10px; border-radius: 3px;">
                    {reset_url}
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request
        
        Hello {user_name}!
        
        We received a request to reset your password for your Recipe Editor account.
        
        To reset your password, visit this link:
        {reset_url}
        
        Important: This password reset link will expire in 1 hour for security reasons.
        
        If you didn't request a password reset, please ignore this email. Your password will remain unchanged.
        
        ---
        This email was sent from Recipe Editor
        """
        
        return self.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            to_name=user_name
        )
    
    def send_notification_email(
        self,
        user_email: str,
        subject: str,
        message: str,
        user_name: str = ""
    ) -> tuple[bool, str]:
        """Send general notification email to user."""
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .content {{
                    background-color: #f8f9fa;
                    padding: 30px;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="content">
                <h2>Hello {user_name if user_name else 'User'}!</h2>
                <p>{message}</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hello {user_name if user_name else 'User'}!
        
        {message}
        """
        
        return self.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            to_name=user_name
        )
    
    # ============================================================================
    # RECIPE EMAIL METHODS (EXISTING)
    # ============================================================================
    
    def format_recipe_email(self, recipe: Recipe, custom_message: str = "") -> str:
        """Format recipe as HTML email content."""
        html = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 25px;
                    border-bottom: 1px solid #bdc3c7;
                    padding-bottom: 5px;
                }}
                .custom-message {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-left: 4px solid #3498db;
                    margin-bottom: 20px;
                    font-style: italic;
                }}
                .ingredient {{
                    margin: 5px 0;
                    padding-left: 20px;
                }}
                .instructions {{
                    white-space: pre-wrap;
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                }}
                .notes {{
                    background-color: #fff9e6;
                    padding: 15px;
                    border-left: 4px solid #f39c12;
                    margin-top: 20px;
                }}
                .tags {{
                    margin-top: 20px;
                }}
                .tag {{
                    display: inline-block;
                    background-color: #3498db;
                    color: white;
                    padding: 5px 12px;
                    border-radius: 15px;
                    margin-right: 8px;
                    font-size: 0.9em;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #bdc3c7;
                    font-size: 0.9em;
                    color: #7f8c8d;
                    text-align: center;
                }}
                .source {{
                    background-color: #e8f4f8;
                    padding: 12px;
                    border-left: 4px solid #3498db;
                    margin-bottom: 20px;
                    font-size: 0.95em;
                }}
            </style>
        </head>
        <body>
            <h1>{recipe.name}</h1>
        """
        
        # Source information
        if recipe.source and recipe.source.get('name'):
            html += '<div class="source">'
            html += '<strong>Source:</strong> '
            html += recipe.source['name']
            if recipe.source.get('author'):
                html += f" ({recipe.source['author']})"
            if recipe.source.get('issue'):
                html += f" - {recipe.source['issue']}"
            if recipe.source.get('url'):
                html += f'<br><a href="{recipe.source["url"]}">{recipe.source["url"]}</a>'
            html += '</div>'
        
        if custom_message:
            html += f"""
            <div class="custom-message">
                {custom_message}
            </div>
            """
        
        # Ingredients
        html += """
            <h2>Ingredients</h2>
            <div class="ingredients">
        """
        for ing in recipe.ingredients:
            html += f'<div class="ingredient">• {str(ing)}</div>\n'
        html += "</div>"
        
        # Instructions
        if recipe.instructions:
            html += f"""
            <h2>Instructions</h2>
            <div class="instructions">{recipe.instructions}</div>
            """
        
        # Notes
        if recipe.notes:
            html += f"""
            <div class="notes">
                <strong>Notes:</strong><br>
                {recipe.notes}
            </div>
            """
        
        # Tags
        if recipe.tags:
            html += """
            <div class="tags">
                <strong>Tags:</strong><br>
            """
            for tag in recipe.tags:
                html += f'<span class="tag">{tag}</span>'
            html += "</div>"
        
        html += """
            <div class="footer">
                Sent from Recipe Editor
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_recipe(
        self,
        recipe: Recipe,
        recipient_email: str,
        recipient_name: str = "",
        custom_message: str = ""
    ) -> tuple[bool, str]:
        """
        Send a recipe via email (updated to use universal send_email method).
        
        Args:
            recipe: The recipe to send
            recipient_email: Email address of recipient
            recipient_name: Optional name of recipient
            custom_message: Optional custom message to include
        
        Returns:
            (success, error_message)
        """
        if not self.is_configured():
            error_msg = "Email service is not configured. Please set SMTP environment variables."
            logger.error(error_msg)
            return False, error_msg
        
        try:
            # Format recipe content
            html_content = self.format_recipe_email(recipe, custom_message)
            text_content = self._format_recipe_text(recipe, custom_message)
            
            # Send using the new unified method
            return self.send_email(
                to_email=recipient_email,
                subject=f"Recipe: {recipe.name}",
                html_content=html_content,
                text_content=text_content,
                to_name=recipient_name
            )
            
        except Exception as e:
            error_msg = f"Error sending recipe email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _format_recipe_text(self, recipe: Recipe, custom_message: str = "") -> str:
        """Format recipe as plain text for email fallback."""
        text = f"{recipe.name}\n{'=' * len(recipe.name)}\n\n"
        
        # Source information
        if recipe.source and recipe.source.get('name'):
            text += f"Source: {recipe.source['name']}"
            if recipe.source.get('author'):
                text += f" ({recipe.source['author']})"
            if recipe.source.get('issue'):
                text += f" - {recipe.source['issue']}"
            if recipe.source.get('url'):
                text += f"\n{recipe.source['url']}"
            text += "\n\n"
        
        if custom_message:
            text += f"{custom_message}\n\n"
        
        text += "INGREDIENTS\n-----------\n"
        for ing in recipe.ingredients:
            text += f"• {str(ing)}\n"
        
        if recipe.instructions:
            text += f"\nINSTRUCTIONS\n------------\n{recipe.instructions}\n"
        
        if recipe.notes:
            text += f"\nNOTES\n-----\n{recipe.notes}\n"
        
        if recipe.tags:
            text += f"\nTags: {', '.join(recipe.tags)}\n"
        
        text += "\n---\nSent from Recipe Editor\n"
        
        return text


# Global email service instance
email_service = EmailService()

