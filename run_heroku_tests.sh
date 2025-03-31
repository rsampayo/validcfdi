#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Heroku app name
HEROKU_APP_NAME="validcfdi-api"

echo -e "${BLUE}====================================================${NC}"
echo -e "${YELLOW}Running CFDI API Tests on Heroku${NC}"
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

# Run Python tests on Heroku
echo -e "${BLUE}====================================================${NC}"
echo -e "${YELLOW}Running API tests...${NC}"
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
HEROKU_API_URL="https://$HEROKU_APP_NAME-be42092ab7e2.herokuapp.com"
echo -e "Using API URL: ${GREEN}$HEROKU_API_URL${NC}"

# Get admin credentials from Heroku config
ADMIN_PASSWORD=$(heroku config:get SUPERADMIN_PASSWORD --app $HEROKU_APP_NAME)
ADMIN_USERNAME=$(heroku config:get SUPERADMIN_USERNAME --app $HEROKU_APP_NAME || echo "admin")

if [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${YELLOW}Warning: Could not find SUPERADMIN_PASSWORD in Heroku config. Using default 'caragram'.${NC}"
    ADMIN_PASSWORD="caragram"
fi

# Run the Python tests directly without using --url since it's causing issues
echo -e "${YELLOW}Running Python tests against Heroku...${NC}"
# Set the environment variables and run the tests
HEROKU_API_URL="$HEROKU_API_URL" HEROKU_ADMIN_USERNAME="$ADMIN_USERNAME" HEROKU_ADMIN_PASSWORD="$ADMIN_PASSWORD" python tests/run_heroku_tests.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}All tests passed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Tests failed.${NC}"
    exit 1
fi 