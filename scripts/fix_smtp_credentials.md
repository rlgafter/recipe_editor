# Fixing SMTP Authentication Issues

## Problem
Gmail is rejecting the SMTP credentials with error: "Username and Password not accepted"

## Solution Steps

### 1. Generate a New Gmail App Password

1. Go to your Google Account: https://myaccount.google.com/
2. Enable 2-Step Verification (if not already enabled)
   - Security → 2-Step Verification → Turn on
3. Generate App Password:
   - Security → App passwords
   - Select "Mail" and "Other (Custom name)"
   - Name it "Recipe Editor"
   - Click "Generate"
   - Copy the 16-character password (no spaces)

### 2. Update .env File

Edit the `.env` file and update the SMTP_PASSWORD line:

```bash
export SMTP_PASSWORD=your-16-character-app-password
```

**Important:**
- Remove any quotes around the password
- Remove any spaces before or after
- The password should be exactly 16 characters (Gmail app passwords are 16 chars, but they display as groups of 4)
- If your password has spaces in the display, remove them

### 3. Test the Connection

Run the test script:
```bash
python3 -c "
from dotenv import load_dotenv
load_dotenv()
import smtplib
import os
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(os.environ.get('SMTP_USERNAME'), os.environ.get('SMTP_PASSWORD'))
    print('✓ Authentication successful!')
    server.quit()
except Exception as e:
    print(f'✗ Failed: {e}')
"
```

### 4. Resend Emails

Once authentication works, run:
```bash
python3 scripts/send_missing_emails.py --execute
```

## Alternative: Use Different Email Provider

If Gmail continues to cause issues, you can use:
- SendGrid
- Mailgun
- AWS SES
- Outlook/Office365

Update the SMTP settings in `.env` accordingly.


