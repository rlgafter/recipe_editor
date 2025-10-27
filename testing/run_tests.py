#!/usr/bin/env python3
"""
Test runner for Recipe Editor testing suite.
Runs all available tests using pytest framework.
"""

import sys
import os
import subprocess
import glob

def run_pytest_tests():
    """Run tests using pytest."""
    print("🚀 Recipe Editor Test Suite (pytest)")
    print("=" * 60)
    
    # Get the project root directory (parent of testing directory)
    testing_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(testing_dir)
    
    # Change to project root directory
    os.chdir(project_root)
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'testing/', 
            '-v', 
            '--tb=short',
            '--color=yes'
        ], capture_output=True, text=True, timeout=300)
        
        print(result.stdout)
        if result.stderr:
            print("Error output:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Tests timed out")
        return False
    except Exception as e:
        print(f"💥 Test error: {e}")
        return False

def run_legacy_tests():
    """Run legacy test scripts (non-pytest)."""
    print("\n🧪 Running Legacy Tests")
    print("-" * 50)
    
    testing_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find legacy test scripts (excluding pytest tests and this runner)
    test_scripts = glob.glob(os.path.join(testing_dir, "test_*.py"))
    pytest_tests = ['test_auth.py', 'test_recipe_visibility.py', 'test_validation.py', 
                   'test_recipe_requirements.py', 'test_integration.py']
    
    legacy_scripts = [script for script in test_scripts 
                     if os.path.basename(script) not in pytest_tests and 
                     not script.endswith("run_tests.py")]
    
    if not legacy_scripts:
        print("No legacy test scripts found")
        return True
    
    results = []
    for script in sorted(legacy_scripts):
        print(f"\n🧪 Running {os.path.basename(script)}")
        print("-" * 30)
        
        try:
            result = subprocess.run([sys.executable, script], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=30)
            
            if result.returncode == 0:
                print("✅ Test passed")
                if result.stdout:
                    print(result.stdout)
                results.append(True)
            else:
                print("❌ Test failed")
                if result.stderr:
                    print("Error output:")
                    print(result.stderr)
                if result.stdout:
                    print("Standard output:")
                    print(result.stdout)
                results.append(False)
                
        except subprocess.TimeoutExpired:
            print("⏰ Test timed out")
            results.append(False)
        except Exception as e:
            print(f"💥 Test error: {e}")
            results.append(False)
    
    return all(results)

def main():
    """Run all available tests."""
    print("🚀 Recipe Editor Comprehensive Test Suite")
    print("=" * 60)
    
    # Check if pytest is available
    try:
        import pytest
        pytest_available = True
    except ImportError:
        pytest_available = False
        print("⚠️  pytest not available, running legacy tests only")
    
    success = True
    
    if pytest_available:
        # Run pytest tests
        pytest_success = run_pytest_tests()
        success = success and pytest_success
    
    # Run legacy tests
    legacy_success = run_legacy_tests()
    success = success and legacy_success
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    if pytest_available:
        print(f"   pytest tests: {'✅ PASS' if pytest_success else '❌ FAIL'}")
    print(f"   legacy tests: {'✅ PASS' if legacy_success else '❌ FAIL'}")
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
