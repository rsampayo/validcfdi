#!/bin/bash

# Colors for formatting output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API URL - Updated to correct validcfdi-efos-api URL
API_URL="https://validcfdi-efos-api-dbb1860f8896.herokuapp.com"

# API Token
API_TOKEN="c822cf5ee82316013d21d912d95c5a770f86bd4ed278a8a33e729609e387efa4"

# Test data
CFDI_DATA='{"uuid":"6128396f-c09b-4ec6-8699-43c5f7e3b230","emisor_rfc":"CDZ050722LA9","receptor_rfc":"XIN06112344A","total":"12000.00"}'
BATCH_CFDI_DATA='{"cfdis":[{"uuid":"6128396f-c09b-4ec6-8699-43c5f7e3b230","emisor_rfc":"CDZ050722LA9","receptor_rfc":"XIN06112344A","total":"12000.00"},{"uuid":"6128396f-c09b-4ec6-8699-43c5f7e3b230","emisor_rfc":"CDZ050722LA9","receptor_rfc":"XIN06112344A","total":"12000.00"}]}'
RFC_DATA='{"rfc":"CDZ050722LA9"}'
BATCH_RFC_DATA='{"rfcs":["CDZ050722LA9","XIN06112344A"]}'

# Function to make API calls and display results
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    local auth=${5:-true}
    
    echo -e "\n${BLUE}====================================================${NC}"
    echo -e "${YELLOW}Testing: ${description}${NC}"
    echo -e "${BLUE}====================================================${NC}"
    echo -e "Endpoint: ${method} ${API_URL}${endpoint}"
    
    if [ ! -z "$data" ]; then
        echo -e "Request Data: ${data}"
    fi
    
    # Build curl command
    CURL_CMD="curl -s -X ${method} ${API_URL}${endpoint}"
    
    # Add authentication header if required
    if [ "$auth" = true ]; then
        CURL_CMD="$CURL_CMD -H \"Authorization: Bearer ${API_TOKEN}\""
    fi
    
    # Add content type and data for POST requests
    if [ "$method" = "POST" ]; then
        CURL_CMD="$CURL_CMD -H \"Content-Type: application/json\""
        if [ ! -z "$data" ]; then
            CURL_CMD="$CURL_CMD -d '${data}'"
        fi
    fi
    
    # Execute and capture response
    echo -e "\nExecuting: ${CURL_CMD}"
    
    # We need to use eval because the command contains quotes
    RESPONSE=$(eval $CURL_CMD)
    STATUS=$?
    
    # Display response
    echo -e "\nResponse:"
    if [ $STATUS -eq 0 ]; then
        # Show raw response without JSON parsing
        echo "$RESPONSE"
        
        if [ ! -z "$RESPONSE" ]; then
            echo -e "\n${GREEN}✅ Response received${NC}"
        else
            echo -e "\n${RED}❌ Empty response${NC}"
        fi
    else
        echo -e "${RED}Failed to connect to the API. Status code: $STATUS${NC}"
    fi
    
    echo -e "${BLUE}====================================================${NC}"
}

# Run tests for various endpoints

# 1. Health endpoint
test_endpoint "GET" "/health" "" "Health Check" false

# 2. Verify CFDI endpoint
test_endpoint "POST" "/verify-cfdi" "$CFDI_DATA" "Verify CFDI"

# 3. Verify CFDI Batch endpoint
test_endpoint "POST" "/verify-cfdi-batch" "$BATCH_CFDI_DATA" "Verify CFDI Batch"

# 4. Check RFC in EFOS list
test_endpoint "POST" "/check-rfc-efos" "$RFC_DATA" "Check RFC in EFOS List"

# 5. Check RFC Batch in EFOS list
test_endpoint "POST" "/check-rfc-efos-batch" "$BATCH_RFC_DATA" "Check RFC Batch in EFOS List"

# 6. Test unauthorized access (no token)
test_endpoint "POST" "/verify-cfdi" "$CFDI_DATA" "Unauthorized Access (No Token)" false

# Print summary
echo -e "\n${BLUE}====================================================${NC}"
echo -e "${YELLOW}Test Summary${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "All tests completed. Check results above for any failures." 