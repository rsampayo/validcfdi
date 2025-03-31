#!/bin/bash

# Colors for formatting output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API URL for Heroku deployment
API_URL="https://validcfdi-api-be42092ab7e2.herokuapp.com"

# API Token 
API_TOKEN="c822cf5ee82316013d21d912d95c5a770f86bd4ed278a8a33e729609e387efa4"

# Admin credentials - CORRECT ONES FROM HEROKU CONFIG
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="caragram"

# Function to perform a test
test_endpoint() {
    local description=$1
    local method=$2
    local endpoint=$3
    local data=$4
    
    echo -e "\n${BLUE}====================================================${NC}"
    echo -e "${YELLOW}Testing: ${description}${NC}"
    echo -e "${BLUE}====================================================${NC}"
    echo -e "Method: ${method}"
    echo -e "Endpoint: ${API_URL}${endpoint}"
    
    if [ ! -z "$data" ]; then
        echo -e "Request Data: ${data}"
    fi
    
    # Create Basic Auth header
    BASIC_AUTH=$(echo -n "${ADMIN_USERNAME}:${ADMIN_PASSWORD}" | base64)
    AUTH_HEADER="-H \"Authorization: Basic ${BASIC_AUTH}\""
    
    # Build curl command
    if [ "$method" = "GET" ]; then
        CMD="curl -s ${AUTH_HEADER} ${API_URL}${endpoint}"
    else
        CMD="curl -s -X ${method} ${AUTH_HEADER} -H \"Content-Type: application/json\" ${API_URL}${endpoint}"
        if [ ! -z "$data" ]; then
            CMD="${CMD} -d '${data}'"
        fi
    fi
    
    echo -e "\nExecuting: ${CMD}"
    
    # Execute command
    RESPONSE=$(eval $CMD)
    
    # Display response
    echo -e "\nResponse:"
    if echo "$RESPONSE" | jq '.' > /dev/null 2>&1; then
        echo "$RESPONSE" | jq '.'
    else
        echo "$RESPONSE"
    fi
    
    echo -e "\n${GREEN}✅ Test completed${NC}"
}

echo -e "${BLUE}====================================================${NC}"
echo -e "${YELLOW}Testing Admin Endpoints with Valid Credentials${NC}"
echo -e "${BLUE}====================================================${NC}"

# Admin Endpoints
test_endpoint "Admin List Tokens" "GET" "/admin/tokens" ""
test_endpoint "Admin EFOS Metadata" "GET" "/admin/efos/metadata" ""
test_endpoint "Admin Create Token" "POST" "/admin/tokens" '{"description":"Test Token"}'

echo -e "\n${BLUE}====================================================${NC}"
echo -e "${YELLOW}All Admin Tests Completed${NC}"
echo -e "${BLUE}====================================================${NC}" 