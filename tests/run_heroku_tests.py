#!/usr/bin/env python
"""
Run all Heroku tests for the CFDI API
"""
import os
import sys
import subprocess
import time
import argparse

# Add parent directory to path so we can import the test modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import heroku test modules directly to run their main function
import tests.heroku.test_api
import tests.heroku.test_admin

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

def main():
    """Run all Heroku test modules"""
    parser = argparse.ArgumentParser(description="Run tests against a Heroku CFDI API deployment")
    parser.add_argument("--url", default=os.getenv("HEROKU_API_URL", "https://validcfdi-api-be42092ab7e2.herokuapp.com"),
                        help="Heroku API URL to test")
    parser.add_argument("--token", default=os.getenv("HEROKU_API_TOKEN", "c822cf5ee82316013d21d912d95c5a770f86bd4ed278a8a33e729609e387efa4"),
                        help="API token for authentication")
    parser.add_argument("--admin-user", default=os.getenv("HEROKU_ADMIN_USERNAME", "admin"),
                        help="Admin username for admin tests")
    parser.add_argument("--admin-password", default=os.getenv("HEROKU_ADMIN_PASSWORD", "caragram"),
                        help="Admin password for admin tests")
    
    args = parser.parse_args()
    
    # Set environment variables for the tests
    os.environ["HEROKU_API_URL"] = args.url
    os.environ["HEROKU_API_TOKEN"] = args.token
    os.environ["HEROKU_ADMIN_USERNAME"] = args.admin_user
    os.environ["HEROKU_ADMIN_PASSWORD"] = args.admin_password
    
    start_time = time.time()
    
    print_header(f"Running CFDI API Heroku Tests against {args.url}")
    
    # First check if the Heroku app is accessible
    try:
        import requests
        response = requests.get(f"{args.url}/health", timeout=5)
        if response.status_code != 200:
            print(f"{RED}Heroku app is not responding correctly. Check if the app is running.{NC}")
            return 1
    except requests.exceptions.RequestException as e:
        print(f"{RED}Cannot connect to Heroku app: {e}{NC}")
        return 1
    
    # Run the test modules directly
    print_header("Testing API Endpoints")
    try:
        # Override sys.argv to avoid confusing the test module's argument parsing
        sys.argv = [sys.argv[0], args.url]
        tests.heroku.test_api.test_health_endpoint()
        headers_val = tests.heroku.test_api.headers()
        tests.heroku.test_api.test_verify_cfdi(headers_val)
        tests.heroku.test_api.test_verify_cfdi_batch(headers_val)
        tests.heroku.test_api.test_check_rfc_efos(headers_val)
        tests.heroku.test_api.test_check_rfc_efos_batch(headers_val)
        tests.heroku.test_api.test_unauthorized_access()
        print(f"{GREEN}✅ API tests passed{NC}")
    except Exception as e:
        print(f"{RED}❌ API tests failed: {e}{NC}")
        return 1
    
    print_header("Testing Admin Endpoints")
    try:
        # Run admin tests
        tests.heroku.test_admin.test_admin_list_tokens()
        tests.heroku.test_admin.test_admin_efos_metadata()
        
        # Create, regenerate and delete a token
        token_id = tests.heroku.test_admin.test_admin_create_token()
        if token_id:
            tests.heroku.test_admin.test_admin_regenerate_token(token_id)
            tests.heroku.test_admin.test_admin_delete_token(token_id)
        
        print(f"{GREEN}✅ Admin tests passed{NC}")
    except Exception as e:
        print(f"{RED}❌ Admin tests failed: {e}{NC}")
        return 1
    
    # Print summary
    elapsed_time = time.time() - start_time
    print_header("Test Summary")
    print(f"Ran all Heroku tests in {elapsed_time:.2f} seconds")
    print(f"{GREEN}All tests passed{NC}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 