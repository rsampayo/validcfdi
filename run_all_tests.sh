#!/bin/bash

# Colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${YELLOW}Running all tests for CFDI Verification API${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Run basic API tests
echo -e "\n${BLUE}======================================================${NC}"
echo -e "${YELLOW}1. Running basic API tests (test_api.py)${NC}"
echo -e "${BLUE}======================================================${NC}"
python -m pytest test_api.py -v

# 2. Run Heroku tests
echo -e "\n${BLUE}======================================================${NC}"
echo -e "${YELLOW}2. Running Heroku deployment tests (test_heroku.py)${NC}"
echo -e "${BLUE}======================================================${NC}"
python test_heroku.py

# 3. Run main API tests
echo -e "\n${BLUE}======================================================${NC}"
echo -e "${YELLOW}3. Running main API tests (test_main.py)${NC}"
echo -e "${BLUE}======================================================${NC}"
python -m pytest test_main.py::test_health_check test_main.py::test_verify_cfdi_unauthorized test_main.py::test_verify_cfdi_with_invalid_token -v

# 4. Run admin API tests
echo -e "\n${BLUE}======================================================${NC}"
echo -e "${YELLOW}4. Running admin API tests (test_admin_api.py)${NC}"
echo -e "${BLUE}======================================================${NC}"
python -m pytest test_admin_api.py::test_create_token -v

echo -e "\n${BLUE}======================================================${NC}"
echo -e "${YELLOW}All tests completed!${NC}"
echo -e "${BLUE}======================================================${NC}" 