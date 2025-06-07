#!/bin/bash

# AWS Setup Script for GitHub Actions
# This script helps create the necessary AWS resources and IAM policies

set -e

echo "☁️ AWS Setup for GitHub Actions"
echo "==============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first:"
    echo "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
REGION="eu-central-1"

print_status "Connected to AWS Account: $ACCOUNT_ID"
print_status "Using region: $REGION"

echo ""
echo "🔐 Creating IAM User for GitHub Actions"
echo "====================================="

# IAM user name
IAM_USER_NAME="github-actions-location-tracker"

# Check if user already exists
if aws iam get-user --user-name "$IAM_USER_NAME" &> /dev/null; then
    print_warning "IAM user '$IAM_USER_NAME' already exists"
    read -p "Do you want to recreate it? This will delete the existing user and keys. (y/N): " RECREATE_USER
    
    if [[ $RECREATE_USER =~ ^[Yy]$ ]]; then
        # Delete existing access keys
        echo "Deleting existing access keys..."
        aws iam list-access-keys --user-name "$IAM_USER_NAME" --query 'AccessKeyMetadata[].AccessKeyId' --output text | \
        while read -r key_id; do
            if [ -n "$key_id" ]; then
                aws iam delete-access-key --user-name "$IAM_USER_NAME" --access-key-id "$key_id"
                echo "Deleted access key: $key_id"
            fi
        done
        
        # Detach policies
        echo "Detaching policies..."
        aws iam list-attached-user-policies --user-name "$IAM_USER_NAME" --query 'AttachedPolicies[].PolicyArn' --output text | \
        while read -r policy_arn; do
            if [ -n "$policy_arn" ]; then
                aws iam detach-user-policy --user-name "$IAM_USER_NAME" --policy-arn "$policy_arn"
                echo "Detached policy: $policy_arn"
            fi
        done
        
        # Delete user
        aws iam delete-user --user-name "$IAM_USER_NAME"
        print_status "Deleted existing IAM user"
    else
        echo "Using existing IAM user"
    fi
fi

# Create IAM user if it doesn't exist
if ! aws iam get-user --user-name "$IAM_USER_NAME" &> /dev/null; then
    aws iam create-user --user-name "$IAM_USER_NAME"
    print_status "Created IAM user: $IAM_USER_NAME"
fi

# Create IAM policy for GitHub Actions
POLICY_NAME="GitHubActionsLocationTrackerPolicy"
POLICY_DOCUMENT=$(cat << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:*",
                "apigateway:*",
                "dynamodb:*",
                "iot:*",
                "logs:*",
                "cloudformation:*",
                "s3:*",
                "iam:PassRole",
                "iam:GetRole",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:GetRolePolicy",
                "iam:TagRole",
                "iam:UntagRole"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:CreateStack",
                "cloudformation:UpdateStack",
                "cloudformation:DeleteStack",
                "cloudformation:DescribeStacks",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStackResource",
                "cloudformation:DescribeStackResources",
                "cloudformation:GetTemplate",
                "cloudformation:ListStackResources",
                "cloudformation:ValidateTemplate"
            ],
            "Resource": [
                "arn:aws:cloudformation:${REGION}:${ACCOUNT_ID}:stack/location-tracker-*/*"
            ]
        }
    ]
}
EOF
)

# Create or update the policy
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"

# Check if policy exists
if aws iam get-policy --policy-arn "$POLICY_ARN" &> /dev/null; then
    print_warning "Policy '$POLICY_NAME' already exists"
    
    # Create new policy version
    POLICY_VERSION=$(aws iam create-policy-version \
        --policy-arn "$POLICY_ARN" \
        --policy-document "$POLICY_DOCUMENT" \
        --set-as-default \
        --query 'PolicyVersion.VersionId' \
        --output text)
    
    print_status "Updated policy to version: $POLICY_VERSION"
else
    # Create new policy
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document "$POLICY_DOCUMENT" \
        --description "Policy for GitHub Actions to deploy Location Tracker application"
    
    print_status "Created IAM policy: $POLICY_NAME"
fi

# Attach policy to user
aws iam attach-user-policy \
    --user-name "$IAM_USER_NAME" \
    --policy-arn "$POLICY_ARN"

print_status "Attached policy to user"

# Create access keys
print_info "Creating new access keys..."
ACCESS_KEY_OUTPUT=$(aws iam create-access-key --user-name "$IAM_USER_NAME")
ACCESS_KEY_ID=$(echo "$ACCESS_KEY_OUTPUT" | grep -o '"AccessKeyId": "[^"]*"' | cut -d'"' -f4)
SECRET_ACCESS_KEY=$(echo "$ACCESS_KEY_OUTPUT" | grep -o '"SecretAccessKey": "[^"]*"' | cut -d'"' -f4)

print_status "Created access keys"

echo ""
echo "🔑 GitHub Secrets Configuration"
echo "==============================="
echo ""
echo "Add these secrets to your GitHub repository:"
echo ""
echo "AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID"
echo "AWS_SECRET_ACCESS_KEY=$SECRET_ACCESS_KEY"
echo ""
print_warning "IMPORTANT: Save these credentials securely. The secret key cannot be retrieved again."
print_warning "Add these to GitHub repository secrets immediately."

# Save credentials to file (optional)
read -p "Do you want to save credentials to a local file? (y/N): " SAVE_CREDS

if [[ $SAVE_CREDS =~ ^[Yy]$ ]]; then
    CREDS_FILE="aws-github-credentials.txt"
    cat > "$CREDS_FILE" << EOF
GitHub Secrets for Location Tracker
==================================

Add these secrets to your GitHub repository:
Repository Settings > Secrets and variables > Actions

AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=$SECRET_ACCESS_KEY

Additional secrets needed:
DEV_API_BASE_URL=https://your-dev-api.execute-api.eu-central-1.amazonaws.com
PROD_API_BASE_URL=https://your-prod-api.execute-api.eu-central-1.amazonaws.com
VERCEL_TOKEN=your-vercel-token
VERCEL_ORG_ID=your-vercel-org-id
VERCEL_PROJECT_ID=your-vercel-project-id

Created: $(date)
Account ID: $ACCOUNT_ID
IAM User: $IAM_USER_NAME
Policy: $POLICY_NAME
EOF
    
    print_status "Credentials saved to: $CREDS_FILE"
    print_warning "Remember to delete this file after adding secrets to GitHub!"
fi

echo ""
echo "🎯 Next Steps"
echo "============"
echo ""
echo "1. Add the AWS credentials to GitHub repository secrets:"
echo "   https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions"
echo ""
echo "2. Set up Vercel integration and get tokens:"
echo "   - Create Vercel account and project"
echo "   - Get integration tokens from Vercel dashboard"
echo ""
echo "3. Configure environment-specific API URLs after first deployment"
echo ""
echo "4. Test the setup by pushing code to main branch"
echo ""
print_status "AWS setup complete!"