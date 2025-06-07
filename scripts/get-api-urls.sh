#!/bin/bash

# Script to get API URLs after deployment
set -e

echo "🔍 Getting API URLs from deployed Serverless applications"
echo "======================================================="

REGION="eu-central-1"

# Check if serverless is installed
if ! command -v serverless &> /dev/null; then
    echo "❌ Serverless Framework not found. Install with: npm install -g serverless"
    exit 1
fi

# Check if we're in the backend directory
if [ ! -f "serverless.yml" ]; then
    echo "❌ serverless.yml not found. Run this script from the backend directory."
    exit 1
fi

echo "Getting API URLs..."
echo ""

# Get dev API URL
echo "🔧 Development environment:"
if DEV_OUTPUT=$(serverless info --stage dev --region $REGION 2>/dev/null); then
    DEV_URL=$(echo "$DEV_OUTPUT" | grep -o 'https://[^[:space:]]*\.execute-api\.[^[:space:]]*\.amazonaws\.com[^[:space:]]*' | head -1)
    if [ -n "$DEV_URL" ]; then
        echo "✅ DEV_API_BASE_URL=$DEV_URL"
    else
        echo "❌ Could not extract dev API URL. Is the dev stage deployed?"
    fi
else
    echo "❌ Dev stage not deployed or not accessible"
fi

echo ""

# Get prod API URL
echo "🚀 Production environment:"
if PROD_OUTPUT=$(serverless info --stage prod --region $REGION 2>/dev/null); then
    PROD_URL=$(echo "$PROD_OUTPUT" | grep -o 'https://[^[:space:]]*\.execute-api\.[^[:space:]]*\.amazonaws\.com[^[:space:]]*' | head -1)
    if [ -n "$PROD_URL" ]; then
        echo "✅ PROD_API_BASE_URL=$PROD_URL"
    else
        echo "❌ Could not extract prod API URL. Is the prod stage deployed?"
    fi
else
    echo "❌ Prod stage not deployed or not accessible"
fi

echo ""
echo "📝 GitHub Secrets Configuration:"
echo "==============================="
echo ""
echo "Add these to your GitHub repository secrets:"
echo ""

if [ -n "$DEV_URL" ]; then
    echo "DEV_API_BASE_URL=$DEV_URL"
fi

if [ -n "$PROD_URL" ]; then
    echo "PROD_API_BASE_URL=$PROD_URL"
fi

echo ""
echo "💡 Note: These URLs are generated during deployment and change if you redeploy the stack."
echo "💡 The GitHub Actions workflow will automatically use these URLs once configured."