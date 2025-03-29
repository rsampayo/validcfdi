import requests
import json
import base64
from colorama import init, Fore, Style
import sys

# Initialize colorama for colored terminal output
init()

# API URL - replace with your actual URL (localhost for development)
API_URL = "http://localhost:8000"

# Superadmin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"

# Test CFDI data
TEST_CFDI = {
    "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
    "emisor_rfc": "CDZ050722LA9",
    "receptor_rfc": "XIN06112344A",
    "total": "12000.00"
}

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f" {text}")
    print(f"{'=' * 60}{Style.RESET_ALL}\n")

def print_success(text):
    """Print a success message"""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")

def print_error(text):
    """Print an error message"""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")

def print_warning(text):
    """Print a warning message"""
    print(f"{Fore.YELLOW}! {text}{Style.RESET_ALL}")

def print_json(data):
    """Print formatted JSON"""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            print(data)
            return
    
    print(json.dumps(data, indent=2))

def get_basic_auth_header(username, password):
    """Create HTTP Basic auth header"""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

def test_health_endpoint():
    """Test health endpoint"""
    print_header("Testing Health Endpoint")
    
    try:
        response = requests.get(f"{API_URL}/health")
        
        if response.status_code == 200:
            print_success(f"Health endpoint returned: {response.json()}")
            return True
        else:
            print_error(f"Health endpoint failed with status code: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Error testing health endpoint: {e}")
        return False

def test_create_token():
    """Test creating a new token"""
    print_header("Testing Token Creation")
    
    try:
        headers = {
            "Authorization": get_basic_auth_header(ADMIN_USERNAME, ADMIN_PASSWORD),
            "Content-Type": "application/json"
        }
        
        data = {
            "description": "Test token for comprehensive test"
        }
        
        response = requests.post(
            f"{API_URL}/admin/tokens",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Token created successfully with ID: {result['id']}")
            print(f"Token value: {result['token']}")
            return result
        else:
            print_error(f"Failed to create token. Status code: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Error creating token: {e}")
        return None

def test_verify_cfdi(token):
    """Test CFDI verification"""
    print_header("Testing CFDI Verification")
    
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{API_URL}/verify-cfdi",
            headers=headers,
            json=TEST_CFDI
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Truncate raw_response for display
            if "raw_response" in result:
                result["raw_response"] = result["raw_response"][:100] + "... (truncated)"
            
            print_success("CFDI verification successful")
            print_json(result)
            
            # Check for expected fields
            required_fields = ["estado", "es_cancelable", "codigo_estatus"]
            missing_fields = [field for field in required_fields if not result.get(field)]
            
            if missing_fields:
                print_warning(f"Missing expected fields: {', '.join(missing_fields)}")
                return False
            
            if result.get("estado") != "Vigente":
                print_warning(f"Unexpected estado value: {result.get('estado')}")
                return False
                
            return True
        else:
            print_error(f"CFDI verification failed with status code: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Error during CFDI verification: {e}")
        return False

def test_list_tokens():
    """Test listing tokens"""
    print_header("Testing Token Listing")
    
    try:
        headers = {
            "Authorization": get_basic_auth_header(ADMIN_USERNAME, ADMIN_PASSWORD)
        }
        
        response = requests.get(
            f"{API_URL}/admin/tokens",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            
            token_count = len(result.get("tokens", []))
            print_success(f"Retrieved {token_count} tokens")
            
            # Display just the first 3 tokens to avoid cluttering output
            if token_count > 3:
                print(f"Showing first 3 of {token_count} tokens:")
                result["tokens"] = result["tokens"][:3]
            
            print_json(result)
            return True
        else:
            print_error(f"Failed to list tokens. Status code: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Error listing tokens: {e}")
        return False

def run_tests():
    """Run all tests"""
    print_header("CFDI API COMPREHENSIVE TEST")
    print(f"Testing API at: {API_URL}")
    print(f"Admin credentials: {ADMIN_USERNAME}:{'*' * len(ADMIN_PASSWORD)}")
    
    # Track test results
    results = {}
    
    # Test health endpoint
    results["health"] = test_health_endpoint()
    
    # Test token creation
    token_data = test_create_token()
    results["create_token"] = token_data is not None
    
    # Test token listing
    results["list_tokens"] = test_list_tokens()
    
    # Test CFDI verification if token was created
    if token_data:
        results["verify_cfdi"] = test_verify_cfdi(token_data["token"])
    else:
        results["verify_cfdi"] = False
    
    # Print summary
    print_header("TEST RESULTS SUMMARY")
    
    all_passed = True
    for test_name, passed in results.items():
        if passed:
            print_success(f"{test_name.replace('_', ' ').title()}: Passed")
        else:
            all_passed = False
            print_error(f"{test_name.replace('_', ' ').title()}: Failed")
    
    if all_passed:
        print_success("\nAll tests passed successfully!")
        return 0
    else:
        print_error("\nSome tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests()) 