# CFDI API Test Suite

This directory contains tests for the CFDI API, both for local testing and Heroku deployment testing.

## Structure

```
tests/
  ├── local/            # Tests for local development
  │   ├── test_api.py   # API endpoint tests
  │   └── test_admin.py # Admin API tests
  ├── heroku/           # Tests for Heroku deployment
  │   ├── test_api.py   # API endpoint tests
  │   └── test_admin.py # Admin API tests
  ├── run_local_tests.py  # Script to run all local tests
  ├── run_heroku_tests.py # Script to run all Heroku tests
  └── requirements.txt    # Dependencies for testing
```

## Prerequisites

1. Install the test dependencies:

```bash
pip install -r tests/requirements.txt
```

2. Make sure you have the necessary environment variables set:

   - For local testing:
     - Create a `.env` file in the project root with:
       ```
       TEST_API_TOKEN=your-test-token
       SUPERADMIN_USERNAME=admin
       SUPERADMIN_PASSWORD=your-admin-password
       ```

   - For Heroku testing:
     - Either set these environment variables:
       ```
       HEROKU_API_URL=https://your-app-name.herokuapp.com
       HEROKU_API_TOKEN=your-heroku-api-token
       HEROKU_ADMIN_USERNAME=admin
       HEROKU_ADMIN_PASSWORD=your-heroku-admin-password
       ```
     - Or they will be fetched from Heroku configuration when using the shell script.

## Running Tests

### Local Tests

1. Make sure your local API server is running:

```bash
uvicorn main:app --reload
```

2. Run the tests:

```bash
python tests/run_local_tests.py
```

### Heroku Tests

#### Using Python Script

```bash
python tests/run_heroku_tests.py
```

You can also specify the Heroku app URL and credentials:

```bash
python tests/run_heroku_tests.py --url https://your-app.herokuapp.com --token your-api-token --admin-user admin --admin-password your-password
```

#### Using Shell Script

This automatically checks and starts the necessary dynos, and gets credentials from Heroku:

```bash
./run_heroku_tests.sh
```

## Running Individual Tests

You can also run individual test modules with pytest:

```bash
# Local API tests
pytest tests/local/test_api.py -v

# Local Admin tests
pytest tests/local/test_admin.py -v

# Heroku tests must be run directly since they have a __main__ function
python tests/heroku/test_api.py
python tests/heroku/test_admin.py
``` 