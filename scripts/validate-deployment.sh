#!/bin/bash

# Deployment Validation Script
set -e

echo "🔍 Validating Deployment Setup"
echo "============================="

# Check if we're in the right directory
if [ ! -f "serverless.yml" ]; then
    echo "❌ serverless.yml not found. Run from backend directory."
    exit 1
fi

# Validate serverless configuration
echo "Checking Serverless configuration..."
if command -v serverless &> /dev/null; then
    serverless config credentials --provider aws --key dummy --secret dummy
    serverless package --stage dev
    echo "✅ Serverless configuration is valid"
else
    echo "⚠️ Serverless Framework not installed globally"
    echo "Install with: npm install -g serverless"
fi

# Check AWS credentials (without exposing them)
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ AWS credentials are configured"
else
    echo "❌ AWS credentials not configured or invalid"
    echo "Configure with: aws configure"
fi

# Validate frontend build
echo ""
echo "Checking Frontend build..."
cd ../frontend
if [ -f "package.json" ]; then
    npm install
    npm run build
    echo "✅ Frontend builds successfully"
else
    echo "❌ Frontend package.json not found"
fi

echo ""
echo "🎉 Validation complete!"
