#!/bin/bash

# Smoke Test Runner Script
# This script runs the critical smoke tests before launch

set -e  # Exit on any error

echo "🚀 Starting Smoke Test Runner"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="$PROJECT_DIR/tests"
SMOKE_TEST="$TEST_DIR/smoke.py"

# Check if smoke test exists
if [ ! -f "$SMOKE_TEST" ]; then
    echo -e "${RED}❌ Smoke test file not found: $SMOKE_TEST${NC}"
    exit 1
fi

echo -e "${BLUE}📁 Project directory: $PROJECT_DIR${NC}"
echo -e "${BLUE}🧪 Smoke test: $SMOKE_TEST${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found${NC}"
    exit 1
fi

echo -e "${BLUE}🐍 Python version: $(python3 --version)${NC}"

# Check pytest
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}⚠️ pytest not found, installing...${NC}"
    pip3 install pytest
fi

# Check required modules
echo ""
echo -e "${BLUE}🔍 Checking required modules...${NC}"

required_modules=(
    "services.pack_youtube"
    "services.trade_service" 
    "services.rate_limiter"
    "services.refund_service"
    "models.card"
    "models.artist"
    "models.purchase"
    "models.trade"
)

missing_modules=()
for module in "${required_modules[@]}"; do
    if ! python3 -c "import $module" 2>/dev/null; then
        missing_modules+=("$module")
    fi
done

if [ ${#missing_modules[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing required modules:${NC}"
    for module in "${missing_modules[@]}"; do
        echo -e "${RED}   - $module${NC}"
    done
    echo ""
    echo -e "${YELLOW}💡 Make sure you're in the project directory with PYTHONPATH set${NC}"
    echo -e "${YELLOW}💡 Try: export PYTHONPATH=$PROJECT_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All required modules found${NC}"

# Check environment
echo ""
echo -e "${BLUE}🌍 Checking environment...${NC}"

if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}⚠️ DATABASE_URL not set, using default${NC}"
fi

if [ -z "$REDIS_URL" ]; then
    echo -e "${YELLOW}⚠️ REDIS_URL not set, using default${NC}"
fi

# Run the smoke tests
echo ""
echo -e "${BLUE}🧪 Running Smoke Tests...${NC}"
echo "================================"

cd "$PROJECT_DIR"

# Set PYTHONPATH to include project directory
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Run pytest with smoke tests
if python3 -m pytest "$SMOKE_TEST" -v --tb=short --color=yes; then
    echo ""
    echo "================================"
    echo -e "${GREEN}🎉 ALL SMOKE TESTS PASSED!${NC}"
    echo -e "${GREEN}✅ System is ready for launch${NC}"
    echo ""
    echo -e "${BLUE}📋 Test Results:${NC}"
    echo -e "${GREEN}   ✅ Black Guarantee${NC}"
    echo -e "${GREEN}   ✅ Legendary Cap${NC}"
    echo -e "${GREEN}   ✅ Parallel Safety${NC}"
    echo -e "${GREEN}   ✅ Trade Atomic${NC}"
    echo -e "${GREEN}   ✅ Rate Limit${NC}"
    echo -e "${GREEN}   ✅ Refund Revoke${NC}"
    echo ""
    echo -e "${GREEN}🚀 PROCEED WITH DEPLOYMENT!${NC}"
    exit 0
else
    echo ""
    echo "================================"
    echo -e "${RED}❌ SMOKE TESTS FAILED!${NC}"
    echo -e "${RED}🚫 System NOT ready for launch${NC}"
    echo ""
    echo -e "${YELLOW}🔧 Next steps:${NC}"
    echo -e "${YELLOW}   1. Fix failing tests${NC}"
    echo -e "${YELLOW}   2. Verify business logic${NC}"
    echo -e "${YELLOW}   3. Re-run smoke tests${NC}"
    echo -e "${YELLOW}   4. Only deploy when all tests pass${NC}"
    echo ""
    echo -e "${RED}🛑 DO NOT DEPLOY!${NC}"
    exit 1
fi
