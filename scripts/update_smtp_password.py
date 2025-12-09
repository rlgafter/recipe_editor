#!/usr/bin/env python3
"""
Interactive script to update SMTP password in .env file.
This will help you set the correct Gmail App Password.
"""
import os
import re
import sys
from pathlib import Path

def update_env_file(new_password):
    """Update SMTP_PASSWORD in .env file."""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found!")
        return False
    
    # Read current content
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Find and update SMTP_PASSWORD line
    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith('export SMTP_PASSWORD='):
            # Update the password
            new_lines.append(f'export SMTP_PASSWORD={new_password}\n')
            updated = True
            print(f"✓ Updated SMTP_PASSWORD in .env")
        else:
            new_lines.append(line)
    
    if not updated:
        # Add it if it doesn't exist
        new_lines.append(f'export SMTP_PASSWORD={new_password}\n')
        print(f"✓ Added SMTP_PASSWORD to .env")
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(new_lines)
    
    return True

def test_password(username, password):
    """Test if the password works with Gmail SMTP."""
    import smtplib
    
    print("\nTesting SMTP connection...")
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(username, password)
        print("✓ Authentication successful!")
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ Authentication failed: {e}")
        print("\nThis usually means:")
        print("  1. The password is incorrect")
        print("  2. You need to generate a Gmail App Password (not your regular password)")
        print("  3. 2-Step Verification is not enabled")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("=" * 70)
    print("UPDATE GMAIL SMTP PASSWORD")
    print("=" * 70)
    print()
    print("To get a Gmail App Password:")
    print("  1. Go to: https://myaccount.google.com/apppasswords")
    print("  2. Select 'Mail' and 'Other (Custom name)'")
    print("  3. Name it 'Recipe Editor'")
    print("  4. Click 'Generate'")
    print("  5. Copy the 16-character password (remove any spaces)")
    print()
    print("Note: You must have 2-Step Verification enabled first!")
    print("      If not, enable it at: https://myaccount.google.com/security")
    print()
    
    # Get current username
    from dotenv import load_dotenv
    load_dotenv()
    current_username = os.environ.get('SMTP_USERNAME', '')
    
    if current_username:
        print(f"Current SMTP username: {current_username}")
        use_current = input(f"Use this username? (y/n) [y]: ").strip().lower()
        if use_current and use_current != 'y':
            username = input("Enter SMTP username (email): ").strip()
        else:
            username = current_username
    else:
        username = input("Enter SMTP username (email): ").strip()
    
    print()
    password = input("Enter Gmail App Password (16 characters, no spaces): ").strip()
    
    # Remove any spaces from password
    password = password.replace(' ', '')
    
    if len(password) < 16:
        print(f"⚠ Warning: Password is only {len(password)} characters. Gmail App Passwords are typically 16 characters.")
        proceed = input("Continue anyway? (y/n) [n]: ").strip().lower()
        if proceed != 'y':
            print("Cancelled.")
            return
    
    # Test the password
    if test_password(username, password):
        # Update .env file
        if update_env_file(password):
            print("\n✓ Password updated successfully!")
            print("\nYou can now send emails using:")
            print("  python3 scripts/send_missing_emails.py --execute")
        else:
            print("\n✗ Failed to update .env file")
    else:
        print("\n⚠ Password test failed. Not updating .env file.")
        print("Please verify your App Password and try again.")

if __name__ == '__main__':
    main()


