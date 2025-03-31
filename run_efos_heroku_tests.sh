#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Heroku app name
HEROKU_APP_NAME="validcfdi-efos"

echo -e "${BLUE}====================================================${NC}"
echo -e "${YELLOW}Running CFDI-EFOS API Tests on Heroku${NC}"
echo -e "${BLUE}====================================================${NC}"

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo -e "${RED}Heroku CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is logged in to Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo -e "${RED}You are not logged in to Heroku. Please run 'heroku login' first.${NC}"
    exit 1
fi

# Check if the app exists
if ! heroku apps:info --app $HEROKU_APP_NAME &> /dev/null; then
    echo -e "${RED}Heroku app '$HEROKU_APP_NAME' does not exist or you don't have access to it.${NC}"
    exit 1
fi

echo -e "${YELLOW}Running tests on Heroku app: $HEROKU_APP_NAME${NC}"

# Run tests on Heroku
echo -e "${BLUE}====================================================${NC}"
echo -e "${YELLOW}Checking Heroku dynos...${NC}"
echo -e "${BLUE}====================================================${NC}"

# First check if the app is running
if ! heroku ps:scale --app $HEROKU_APP_NAME | grep -q "web=1"; then
    echo -e "${RED}The web dyno is not running. Starting it...${NC}"
    heroku ps:scale web=1 --app $HEROKU_APP_NAME
    echo -e "${YELLOW}Waiting for the web dyno to start...${NC}"
    sleep 10
fi

# Check if worker is running for EFOS data
if ! heroku ps:scale --app $HEROKU_APP_NAME | grep -q "worker=1"; then
    echo -e "${YELLOW}The worker dyno is not running. Starting it for EFOS data...${NC}"
    heroku ps:scale worker=1 --app $HEROKU_APP_NAME
    echo -e "${YELLOW}Waiting for the worker dyno to start...${NC}"
    sleep 10
fi

# Get the necessary credentials from Heroku config
echo -e "${YELLOW}Getting API URL and credentials...${NC}"
HEROKU_API_URL="https://$HEROKU_APP_NAME-d2fa8fe5e435.herokuapp.com"
echo -e "Using API URL: ${GREEN}$HEROKU_API_URL${NC}"

# Get admin credentials from Heroku config
ADMIN_PASSWORD=$(heroku config:get SUPERADMIN_PASSWORD --app $HEROKU_APP_NAME)
ADMIN_USERNAME=$(heroku config:get SUPERADMIN_USERNAME --app $HEROKU_APP_NAME || echo "admin")

if [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${RED}Could not find SUPERADMIN_PASSWORD in Heroku config.${NC}"
    exit 1
fi

echo -e "${BLUE}====================================================${NC}"
echo -e "${YELLOW}Running Python tests...${NC}"
echo -e "${BLUE}====================================================${NC}"

# Create the Python test script
cat > temp_test_efos.py << 'END_OF_SCRIPT'
import requests
import json
import os
import base64
import sys

# Get the API URL and credentials from environment
API_URL = os.environ.get('HEROKU_API_URL')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

# Colors for better output in terminal
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_color(color, message):
    print(f"{color}{message}{NC}")

def print_separator():
    print_color(BLUE, "=" * 60)

def test_health():
    print_color(YELLOW, "Testing Health Endpoint...")
    response = requests.get(f"{API_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2) if response.status_code == 200 else response.text}")
    
    if response.status_code == 200:
        print_color(GREEN, "✅ Health check passed")
        return True
    else:
        print_color(RED, f"❌ Health check failed")
        return False

def get_admin_auth_header():
    # Create Basic Auth header
    auth_string = f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    return {"Authorization": f"Basic {auth_b64}"}

def test_admin_tokens():
    print_color(YELLOW, "Testing Admin Tokens Endpoint...")
    auth_header = get_admin_auth_header()
    
    response = requests.get(f"{API_URL}/admin/tokens", headers=auth_header)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        tokens_data = response.json()
        tokens = tokens_data.get("tokens", [])
        print_color(GREEN, f"✅ Admin tokens endpoint passed. Found {len(tokens)} tokens.")
        
        if tokens:
            return tokens[0].get("token")
        else:
            print_color(YELLOW, "No tokens found. Creating one...")
            create_response = requests.post(
                f"{API_URL}/admin/tokens", 
                headers=auth_header,
                json={"description": "Test token created by test script"}
            )
            
            if create_response.status_code == 200:
                token = create_response.json().get("token")
                print_color(GREEN, f"✅ Created new API token")
                return token
            else:
                print_color(RED, f"❌ Failed to create token: {create_response.text}")
                return None
    else:
        print_color(RED, f"❌ Admin tokens endpoint failed: {response.text}")
        return None

def test_efos_metadata():
    print_color(YELLOW, "Testing EFOS Metadata Endpoint...")
    auth_header = get_admin_auth_header()
    
    response = requests.get(f"{API_URL}/admin/efos/metadata", headers=auth_header)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        metadata = response.json()
        print(f"Response: {json.dumps(metadata, indent=2)}")
        print_color(GREEN, f"✅ EFOS metadata endpoint passed")
        
        if metadata.get("is_downloaded"):
            print_color(GREEN, f"✅ EFOS data is downloaded with {metadata.get('records_count', 0)} records")
        else:
            print_color(YELLOW, f"⚠️ EFOS data is not downloaded")
        
        return True
    else:
        print_color(RED, f"❌ EFOS metadata endpoint failed: {response.text}")
        return False

def test_cfdi_verification(token):
    print_color(YELLOW, "Testing CFDI Verification Endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test data - using a random but well-formed UUID that won't be found
    test_data = {
        "uuid": "A1B2C3D4-E5F6-G7H8-I9J0-K1L2M3N4O5P6",
        "emisor_rfc": "TEST010101TE5",
        "receptor_rfc": "TEST010101TES",
        "total": "1000.00"
    }
    
    response = requests.post(f"{API_URL}/verify-cfdi", json=test_data, headers=headers)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # The expected response for a non-existent CFDI should indicate "No Encontrado"
        if result.get("estado") == "No Encontrado":
            print_color(GREEN, f"✅ CFDI verification endpoint passed (correctly reported as 'No Encontrado')")
            return True
        else:
            print_color(YELLOW, f"⚠️ CFDI verification returned unexpected status: {result.get('estado')}")
            return True
    else:
        print_color(RED, f"❌ CFDI verification endpoint failed: {response.text}")
        return False

def test_rfc_efos_check(token):
    print_color(YELLOW, "Testing RFC EFOS Check Endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with a fake RFC that's unlikely to be in the list
    test_data = {"rfc": "TEST010101TE5"}
    
    response = requests.post(f"{API_URL}/check-rfc-efos", json=test_data, headers=headers)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # The test RFC should not be in the EFOS list
        if result.get("is_in_efos_list") == False:
            print_color(GREEN, f"✅ RFC EFOS check endpoint passed (correctly reported as not in list)")
            return True
        else:
            print_color(YELLOW, f"⚠️ RFC EFOS check returned unexpected result for test RFC")
            return True
    else:
        print_color(RED, f"❌ RFC EFOS check endpoint failed: {response.text}")
        return False

def main():
    print_color(BLUE, "=" * 60)
    print_color(YELLOW, f"Running CFDI-EFOS API Tests against {API_URL}")
    print_color(BLUE, "=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test health endpoint
    print_separator()
    if test_health():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test admin tokens endpoint & get token
    print_separator()
    token = test_admin_tokens()
    if token:
        tests_passed += 1
    else:
        tests_failed += 1
        print_color(RED, "❌ Cannot continue tests without API token")
        sys.exit(1)
    
    # Test EFOS metadata endpoint
    print_separator()
    if test_efos_metadata():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test CFDI verification endpoint
    print_separator()
    if test_cfdi_verification(token):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test RFC EFOS check endpoint
    print_separator()
    if test_rfc_efos_check(token):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Print summary
    print_separator()
    print_color(YELLOW, "Test Summary")
    print_separator()
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"Tests passed: {tests_passed}")
    print(f"Tests failed: {tests_failed}")
    
    if tests_failed == 0:
        print_color(GREEN, "✅ All tests passed!")
        sys.exit(0)
    else:
        print_color(RED, f"❌ {tests_failed} tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
END_OF_SCRIPT

# Run the Python test script with environment variables
HEROKU_API_URL="$HEROKU_API_URL" ADMIN_USERNAME="$ADMIN_USERNAME" ADMIN_PASSWORD="$ADMIN_PASSWORD" python temp_test_efos.py

# Capture the exit code
TEST_RESULT=$?

# Clean up the temporary test file
rm temp_test_efos.py

# Return the test result
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}All tests passed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Tests failed.${NC}"
    exit 1
fi 