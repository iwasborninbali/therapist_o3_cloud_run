# Task: CI Container Test

## Status: done

## Assigned to: gemini_1

## Description
Create a CI testing workflow that verifies the Telegram bot Docker container builds and passes basic tests.

## Requirements
- Create a Docker-based test approach for CI
- Ensure the container can be built and run in a test environment
- Verify basic functionality works within the container
- Document the testing process

## Files to modify/create
- tests/test_container.py
- .github/workflows/container-test.yml (if applicable)
- Update README.md with CI testing instructions

## Acceptance Criteria
- Tests verify the Docker container builds successfully
- Container starts and exposes expected endpoints
- Health check endpoint returns 200 OK
- README includes instructions for running container tests locally

## Implementation Notes
- Created `tests/test_container.py` with Docker container tests
- Added docker and requests packages to requirements.txt
- Updated README.md with container testing instructions
- Implemented pytest fixtures for Docker resource management
- Added retry logic for potentially flaky network tests
- Added ability to skip container tests via SKIP_CONTAINER_TESTS environment variable 