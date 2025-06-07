#!/bin/bash

# Get Vercel Information for GitHub Actions Setup
echo "🔍 Getting Vercel Information"
echo "============================"

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

echo ""
echo "📋 Getting your Vercel information..."
echo ""

echo "🏢 Organizations/Teams:"
vercel teams list

echo ""
echo "📁 Projects:"
vercel projects list

echo ""
echo "💡 To get specific project info:"
echo "vercel project info YOUR_PROJECT_NAME"

echo ""
echo "🔐 For GitHub Actions, you need:"
echo "VERCEL_TOKEN=xxx (get from vercel.com/account/tokens)"
echo "VERCEL_ORG_ID=xxx (from 'vercel teams list' or dashboard)"
echo "VERCEL_PROJECT_ID=xxx (from 'vercel projects list' or dashboard)"