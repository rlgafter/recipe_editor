# Testing Directory

This directory contains test scripts and testing utilities for the Recipe Editor application.

## 📁 Directory Structure

```
testing/
├── README.md                           # This file
├── run_tests.py                        # Test runner script
├── open_popup_test.py                  # Helper to open popup test page
├── test_enhanced_email_service.py     # Email service tests
├── test_email_popups.html             # Email popup UI tests
├── test_user_registration.py          # User registration tests (planned)
├── test_database_migrations.py        # Database migration tests (planned)
└── test_integration.py                # Integration tests (planned)
```

## 🧪 Test Scripts

### **test_enhanced_email_service.py**
Tests the enhanced email service functionality:
- Universal `send_email()` method
- `send_verification_email()` method
- `send_welcome_email()` method
- `send_password_reset_email()` method
- `send_notification_email()` method
- Updated `send_recipe()` method

**Usage:**
```bash
cd /path/to/recipe_editor
python3 testing/test_enhanced_email_service.py
```

### **test_email_popups.html**
Interactive test page for email popup notifications:
- Success popup testing with different scenarios
- Error popup testing with various error types
- Multiple popup stacking behavior
- Real recipe data testing
- Manual popup dismissal testing

**Usage:**
```bash
# Easy way - use the helper script
python3 testing/open_popup_test.py

# Manual way - open in browser
open testing/test_email_popups.html

# Or serve via web server
python3 -m http.server 8000
# Then visit: http://localhost:8000/testing/test_email_popups.html
```

### **open_popup_test.py**
Helper script to easily open the email popup test page:
- Opens the test page in your default browser
- Shows test features and instructions
- No setup required

**Usage:**
```bash
python3 testing/open_popup_test.py
```

### **Planned Test Scripts:**

#### **test_user_registration.py**
- Test user registration form validation
- Test username/email uniqueness checks
- Test password confirmation
- Test terms acceptance
- Test email verification flow

#### **test_database_migrations.py**
- Test database schema updates
- Test user type migrations
- Test verification field additions
- Test unique constraint creation

#### **test_integration.py**
- Test complete registration flow
- Test email verification end-to-end
- Test user login after verification
- Test error handling scenarios

## 🚀 Running Tests

### **Individual Test Scripts:**
```bash
# Test email service
python3 testing/test_enhanced_email_service.py

# Test user registration (when implemented)
python3 testing/test_user_registration.py

# Test database migrations (when implemented)
python3 testing/test_database_migrations.py

# Test integration (when implemented)
python3 testing/test_integration.py
```

### **All Tests (Future):**
```bash
# Run all tests
python3 -m pytest testing/

# Run with verbose output
python3 -m pytest testing/ -v

# Run specific test file
python3 -m pytest testing/test_enhanced_email_service.py
```

## 📋 Test Requirements

### **For Email Service Tests:**
- No external dependencies required
- Tests method existence and basic functionality
- SMTP configuration not required for basic tests

### **For Registration Tests:**
- Database connection required
- SMTP configuration for email tests
- Test user cleanup after tests

### **For Integration Tests:**
- Full application setup
- Database with test data
- SMTP configuration
- Web server running

## 🔧 Test Configuration

### **Environment Variables for Testing:**
```bash
# Database (for integration tests)
TEST_DATABASE_URL=sqlite:///test_recipe_editor.db

# Email (for email tests)
TEST_SMTP_SERVER=smtp.gmail.com
TEST_SMTP_PORT=587
TEST_SMTP_USERNAME=your-email@gmail.com
TEST_SMTP_PASSWORD=your-app-password
TEST_SENDER_EMAIL=your-email@gmail.com
TEST_SENDER_NAME=Recipe Editor Test

# Application
TEST_BASE_URL=http://localhost:5000
```

## 📊 Test Coverage Goals

- **Email Service**: 100% method coverage
- **User Registration**: 90%+ scenario coverage
- **Database Operations**: 95%+ query coverage
- **Integration Flow**: 85%+ user journey coverage

## 🐛 Debugging Tests

### **Common Issues:**
1. **Import Errors**: Ensure project root is in Python path
2. **Configuration Errors**: Check environment variables
3. **Database Errors**: Verify database connection
4. **Email Errors**: Verify SMTP configuration

### **Debug Mode:**
```bash
# Run with debug output
PYTHONPATH=/path/to/recipe_editor python3 testing/test_enhanced_email_service.py

# Run with logging
python3 testing/test_enhanced_email_service.py --debug
```

## 📝 Adding New Tests

### **Test File Template:**
```python
#!/usr/bin/env python3
"""
Test script for [component name].
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_component():
    """Test [component name] functionality."""
    print("🧪 Testing [Component Name]")
    print("=" * 50)
    
    # Test implementation here
    
    print("✅ Test Complete!")

if __name__ == "__main__":
    test_component()
```

### **Best Practices:**
- Use descriptive test names
- Include setup and teardown
- Test both success and failure cases
- Clean up test data
- Use meaningful assertions
- Document test requirements

## 🎯 Future Enhancements

- **Automated Testing**: CI/CD integration
- **Performance Testing**: Load testing for registration
- **Security Testing**: Input validation and SQL injection tests
- **UI Testing**: Selenium-based browser tests
- **API Testing**: REST endpoint testing
