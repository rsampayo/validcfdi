#!/usr/bin/env python
"""
Run all Heroku tests for the CFDI API
"""
import os
import sys
import subprocess
import time
import argparse
import requests
import json

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

def main():
    """Run all Heroku test modules"""
    parser = argparse.ArgumentParser(description="Run tests against a Heroku CFDI API deployment")
    parser.add_argument("--url", default=os.getenv("HEROKU_API_URL", "https://validcfdi-api-be42092ab7e2.herokuapp.com"),
                        help="Heroku API URL to test")
    parser.add_argument("--token", default=os.getenv("HEROKU_API_TOKEN", "default-token-479efc20c963150db08021870723d0f3"),
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
        response = requests.get(f"{args.url}/health", timeout=5)
        if response.status_code != 200:
            print(f"{RED}Heroku app is not responding correctly. Check if the app is running.{NC}")
            return 1
    except requests.exceptions.RequestException as e:
        print(f"{RED}Cannot connect to Heroku app: {e}{NC}")
        return 1
    
    # Run API tests directly without using pytest fixtures
    print_header("Testing API Endpoints")
    try:
        # Test health endpoint
        print(f"\nTesting Health Endpoint on {args.url}...")
        response = requests.get(f"{args.url}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 200
        assert "status" in response.json()
        
        # Set up headers for authenticated requests
        headers = {
            "Authorization": f"Bearer {args.token}",
            "Content-Type": "application/json"
        }
        
        # Test verify-cfdi endpoint
        print(f"\nTesting Single CFDI Verification on {args.url}...")
        test_data = {
            "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
            "emisor_rfc": "CDZ050722LA9",
            "receptor_rfc": "XIN06112344A",
            "total": "12000.00"
        }
        response = requests.post(f"{args.url}/verify-cfdi", headers=headers, json=test_data)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200
        assert "estado" in response.json()
        
        # Test verify-cfdi-batch endpoint
        print(f"\nTesting Batch CFDI Verification on {args.url}...")
        batch_data = {
            "cfdis": [
                {
                    "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
                    "emisor_rfc": "CDZ050722LA9",
                    "receptor_rfc": "XIN06112344A",
                    "total": "12000.00"
                },
                {
                    "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
                    "emisor_rfc": "CDZ050722LA9",
                    "receptor_rfc": "XIN06112344A",
                    "total": "12000.00"
                }
            ]
        }
        response = requests.post(f"{args.url}/verify-cfdi-batch", headers=headers, json=batch_data)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200
        assert "results" in response.json()
        
        # Test check-rfc-efos endpoint
        print(f"\nTesting RFC EFOS Check on {args.url}...")
        rfc_data = {"rfc": "AAA100303L51"}
        response = requests.post(f"{args.url}/check-rfc-efos", headers=headers, json=rfc_data)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200
        assert "rfc" in response.json()
        assert "is_in_efos_list" in response.json()
        
        # Test check-rfc-efos-batch endpoint
        print(f"\nTesting Batch RFC EFOS Check on {args.url}...")
        batch_rfc_data = {"rfcs": ["AAA100303L51", "AAA120730823", "AAA121206EV5"]}
        response = requests.post(f"{args.url}/check-rfc-efos-batch", headers=headers, json=batch_rfc_data)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200
        assert "results" in response.json()
        
        # Test unauthorized access
        print(f"\nTesting Unauthorized Access on {args.url}...")
        response = requests.post(f"{args.url}/verify-cfdi", json=test_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        # Accept either 401 or 403 as valid status codes for unauthorized access
        assert response.status_code in [401, 403]
        assert "detail" in response.json()
        # Check that the message contains an auth error (either "Not authenticated" or "Forbidden")
        assert any(msg in response.json()["detail"] for msg in ["authenticate", "Forbidden", "Not authenticated"])
        
        print(f"{GREEN}✅ API tests passed{NC}")
    except Exception as e:
        print(f"{RED}❌ API tests failed: {e}{NC}")
        return 1
    
    # Run Admin tests
    print_header("Testing Admin Endpoints")
    try:
        import base64
        # Set up admin headers with Basic auth
        credentials = f"{args.admin_user}:{args.admin_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        admin_headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }
        
        # Test admin/tokens endpoint
        print(f"\nTesting Admin List Tokens on {args.url}...")
        response = requests.get(f"{args.url}/admin/tokens", headers=admin_headers)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200
        assert "tokens" in response.json()
        
        # Test admin/efos/metadata endpoint
        print(f"\nTesting Admin EFOS Metadata on {args.url}...")
        response = requests.get(f"{args.url}/admin/efos/metadata", headers=admin_headers)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200
        
        # Test admin/tokens (create token) endpoint
        print(f"\nTesting Admin Create Token on {args.url}...")
        test_data = {"description": "Heroku Test Token"}
        response = requests.post(f"{args.url}/admin/tokens", headers=admin_headers, json=test_data)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200
        assert "token" in response.json()
        assert "id" in response.json()
        
        # Get the token ID for subsequent tests
        token_id = response.json()["id"]
        
        # Test regenerate token
        print(f"\nTesting Admin Regenerate Token on {args.url}...")
        response = requests.post(f"{args.url}/admin/tokens/{token_id}/regenerate", headers=admin_headers)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200
        assert "token" in response.json()
        
        # Test delete token
        print(f"\nTesting Admin Delete Token on {args.url}...")
        response = requests.delete(f"{args.url}/admin/tokens/{token_id}", headers=admin_headers)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200
        assert "message" in response.json()
        
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