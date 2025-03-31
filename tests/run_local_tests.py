#!/usr/bin/env python
"""
Run all local tests for the CFDI API
"""
import os
import sys
import subprocess
import time

# Set the API URL to the Heroku endpoint
os.environ["API_URL"] = "https://validcfdi-efos-d2fa8fe5e435.herokuapp.com"

# Add parent directory to path so we can import the test modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define colors for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_header(message):
    """Print a formatted header message"""
    print(f"\n{BLUE}{'=' * 70}{NC}")
    print(f"{YELLOW}{message}{NC}")
    print(f"{BLUE}{'=' * 70}{NC}")

def run_pytest(module_path):
    """Run pytest on a specific module and return True if successful"""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", module_path, "-v"],
            check=False,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(f"{RED}ERRORS:{NC}")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"{RED}Failed to run tests: {e}{NC}")
        return False

def main():
    """Run all test modules"""
    start_time = time.time()
    
    print_header("Running CFDI API Local Tests")
    
    # Check if the server is running on localhost:8000
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print(f"{RED}Server is not responding correctly. Make sure it's running on localhost:8000{NC}")
            return 1
    except requests.exceptions.RequestException:
        print(f"{RED}Server is not running. Please start the server with 'uvicorn main:app --reload' before running tests.{NC}")
        return 1
    
    # Define test modules to run
    test_modules = [
        "tests/local/test_api.py",
        "tests/local/test_admin.py"
    ]
    
    # Run each test module
    success_count = 0
    for module in test_modules:
        module_name = os.path.basename(module)
        print_header(f"Running {module_name}")
        if run_pytest(module):
            success_count += 1
            print(f"{GREEN}✅ {module_name} tests passed{NC}")
        else:
            print(f"{RED}❌ {module_name} tests failed{NC}")
    
    # Print summary
    elapsed_time = time.time() - start_time
    print_header("Test Summary")
    print(f"Ran {len(test_modules)} test modules in {elapsed_time:.2f} seconds")
    print(f"{GREEN}{success_count}/{len(test_modules)} modules passed{NC}")
    
    return 0 if success_count == len(test_modules) else 1

if __name__ == "__main__":
    sys.exit(main()) 