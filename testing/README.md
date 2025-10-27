# Recipe Editor Test Suite

A comprehensive test suite for the Recipe Editor application that tests authentication, authorization, recipe validation, and complete user workflows across both JSON and MySQL storage backends.

## Test Structure

The test suite is organized into the following categories:

### 1. Authentication & Authorization Tests (`test_auth.py`)
- **User Authentication**: Login/logout functionality, credential validation
- **Access Control**: Protected route access, session management
- **User Permissions**: Recipe creation permissions, admin access
- **Session Management**: Session persistence and expiry

### 2. Recipe Visibility Tests (`test_recipe_visibility.py`)
- **Visibility Control**: Private, public, and incomplete recipe access
- **User Access**: Logged-in vs logged-out user recipe visibility
- **Admin Access**: Admin users can see all recipes
- **Recipe Filtering**: Proper filtering in recipe lists

### 3. Validation Tests (`test_validation.py`)
- **Field Validation**: Name, instructions, source, ingredients
- **Error Messages**: Consistent error presentation
- **Edge Cases**: Special characters, unicode, long inputs
- **Form Integration**: Multiple validation errors

### 4. Recipe Requirements Tests (`test_recipe_requirements.py`)
- **Minimum Requirements**: Name, source, 3+ ingredients, instructions
- **Source Validation**: At least one of name, author, or URL required
- **Ingredient Validation**: Minimum 3 ingredients with descriptions
- **Complete Workflows**: End-to-end requirement validation

### 5. Integration Tests (`test_integration.py`)
- **Complete Workflows**: Registration → Login → Recipe Creation
- **Error Recovery**: Form validation error handling
- **Data Consistency**: Recipe data consistency across operations
- **Performance**: Response time and concurrent operations

## Test Configuration

### Backend Support
The test suite supports both storage backends:
- **JSON Backend**: Uses `app.py` with JSON file storage
- **MySQL Backend**: Uses `app_mysql.py` with SQLite for testing

### Test Database
- Uses **SQLite in-memory database** for fast test execution
- Each test gets a fresh database instance
- No external database dependencies required

### Fixtures
- **Test Users**: Regular user and admin user accounts
- **Test Recipes**: Public, private, and incomplete recipes
- **Invalid Data**: Comprehensive invalid data sets for validation testing
- **Valid Data**: Complete valid recipe data for success testing

## Running Tests

### Prerequisites
Install test dependencies:
```bash
pip install pytest pytest-flask
```

### Run All Tests
```bash
# From project root
python testing/run_tests.py

# Or using pytest directly
pytest testing/ -v
```

### Run Specific Test Categories
```bash
# Authentication tests only
pytest testing/test_auth.py -v

# Validation tests only
pytest testing/test_validation.py -v

# Integration tests only
pytest testing/test_integration.py -v
```

### Run Tests for Specific Backend
```bash
# JSON backend only
pytest testing/ -k "json" -v

# MySQL backend only
pytest testing/ -k "mysql" -v
```

### Run Tests with Markers
```bash
# Unit tests only
pytest testing/ -m "unit" -v

# Integration tests only
pytest testing/ -m "integration" -v

# Skip slow tests
pytest testing/ -m "not slow" -v
```

## Test Coverage

### Authentication & Authorization
- ✅ Login/logout functionality
- ✅ Protected route access control
- ✅ Session management
- ✅ User permission validation
- ✅ Admin access control

### Recipe Visibility
- ✅ Public recipe visibility to all users
- ✅ Private recipe visibility to owners only
- ✅ Incomplete recipe visibility to owners only
- ✅ Admin access to all recipes
- ✅ Recipe list filtering

### Validation
- ✅ Required field validation (name, instructions, source, ingredients)
- ✅ Field format validation (amounts, URLs)
- ✅ Error message consistency
- ✅ Multiple validation error handling
- ✅ Edge case handling (unicode, special characters)

### Recipe Requirements
- ✅ Recipe name requirement
- ✅ Source information requirement (name, author, or URL)
- ✅ Minimum 3 ingredients requirement
- ✅ Instructions requirement
- ✅ Complete recipe validation

### Integration
- ✅ Complete user workflows
- ✅ Error recovery scenarios
- ✅ Data consistency across operations
- ✅ Performance testing
- ✅ Cross-backend compatibility

## Test Data

### Test Users
- **testuser**: Regular user with recipe creation permissions
- **admin**: Admin user with full access

### Test Recipes
- **Public Recipe**: Visible to all authenticated users
- **Private Recipe**: Visible only to owner
- **Incomplete Recipe**: Visible only to owner

### Validation Test Cases
- Empty fields
- Invalid formats
- Insufficient data
- Special characters
- Unicode characters
- Very long inputs

## Error Message Consistency

The test suite ensures that error messages are:
- **Consistent**: Same format across different validation failures
- **Descriptive**: Clear indication of what's wrong
- **User-friendly**: Easy to understand and act upon
- **Comprehensive**: Cover all validation scenarios

## Performance Considerations

- Tests use SQLite in-memory database for speed
- Each test is isolated with fresh data
- Timeout limits prevent hanging tests
- Concurrent operation testing included

## Continuous Integration

The test suite is designed to work in CI environments:
- No external dependencies
- Fast execution
- Clear pass/fail indicators
- Comprehensive error reporting

## Contributing

When adding new tests:
1. Follow the existing test structure and naming conventions
2. Add appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
3. Include both positive and negative test cases
4. Test both JSON and MySQL backends
5. Update this README if adding new test categories

## Troubleshooting

### Common Issues
- **Import Errors**: Ensure you're running from the project root
- **Database Errors**: Check that SQLite is available
- **Authentication Errors**: Verify test user credentials in fixtures
- **Timeout Errors**: Increase timeout limits for slow tests

### Debug Mode
Run tests with verbose output for debugging:
```bash
pytest testing/ -v -s --tb=long
```