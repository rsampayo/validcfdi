# CFDI API Test Suite

This document explains the comprehensive test suite created for the ValidCFDI API, which includes tests for both local development and Heroku deployments.

## Test Suite Structure

```
tests/
  ├── local/              # Tests for local development
  │   ├── test_api.py     # API endpoint tests (CFDI and EFOS)
  │   └── test_admin.py   # Admin endpoint tests (tokens and metadata)
  ├── heroku/             # Tests for Heroku deployment
  │   ├── test_api.py     # API endpoint tests for Heroku
  │   └── test_admin.py   # Admin endpoint tests for Heroku
  ├── run_local_tests.py  # Script to run all local tests
  ├── run_heroku_tests.py # Script to run all Heroku tests (no pytest fixtures)
  └── requirements.txt    # Dependencies for testing

run_heroku_tests.sh       # Shell script to run Heroku tests via CLI
```

## Test Coverage

The test suite covers:

1. **API Endpoints**:
   - Health check
   - CFDI verification (single and batch)
   - EFOS verification (single and batch)
   - Authentication checks

2. **Admin Endpoints**:
   - Token management (list, create, regenerate, delete)
   - EFOS metadata viewing

## Running Tests

### Local Development Tests

1. Install dependencies:
   ```bash
   pip install -r tests/requirements.txt
   ```

2. Start your local API server:
   ```bash
   uvicorn main:app --reload
   ```

3. Run the local tests:
   ```bash
   python tests/run_local_tests.py
   ```

### Heroku Deployment Tests

There are two ways to run the Heroku tests:

#### Using the Shell Script (Recommended)

The shell script automatically:
- Checks if the necessary Heroku dynos are running
- Starts them if needed
- Gets the proper admin credentials from Heroku config
- Runs the tests

```bash
./run_heroku_tests.sh
```

#### Using the Python Script Directly

```bash
python tests/run_heroku_tests.py
```

You can also specify custom parameters:

```bash
python tests/run_heroku_tests.py --url https://your-app.herokuapp.com --token your-api-token --admin-user admin --admin-password your-password
```

## Running Individual Tests

You can also run individual test modules:

```bash
# Local API tests
pytest tests/local/test_api.py -v

# Local Admin tests
pytest tests/local/test_admin.py -v

# Heroku tests (direct execution)
python tests/heroku/test_api.py
python tests/heroku/test_admin.py
```

## Environment Variables

For the tests to work properly, you might need to set these environment variables:

### For Local Testing
```
TEST_API_TOKEN=your-test-token
SUPERADMIN_USERNAME=admin
SUPERADMIN_PASSWORD=your-admin-password
```

### For Heroku Testing
```
HEROKU_API_URL=https://your-app-name.herokuapp.com
HEROKU_API_TOKEN=your-heroku-api-token
HEROKU_ADMIN_USERNAME=admin
HEROKU_ADMIN_PASSWORD=your-heroku-admin-password
```

Note: The shell script will retrieve most of these values automatically from your Heroku config.

## Troubleshooting

If you encounter issues with the tests:

1. **Local tests failing**: Make sure your local server is running and the database is properly set up.

2. **Heroku tests failing**: 
   - Check if the web and worker dynos are running (`heroku ps --app validcfdi-api`)
   - Verify your admin credentials (`heroku config:get SUPERADMIN_PASSWORD --app validcfdi-api`)
   - Ensure the EFOS database has been downloaded (worker dyno should handle this)

3. **Authentication issues**: Double-check your API tokens and admin credentials.

## Extending the Tests

When adding new endpoints to the API, remember to:

1. Add corresponding tests to both local and Heroku test files
2. Update the runner scripts as needed
3. Test both locally and on Heroku to ensure everything works

This comprehensive test suite helps ensure that your ValidCFDI API functions correctly in both local development and production Heroku environments. 