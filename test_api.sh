#!/bin/bash

# API Testing Script for Transcription Platform
# This script tests the core functionality of the API

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
TOKEN=""

echo "=================================================="
echo "  Transcription Platform - API Tests"
echo "=================================================="
echo ""

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        echo -e "${YELLOW}  Response: $3${NC}"
    fi
}

# Test 1: Health Check
echo "Test 1: Health Check"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health")
if [ "$RESPONSE" -eq 200 ]; then
    print_result 0 "Health check passed"
else
    print_result 1 "Health check failed" "HTTP $RESPONSE"
    echo "Make sure the backend is running: uvicorn app.main:app"
    exit 1
fi
echo ""

# Test 2: API Docs Available
echo "Test 2: API Documentation"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/docs")
if [ "$RESPONSE" -eq 200 ]; then
    print_result 0 "API docs accessible at $API_URL/docs"
else
    print_result 1 "API docs not accessible" "HTTP $RESPONSE"
fi
echo ""

# Test 3: Register User
echo "Test 3: User Registration"
REGISTER_EMAIL="test_$(date +%s)@example.com"
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$REGISTER_EMAIL\",
        \"password\": \"TestPassword123!\",
        \"first_name\": \"Test\",
        \"last_name\": \"User\"
    }")

if echo "$REGISTER_RESPONSE" | grep -q "id"; then
    print_result 0 "User registration successful"
else
    print_result 1 "User registration failed" "$REGISTER_RESPONSE"
fi
echo ""

# Test 4: Login
echo "Test 4: User Login"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$REGISTER_EMAIL\",
        \"password\": \"TestPassword123!\"
    }")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    print_result 0 "User login successful"
else
    print_result 1 "User login failed" "$LOGIN_RESPONSE"
    TOKEN=""
fi
echo ""

if [ -z "$TOKEN" ]; then
    echo -e "${YELLOW}Warning: No authentication token available${NC}"
    echo "Skipping authenticated endpoint tests"
    echo ""
else
    # Test 5: Get User Profile
    echo "Test 5: Get User Profile"
    PROFILE_RESPONSE=$(curl -s -X GET "$API_URL/api/users/me" \
        -H "Authorization: Bearer $TOKEN")

    if echo "$PROFILE_RESPONSE" | grep -q "email"; then
        print_result 0 "User profile retrieved successfully"
    else
        print_result 1 "User profile retrieval failed" "$PROFILE_RESPONSE"
    fi
    echo ""

    # Test 6: List Transcriptions
    echo "Test 6: List Transcriptions"
    TRANSCRIPTIONS_RESPONSE=$(curl -s -X GET "$API_URL/api/transcriptions/list" \
        -H "Authorization: Bearer $TOKEN")

    if echo "$TRANSCRIPTIONS_RESPONSE" | grep -q "\[\]"; then
        print_result 0 "Transcriptions list retrieved (empty)"
    elif echo "$TRANSCRIPTIONS_RESPONSE" | grep -q "items"; then
        print_result 0 "Transcriptions list retrieved"
    else
        print_result 1 "Transcriptions list failed" "$TRANSCRIPTIONS_RESPONSE"
    fi
    echo ""

    # Test 7: Rate Limit Stats (if available)
    echo "Test 7: Rate Limit Statistics"
    RATE_LIMIT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "$API_URL/api/rate-limit/stats" \
        -H "Authorization: Bearer $TOKEN")

    if [ "$RATE_LIMIT_RESPONSE" -eq 200 ]; then
        print_result 0 "Rate limit stats available"
    else
        print_result 0 "Rate limit stats endpoint not found (optional)" ""
    fi
    echo ""
fi

# Test 8: CORS Headers
echo "Test 8: CORS Configuration"
CORS_RESPONSE=$(curl -s -I "$API_URL/health" | grep -i "access-control-allow-origin")
if [ -n "$CORS_RESPONSE" ]; then
    print_result 0 "CORS headers configured"
else
    print_result 1 "CORS headers not found" "May cause frontend issues"
fi
echo ""

# Summary
echo "=================================================="
echo "  Test Summary"
echo "=================================================="
echo ""
echo "API URL: $API_URL"
echo "Test User: $REGISTER_EMAIL"
echo ""

if [ -n "$TOKEN" ]; then
    echo "To test file upload manually:"
    echo "  curl -X POST '$API_URL/api/transcriptions/upload' \\"
    echo "    -H 'Authorization: Bearer $TOKEN' \\"
    echo "    -F 'file=@your_audio.mp3' \\"
    echo "    -F 'language=en' \\"
    echo "    -F 'generate_summary=true'"
    echo ""
fi

echo "To test with real audio files:"
echo "  1. Record a short audio clip"
echo "  2. Upload via web UI at http://localhost:3000"
echo "  3. Or use the curl command above"
echo ""

echo "For more tests, see: $API_URL/docs"
echo ""
