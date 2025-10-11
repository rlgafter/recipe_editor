"""
Email service for sending recipes via SMTP.
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
    """Handles sending emails via SMTP."""
    
    def __init__(self):
        """Initialize email service with configuration."""
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.username = config.SMTP_USERNAME
        self.password = config.SMTP_PASSWORD
        self.use_tls = config.SMTP_USE_TLS
        self.sender_email = config.SENDER_EMAIL
        self.sender_name = config.SENDER_NAME
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.smtp_server and self.username and self.password and self.sender_email)
    
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
            </style>
        </head>
        <body>
            <h1>{recipe.name}</h1>
        """
        
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
        Send a recipe via email.
        
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
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Recipe: {recipe.name}"
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            
            if recipient_name:
                msg['To'] = f"{recipient_name} <{recipient_email}>"
            else:
                msg['To'] = recipient_email
            
            # Create HTML content
            html_content = self.format_recipe_email(recipe, custom_message)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Create plain text fallback
            text_content = self._format_recipe_text(recipe, custom_message)
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
            
            logger.info(f"Successfully sent recipe '{recipe.name}' to {recipient_email}")
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
    
    def _format_recipe_text(self, recipe: Recipe, custom_message: str = "") -> str:
        """Format recipe as plain text for email fallback."""
        text = f"{recipe.name}\n{'=' * len(recipe.name)}\n\n"
        
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

