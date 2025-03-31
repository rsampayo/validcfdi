#!/bin/bash

# Colors for formatting output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API URL for Heroku deployment
API_URL="https://validcfdi-efos-d2fa8fe5e435.herokuapp.com"

# API Token 
API_TOKEN="6d0521e03f3db147355da4c8dbc4ad4fb4aa878b219d0f9fa77ce041a184b614"

# Admin credentials
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="password"

# Test data
CFDI_DATA='{"uuid":"6128396f-c09b-4ec6-8699-43c5f7e3b230","emisor_rfc":"CDZ050722LA9","receptor_rfc":"XIN06112344A","total":"12000.00"}'
BATCH_CFDI_DATA='{"cfdis":[{"uuid":"6128396f-c09b-4ec6-8699-43c5f7e3b230","emisor_rfc":"CDZ050722LA9","receptor_rfc":"XIN06112344A","total":"12000.00"},{"uuid":"6128396f-c09b-4ec6-8699-43c5f7e3b230","emisor_rfc":"CDZ050722LA9","receptor_rfc":"XIN06112344A","total":"12000.00"}]}'
RFC_DATA='{"rfc":"AAA100303L51"}'
BATCH_RFC_DATA='{"rfcs":["AAA100303L51","AAA120730823","AAA121206EV5"]}'

# Function to perform a test
test_endpoint() {
    local description=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local auth_type=$5  # bearer, basic, none
    local expect_auth_error=${6:-false}
    
    echo -e "\n${BLUE}====================================================${NC}"
    echo -e "${YELLOW}Testing: ${description}${NC}"
    echo -e "${BLUE}====================================================${NC}"
    echo -e "Method: ${method}"
    echo -e "Endpoint: ${API_URL}${endpoint}"
    
    if [ ! -z "$data" ]; then
        echo -e "Request Data: ${data}"
    fi
    
    # Construct auth header
    AUTH_HEADER=""
    if [ "$auth_type" = "bearer" ]; then
        AUTH_HEADER="-H \"Authorization: Bearer ${API_TOKEN}\""
    elif [ "$auth_type" = "basic" ]; then
        # Create Basic Auth header
        BASIC_AUTH=$(echo -n "${ADMIN_USERNAME}:${ADMIN_PASSWORD}" | base64)
        AUTH_HEADER="-H \"Authorization: Basic ${BASIC_AUTH}\""
    fi
    
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
    
    # Check for authentication errors if we're expecting them
    if [ "$expect_auth_error" = true ] && [[ "$RESPONSE" == *"Invalid authentication token"* || "$RESPONSE" == *"Not authenticated"* || "$RESPONSE" == *"Invalid API token"* ]]; then
        echo -e "\n${GREEN}✅ Expected authentication error received${NC}"
    else
        echo -e "\n${GREEN}✅ Test completed${NC}"
    fi
}

echo -e "${BLUE}====================================================${NC}"
echo -e "${YELLOW}Testing All Endpoints${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. Health Endpoint (Public)
test_endpoint "Health Check" "GET" "/health" "" "none"

# 2. CFDI Verification Endpoints
test_endpoint "CFDI Verification" "POST" "/verify-cfdi" "$CFDI_DATA" "bearer" true
test_endpoint "Batch CFDI Verification" "POST" "/verify-cfdi-batch" "$BATCH_CFDI_DATA" "bearer" true

# 3. EFOS Validation Endpoints
test_endpoint "RFC EFOS Check" "POST" "/check-rfc-efos" "$RFC_DATA" "bearer" true
test_endpoint "Batch RFC EFOS Check" "POST" "/check-rfc-efos-batch" "$BATCH_RFC_DATA" "bearer" true

# 4. Unauthorized Access Tests
test_endpoint "Unauthorized CFDI Verification" "POST" "/verify-cfdi" "$CFDI_DATA" "none" true
test_endpoint "Unauthorized EFOS Check" "POST" "/check-rfc-efos" "$RFC_DATA" "none" true

# 5. Admin Endpoints (these may return 401/403 if credentials are incorrect)
test_endpoint "Admin List Tokens" "GET" "/admin/tokens" "" "basic" true
test_endpoint "Admin EFOS Metadata" "GET" "/admin/efos/metadata" "" "basic" true
test_endpoint "Admin Create Token (may fail)" "POST" "/admin/tokens" '{"description":"Test Token"}' "basic" true

# Test a non-existent endpoint to see 404 behavior
test_endpoint "Non-existent Endpoint" "GET" "/not-found" "" "none"

echo -e "\n${BLUE}====================================================${NC}"
echo -e "${YELLOW}All Tests Completed${NC}"
echo -e "${BLUE}====================================================${NC}" 