#!/bin/bash

# Production Readiness Test Script
# Verifies all checklist-critical items are working

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚦 PRODUCTION READINESS CHECK${NC}"
echo "================================"
echo "Timestamp: $(date)"
echo ""

# Function to run test and check result
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${BLUE}🧪 Testing: $test_name${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ $test_name - PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ $test_name - FAILED${NC}"
        return 1
    fi
}

# Function to check if service is running
check_service() {
    local service_name="$1"
    local check_command="$2"
    
    echo -e "${BLUE}🔍 Checking service: $service_name${NC}"
    
    if eval "$check_command"; then
        echo -e "${GREEN}✅ $service_name - RUNNING${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name - NOT RUNNING${NC}"
        return 1
    fi
}

# Function to check configuration
check_config() {
    local config_name="$1"
    local config_var="$2"
    
    echo -e "${BLUE}⚙️  Checking config: $config_name${NC}"
    
    if [ -n "${!config_var}" ]; then
        echo -e "${GREEN}✅ $config_name - CONFIGURED${NC}"
        return 0
    else
        echo -e "${RED}❌ $config_name - NOT CONFIGURED${NC}"
        return 1
    fi
}

echo -e "${BLUE}📋 1. SMOKE TESTS${NC}"
echo "-------------------"

# Run smoke tests
if run_test "Smoke Test Suite" "python -m pytest tests/smoke.py -v --tb=short"; then
    SMOKE_TESTS_PASSED=true
else
    SMOKE_TESTS_PASSED=false
fi

echo ""
echo -e "${BLUE}🔄 2. RESTORE DRILL${NC}"
echo "---------------------"

# Check restore drill script exists
if [ -f "scripts/restore_drill.sh" ]; then
    echo -e "${GREEN}✅ Restore drill script exists${NC}"
    
    # Check if script is executable
    if [ -x "scripts/restore_drill.sh" ]; then
        echo -e "${GREEN}✅ Restore drill script is executable${NC}"
    else
        echo -e "${YELLOW}⚠️  Restore drill script not executable${NC}"
        chmod +x scripts/restore_drill.sh
        echo -e "${GREEN}✅ Made restore drill script executable${NC}"
    fi
    
    # Check backup directory
    if [ -n "$BACKUP_PATH" ] && [ -d "$BACKUP_PATH" ]; then
        echo -e "${GREEN}✅ Backup directory exists: $BACKUP_PATH${NC}"
        
        # Check for backups
        if [ "$(ls -A $BACKUP_PATH/db 2>/dev/null)" ]; then
            BACKUP_COUNT=$(ls $BACKUP_PATH/db/*.sql 2>/dev/null | wc -l)
            echo -e "${GREEN}✅ Found $BACKUP_COUNT backup files${NC}"
        else
            echo -e "${YELLOW}⚠️  No backup files found${NC}"
        fi
    else
        echo -e "${RED}❌ Backup directory not found or not configured${NC}"
    fi
    
    # Check CI workflow exists
    if [ -f ".github/workflows/restore.yml" ]; then
        echo -e "${GREEN}✅ Restore drill CI workflow exists${NC}"
    else
        echo -e "${RED}❌ Restore drill CI workflow missing${NC}"
    fi
    
    RESTORE_DRILL_READY=true
else
    echo -e "${RED}❌ Restore drill script missing${NC}"
    RESTORE_DRILL_READY=false
fi

echo ""
echo -e "${BLUE}🌐 3. PAYMENT GATEWAY${NC}"
echo "----------------------"

# Check webhook endpoint file exists
if [ -f "app.py" ]; then
    echo -e "${GREEN}✅ Webhook application exists${NC}"
    
    # Check webhook adapter exists
    if [ -f "webhooks/payments.py" ]; then
        echo -e "${GREEN}✅ Payment webhook adapter exists${NC}"
    else
        echo -e "${RED}❌ Payment webhook adapter missing${NC}"
    fi
    
    # Check gateway adapters exist
    if [ -f "webhooks/gateways/stripe_adapter.py" ]; then
        echo -e "${GREEN}✅ Stripe adapter exists${NC}"
    else
        echo -e "${RED}❌ Stripe adapter missing${NC}"
    fi
    
    if [ -f "webhooks/gateways/paypal_adapter.py" ]; then
        echo -e "${GREEN}✅ PayPal adapter exists${NC}"
    else
        echo -e "${RED}❌ PayPal adapter missing${NC}"
    fi
    
    # Check configuration
    check_config "Stripe Webhook Secret" "STRIPE_WEBHOOK_SECRET"
    check_config "PayPal Webhook ID" "PAYPAL_WEBHOOK_ID"
    
    GATEWAY_READY=true
else
    echo -e "${RED}❌ Webhook application missing${NC}"
    GATEWAY_READY=false
fi

echo ""
echo -e "${BLUE}🧪 4. PAYMENT FLOW TESTS${NC}"
echo "------------------------"

# Run payment flow tests
if run_test "Payment Flow Tests" "python -m pytest tests/payment_flow.py -v --tb=short"; then
    PAYMENT_TESTS_PASSED=true
else
    PAYMENT_TESTS_PASSED=false
fi

# Run production readiness tests specifically
if run_test "Production Readiness Tests" "python tests/payment_flow.py production"; then
    PROD_TESTS_PASSED=true
else
    PROD_TESTS_PASSED=false
fi

echo ""
echo -e "${BLUE}🔧 5. ENVIRONMENT CHECKS${NC}"
echo "------------------------"

# Check Python environment
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ Python: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python not found${NC}"
fi

# Check required packages
echo -e "${BLUE}📦 Checking required packages...${NC}"
REQUIRED_PACKAGES=("pytest" "flask" "psycopg2-binary" "redis")
PACKAGES_OK=true

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "${GREEN}✅ $package${NC}"
    else
        echo -e "${RED}❌ $package${NC}"
        PACKAGES_OK=false
    fi
done

# Check environment variables
echo -e "${BLUE}🌍 Checking environment variables...${NC}"
REQUIRED_VARS=("DATABASE_URL" "REDIS_URL")
VARS_OK=true

for var in "${REQUIRED_VARS[@]}"; do
    check_config "$var" "$var"
    if [ $? -ne 0 ]; then
        VARS_OK=false
    fi
done

echo ""
echo -e "${BLUE}📊 6. SERVICES STATUS${NC}"
echo "----------------------"

# Check database connectivity
if check_service "Database" "python3 -c \"import psycopg2; conn = psycopg2.connect('$DATABASE_URL'); conn.close()\""; then
    DB_OK=true
else
    DB_OK=false
fi

# Check Redis connectivity
if check_service "Redis" "python3 -c \"import redis; r = redis.from_url('$REDIS_URL'); r.ping()\""; then
    REDIS_OK=true
else
    REDIS_OK=false
fi

echo ""
echo -e "${BLUE}📋 PRODUCTION READINESS SUMMARY${NC}"
echo "=================================="

# Calculate overall status
ALL_CHECKS_PASSED=true

echo -e "${BLUE}🧪 Smoke Tests:${NC}"
if [ "$SMOKE_TESTS_PASSED" = true ]; then
    echo -e "   ${GREEN}✅ PASSED${NC}"
else
    echo -e "   ${RED}❌ FAILED${NC}"
    ALL_CHECKS_PASSED=false
fi

echo -e "${BLUE}🔄 Restore Drill:${NC}"
if [ "$RESTORE_DRILL_READY" = true ]; then
    echo -e "   ${GREEN}✅ READY${NC}"
else
    echo -e "   ${RED}❌ NOT READY${NC}"
    ALL_CHECKS_PASSED=false
fi

echo -e "${BLUE}🌐 Payment Gateway:${NC}"
if [ "$GATEWAY_READY" = true ]; then
    echo -e "   ${GREEN}✅ READY${NC}"
else
    echo -e "   ${RED}❌ NOT READY${NC}"
    ALL_CHECKS_PASSED=false
fi

echo -e "${BLUE}🧪 Payment Tests:${NC}"
if [ "$PAYMENT_TESTS_PASSED" = true ] && [ "$PROD_TESTS_PASSED" = true ]; then
    echo -e "   ${GREEN}✅ PASSED${NC}"
else
    echo -e "   ${RED}❌ FAILED${NC}"
    ALL_CHECKS_PASSED=false
fi

echo -e "${BLUE}🔧 Environment:${NC}"
if [ "$PACKAGES_OK" = true ] && [ "$VARS_OK" = true ]; then
    echo -e "   ${GREEN}✅ OK${NC}"
else
    echo -e "   ${RED}❌ ISSUES FOUND${NC}"
    ALL_CHECKS_PASSED=false
fi

echo -e "${BLUE}📊 Services:${NC}"
if [ "$DB_OK" = true ] && [ "$REDIS_OK" = true ]; then
    echo -e "   ${GREEN}✅ RUNNING${NC}"
else
    echo -e "   ${RED}❌ SOME SERVICES DOWN${NC}"
    ALL_CHECKS_PASSED=false
fi

echo ""
echo "=================================="

if [ "$ALL_CHECKS_PASSED" = true ]; then
    echo -e "${GREEN}🎉 PRODUCTION READY!${NC}"
    echo -e "${GREEN}✅ All systems operational${NC}"
    echo -e "${GREEN}✅ Checklist criteria met${NC}"
    echo -e "${GREEN}✅ Ready for launch${NC}"
    echo ""
    echo -e "${BLUE}🚀 NEXT STEPS:${NC}"
    echo -e "   1. Deploy to production${NC}"
    echo -e "   2. Monitor initial traffic${NC}"
    echo -e "   3. Verify webhook endpoints${NC}"
    echo -e "   4. Schedule weekly restore drills${NC}"
    exit 0
else
    echo -e "${RED}❌ NOT PRODUCTION READY${NC}"
    echo -e "${RED}🚫 Fix issues before deployment${NC}"
    echo ""
    echo -e "${YELLOW}🔧 REQUIRED ACTIONS:${NC}"
    
    if [ "$SMOKE_TESTS_PASSED" = false ]; then
        echo -e "   ${YELLOW}• Fix smoke test failures${NC}"
    fi
    
    if [ "$RESTORE_DRILL_READY" = false ]; then
        echo -e "   ${YELLOW}• Complete restore drill setup${NC}"
    fi
    
    if [ "$GATEWAY_READY" = false ]; then
        echo -e "   ${YELLOW}• Complete payment gateway setup${NC}"
    fi
    
    if [ "$PAYMENT_TESTS_PASSED" = false ] || [ "$PROD_TESTS_PASSED" = false ]; then
        echo -e "   ${YELLOW}• Fix payment flow test failures${NC}"
    fi
    
    if [ "$PACKAGES_OK" = false ] || [ "$VARS_OK" = false ]; then
        echo -e "   ${YELLOW}• Fix environment issues${NC}"
    fi
    
    if [ "$DB_OK" = false ] || [ "$REDIS_OK" = false ]; then
        echo -e "   ${YELLOW}• Start required services${NC}"
    fi
    
    echo ""
    echo -e "${RED}🛑 DO NOT DEPLOY UNTIL ALL ISSUES ARE RESOLVED${NC}"
    exit 1
fi
