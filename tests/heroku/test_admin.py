"""
Heroku Admin API tests for CFDI API
"""
import pytest
import requests
import os
import sys
import json
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API URL for Heroku testing
if len(sys.argv) > 1:
    # Allow passing API URL as command line argument
    API_URL = sys.argv[1]
else:
    API_URL = os.getenv("HEROKU_API_URL", "https://validcfdi-api-be42092ab7e2.herokuapp.com")

# Get admin credentials from environment or use default
ADMIN_USERNAME = os.getenv("HEROKU_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("HEROKU_ADMIN_PASSWORD", "caragram")

def get_admin_headers():
    """Return the headers for admin API requests with basic auth"""
    credentials = f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }

def test_admin_list_tokens():
    """Test the admin/tokens endpoint (listing tokens)"""
    print(f"\nTesting Admin List Tokens on {API_URL}...")
    
    headers = get_admin_headers()
    
    response = requests.get(
        f"{API_URL}/admin/tokens",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("Response:")
        # Truncate output if too many tokens
        response_data = response.json()
        if response_data.get("tokens") and len(response_data["tokens"]) > 3:
            response_data["tokens"] = response_data["tokens"][:3]
            response_data["tokens"].append({"note": "... more tokens truncated ..."})
        print(json.dumps(response_data, indent=2))
    else:
        print(f"Error Response: {response.text}")
    
    assert response.status_code == 200
    assert "tokens" in response.json()
    
def test_admin_efos_metadata():
    """Test the admin/efos/metadata endpoint"""
    print(f"\nTesting Admin EFOS Metadata on {API_URL}...")
    
    headers = get_admin_headers()
    
    response = requests.get(
        f"{API_URL}/admin/efos/metadata",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error Response: {response.text}")
    
    assert response.status_code == 200
    
def test_admin_create_token():
    """Test token creation"""
    print(f"\nTesting Admin Create Token on {API_URL}...")
    
    headers = get_admin_headers()
    
    test_data = {
        "description": "Heroku Test Token"
    }
    
    print("Request:")
    print(json.dumps(test_data, indent=2))
    
    response = requests.post(
        f"{API_URL}/admin/tokens",
        headers=headers,
        json=test_data
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error Response: {response.text}")
    
    assert response.status_code == 200
    assert "token" in response.json()
    assert "id" in response.json()
    
    # Return the token ID for subsequent tests
    return response.json()["id"]
    
def test_admin_regenerate_token(token_id):
    """Test token regeneration"""
    print(f"\nTesting Admin Regenerate Token on {API_URL}...")
    
    headers = get_admin_headers()
    
    response = requests.post(
        f"{API_URL}/admin/tokens/{token_id}/regenerate",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error Response: {response.text}")
    
    assert response.status_code == 200
    assert "token" in response.json()
    
def test_admin_delete_token(token_id):
    """Test token deletion"""
    print(f"\nTesting Admin Delete Token on {API_URL}...")
    
    headers = get_admin_headers()
    
    response = requests.delete(
        f"{API_URL}/admin/tokens/{token_id}",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error Response: {response.text}")
    
    assert response.status_code == 200
    assert "message" in response.json()

if __name__ == "__main__":
    # Allow running as a standalone script
    print(f"Testing Heroku Admin API at {API_URL}")
    print("=" * 50)
    
    test_admin_list_tokens()
    test_admin_efos_metadata()
    
    # Create a token, then regenerate and delete it
    token_id = test_admin_create_token()
    if token_id:
        test_admin_regenerate_token(token_id)
        test_admin_delete_token(token_id)
    
    print("\nTest Summary")
    print("=" * 50)
    print("All tests passed ✅") 