#!/bin/bash

# Colors for formatting output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API URL for Heroku deployment
API_URL="https://validcfdi-api-be42092ab7e2.herokuapp.com"

# API Token from Heroku database
API_TOKEN="c822cf5ee82316013d21d912d95c5a770f86bd4ed278a8a33e729609e387efa4"

# Create the EFOS RFCs batch data using the provided RFCs
BATCH_RFC_DATA='{
  "rfcs": [
    "AAA100303L51",
    "AAA120730823",
    "AAA121206EV5",
    "AAA140116926",
    "AAA1502061S0",
    "AAA151209DYA",
    "AAAA620217U54",
    "AAAE910314EJ7",
    "AAAG7012036UA",
    "AAAJ830204PA9",
    "AAAL440727T22"
  ]
}'

# Individual RFC tests
INDIVIDUAL_RFCS=(
  "AAA100303L51"
  "AAA120730823"
  "AAA121206EV5"
)

echo -e "${BLUE}====================================================${NC}"
echo -e "${YELLOW}Testing EFOS Verification Endpoints${NC}"
echo -e "${BLUE}====================================================${NC}"

# Test health endpoint first
echo -e "\n${BLUE}====================================================${NC}"
echo -e "${YELLOW}Testing: Health Check${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "Endpoint: GET ${API_URL}/health"

RESPONSE=$(curl -s -X GET ${API_URL}/health)
echo -e "\nResponse:"
echo $RESPONSE | jq '.' 2>/dev/null || echo $RESPONSE
echo -e "${GREEN}✅ Health check completed${NC}"

# Test batch RFC EFOS verification
echo -e "\n${BLUE}====================================================${NC}"
echo -e "${YELLOW}Testing: Batch RFC EFOS Verification${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "Endpoint: POST ${API_URL}/check-rfc-efos-batch"
echo -e "Request Data: ${BATCH_RFC_DATA}"

RESPONSE=$(curl -s -X POST ${API_URL}/check-rfc-efos-batch \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${BATCH_RFC_DATA}")

echo -e "\nResponse:"
echo $RESPONSE | jq '.' 2>/dev/null || echo $RESPONSE

if [[ $(echo $RESPONSE | grep -c "Not Found") -gt 0 ]]; then
  echo -e "\n${YELLOW}⚠️ Endpoint returned 'Not Found' - this may indicate no records found in EFOS database${NC}"
else
  echo -e "\n${GREEN}✅ EFOS Batch Test completed${NC}"
fi

# Test individual RFCs one by one
echo -e "\n${BLUE}====================================================${NC}"
echo -e "${YELLOW}Testing: Individual RFC EFOS Verification${NC}"
echo -e "${BLUE}====================================================${NC}"

for RFC in "${INDIVIDUAL_RFCS[@]}"; do
  echo -e "\n${BLUE}---------------------------------------------------${NC}"
  echo -e "${YELLOW}Testing RFC: ${RFC}${NC}"
  echo -e "Endpoint: POST ${API_URL}/check-rfc-efos"
  
  RFC_DATA="{\"rfc\":\"${RFC}\"}"
  echo -e "Request Data: ${RFC_DATA}"
  
  RESPONSE=$(curl -s -X POST ${API_URL}/check-rfc-efos \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${RFC_DATA}")
  
  echo -e "\nResponse:"
  echo $RESPONSE | jq '.' 2>/dev/null || echo $RESPONSE
  
  if [[ $(echo $RESPONSE | grep -c "Not Found") -gt 0 ]]; then
    echo -e "${YELLOW}⚠️ RFC not found in EFOS database${NC}"
  else
    echo -e "${GREEN}✅ Test completed${NC}"
  fi
done

echo -e "\n${BLUE}====================================================${NC}"
echo -e "${YELLOW}Test Summary${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "All EFOS tests completed." 