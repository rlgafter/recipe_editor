#!/usr/bin/env python3
"""
Test runner for Recipe Editor testing suite.
Runs all available tests in the testing directory.
"""

import sys
import os
import subprocess
import glob

def run_test_script(script_path):
    """Run a single test script and return results."""
    print(f"\n🧪 Running {os.path.basename(script_path)}")
    print("-" * 50)
    
    try:
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, 
                              text=True, 
                              timeout=30)
        
        if result.returncode == 0:
            print("✅ Test passed")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print("❌ Test failed")
            if result.stderr:
                print("Error output:")
                print(result.stderr)
            if result.stdout:
                print("Standard output:")
                print(result.stdout)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Test timed out")
        return False
    except Exception as e:
        print(f"💥 Test error: {e}")
        return False

def main():
    """Run all available tests."""
    print("🚀 Recipe Editor Test Suite")
    print("=" * 60)
    
    # Get the testing directory
    testing_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find all test scripts (excluding this runner)
    test_scripts = glob.glob(os.path.join(testing_dir, "test_*.py"))
    test_scripts = [script for script in test_scripts 
                   if not script.endswith("run_tests.py")]
    
    # Add HTML test files (for documentation)
    html_tests = glob.glob(os.path.join(testing_dir, "test_*.html"))
    if html_tests:
        print(f"📄 Found {len(html_tests)} HTML test file(s) (manual testing required)")
        for html_test in html_tests:
            print(f"   • {os.path.basename(html_test)} - Open in browser for manual testing")
    
    if not test_scripts:
        print("❌ No test scripts found in testing directory")
        return
    
    print(f"📁 Found {len(test_scripts)} test script(s)")
    
    # Run each test
    results = []
    for script in sorted(test_scripts):
        success = run_test_script(script)
        results.append((os.path.basename(script), success))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for script_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {script_name:<30} {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
