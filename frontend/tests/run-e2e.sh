#!/bin/bash

# Location Tracker E2E Test Runner
# This script manages the full E2E testing process including dev server startup

set -e

# Configuration
DEV_SERVER_PORT=5173
DEV_SERVER_URL="http://localhost:$DEV_SERVER_PORT"
TIMEOUT=60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if dev server is already running
check_server() {
    if curl -s "$DEV_SERVER_URL" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Start dev server
start_dev_server() {
    log_info "Starting development server..."
    npm run dev &
    DEV_SERVER_PID=$!
    
    # Wait for server to start
    local count=0
    while ! check_server && [ $count -lt $TIMEOUT ]; do
        sleep 1
        count=$((count + 1))
        if [ $((count % 5)) -eq 0 ]; then
            log_info "Waiting for dev server... ($count/$TIMEOUT seconds)"
        fi
    done
    
    if check_server; then
        log_success "Development server started on $DEV_SERVER_URL"
        return 0
    else
        log_error "Failed to start development server"
        return 1
    fi
}

# Stop dev server
stop_dev_server() {
    if [ ! -z "$DEV_SERVER_PID" ]; then
        log_info "Stopping development server..."
        kill $DEV_SERVER_PID 2>/dev/null || true
        wait $DEV_SERVER_PID 2>/dev/null || true
        log_success "Development server stopped"
    fi
}

# Cleanup function
cleanup() {
    stop_dev_server
    exit 0
}

# Trap cleanup on script exit
trap cleanup EXIT INT TERM

# Main execution
main() {
    log_info "Starting Location Tracker E2E Test Suite"
    
    # Check if server is already running
    if check_server; then
        log_warning "Development server already running on $DEV_SERVER_URL"
        SERVER_WAS_RUNNING=true
    else
        # Start dev server
        if ! start_dev_server; then
            log_error "Could not start development server"
            exit 1
        fi
        SERVER_WAS_RUNNING=false
    fi
    
    # Run tests based on arguments
    case "${1:-all}" in
        "simple")
            log_info "Running simple tests..."
            npm run test tests/e2e/simple-test.test.ts
            ;;
        "minimal")
            log_info "Running minimal app tests..."
            npm run test tests/e2e/app-minimal.test.ts
            ;;
        "comprehensive")
            log_info "Running comprehensive tests..."
            npm run test tests/e2e/comprehensive.test.ts
            ;;
        "all"|"")
            log_info "Running all E2E tests..."
            npm run test:e2e
            ;;
        *)
            log_error "Unknown test type: $1"
            log_info "Available options: simple, minimal, comprehensive, all"
            exit 1
            ;;
    esac
    
    # Check test results
    if [ $? -eq 0 ]; then
        log_success "All tests passed!"
    else
        log_error "Some tests failed!"
        exit 1
    fi
    
    # Only stop server if we started it
    if [ "$SERVER_WAS_RUNNING" = false ]; then
        stop_dev_server
    fi
}

# Help function
show_help() {
    echo "Location Tracker E2E Test Runner"
    echo ""
    echo "Usage: $0 [test-type]"
    echo ""
    echo "Test types:"
    echo "  simple        - Run basic functionality tests"
    echo "  minimal       - Run minimal app interaction tests"  
    echo "  comprehensive - Run full comprehensive test suite"
    echo "  all           - Run all E2E tests (default)"
    echo ""
    echo "Examples:"
    echo "  $0                # Run all tests"
    echo "  $0 comprehensive  # Run comprehensive test suite"
    echo "  $0 simple         # Run simple tests only"
}

# Check for help flag
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

# Run main function
main "$@"