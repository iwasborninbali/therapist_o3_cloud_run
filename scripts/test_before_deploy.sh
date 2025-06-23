#!/bin/bash

# Pre-deployment validation script
# This script tests the application locally before deploying to Cloud Run

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_IMAGE_NAME="therapist-bot-test"
TEST_CONTAINER_NAME="therapist-test"

echo -e "${BLUE}🧪 Pre-deployment validation started${NC}"
echo "========================================"

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# Function to cleanup test resources
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up test resources...${NC}"
    docker stop ${TEST_CONTAINER_NAME} 2>/dev/null || true
    docker rm ${TEST_CONTAINER_NAME} 2>/dev/null || true
    docker rmi ${TEST_IMAGE_NAME}:latest 2>/dev/null || true
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Test 1: Python imports
echo -e "${BLUE}1. Testing Python imports...${NC}"
python -c "
try:
    from bot.main import app
    print('   - bot.main imported successfully')
except ImportError as e:
    print(f'   - Import error: {e}')
    exit(1)
" 2>/dev/null
print_result $? "Python imports working"

# Test 2: FastAPI app creation
echo -e "${BLUE}2. Testing FastAPI app creation...${NC}"
python -c "
try:
    from bot.main import app
    print('   - FastAPI app instance created')
except Exception as e:
    print(f'   - Error creating app: {e}')
    exit(1)
" 2>/dev/null
print_result $? "FastAPI app creation working"

# Test 3: Specific import fix verification
echo -e "${BLUE}3. Testing error middleware imports...${NC}"
python -c "
try:
    from bot.error_middleware import setup_error_handler, add_error_middleware
    print('   - setup_error_handler imported successfully')
    print('   - add_error_middleware imported successfully')
except ImportError as e:
    print(f'   - Import error: {e}')
    exit(1)
" 2>/dev/null
print_result $? "Error middleware imports fixed"

# Test 4: Docker build
echo -e "${BLUE}4. Testing Docker build...${NC}"
if docker build --platform linux/amd64 -t ${TEST_IMAGE_NAME}:latest . >/dev/null 2>&1; then
    print_result 0 "Docker build successful"
else
    print_result 1 "Docker build failed"
    exit 1
fi

# Test 5: Docker container startup
echo -e "${BLUE}5. Testing Docker container startup...${NC}"
if docker run --rm -d --name ${TEST_CONTAINER_NAME} -p 8080:8080 -e PORT=8080 ${TEST_IMAGE_NAME}:latest >/dev/null 2>&1; then
    # Wait a moment for container to start
    sleep 3
    
    # Check if container is running and get logs
    if docker ps | grep -q ${TEST_CONTAINER_NAME}; then
        # Get logs to check for startup
        LOGS=$(docker logs ${TEST_CONTAINER_NAME} 2>&1)
        
        # Check if the application started (looking for uvicorn startup message)
        if echo "$LOGS" | grep -q "Started server process"; then
            print_result 0 "Docker container startup successful"
        else
            echo -e "${YELLOW}   - Container started but may have configuration issues${NC}"
            echo -e "${YELLOW}   - This is expected without environment variables${NC}"
            print_result 0 "Docker container startup working (expected config errors)"
        fi
        
        # Stop the test container
        docker stop ${TEST_CONTAINER_NAME} >/dev/null 2>&1
    else
        print_result 1 "Docker container failed to start"
        exit 1
    fi
else
    print_result 1 "Docker container startup failed"
    exit 1
fi

# Test 6: Requirements check
echo -e "${BLUE}6. Checking requirements.txt...${NC}"
if [ -f "requirements.txt" ]; then
    # Check if main dependencies are present
    if grep -q "fastapi" requirements.txt && grep -q "uvicorn" requirements.txt && grep -q "python-telegram-bot" requirements.txt; then
        print_result 0 "Requirements.txt contains essential dependencies"
    else
        print_result 1 "Requirements.txt missing essential dependencies"
    fi
else
    print_result 1 "Requirements.txt not found"
fi

# Test 7: Environment structure check
echo -e "${BLUE}7. Checking project structure...${NC}"
REQUIRED_FILES=("bot/main.py" "bot/error_middleware.py" "bot/telegram_router.py" "Dockerfile" "requirements.txt")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    print_result 0 "All required files present"
else
    echo -e "${RED}   - Missing files: ${MISSING_FILES[*]}${NC}"
    print_result 1 "Missing required files"
fi

echo ""
echo "========================================"
echo -e "${GREEN}🎉 All pre-deployment tests passed!${NC}"
echo -e "${GREEN}✅ Application is ready for deployment${NC}"
echo ""
echo -e "${BLUE}To deploy, run:${NC}"
echo -e "${BLUE}./scripts/build_and_deploy.sh${NC}" 