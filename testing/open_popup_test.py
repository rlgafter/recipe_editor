#!/usr/bin/env python3
"""
Open the email popup test page in the default browser.
"""

import webbrowser
import os
import sys

def main():
    """Open the email popup test page."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_file = os.path.join(script_dir, "test_email_popups.html")
    
    # Check if file exists
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return 1
    
    # Get absolute path
    abs_path = os.path.abspath(test_file)
    
    print("🧪 Opening Email Popup Test Page")
    print("=" * 40)
    print(f"📁 File: {test_file}")
    print(f"🌐 URL: file://{abs_path}")
    print()
    print("📋 Test Features:")
    print("   • Success popup testing")
    print("   • Error popup testing") 
    print("   • Multiple popup scenarios")
    print("   • Real recipe examples")
    print("   • Manual dismissal testing")
    print()
    print("🎯 Click the test buttons to see different popup behaviors!")
    
    # Open in default browser
    webbrowser.open(f"file://{abs_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
