#!/bin/bash

# GitHub Migration Setup Script
# This script helps automate the initial setup for GitHub migration

set -e

echo "🚀 GitHub Migration Setup Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
echo "Checking prerequisites..."

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed. Please install Git first."
    exit 1
fi

# Check if aws cli is installed
if ! command -v aws &> /dev/null; then
    print_warning "AWS CLI is not installed. You'll need it for manual deployment verification."
fi

# Check if current directory is a git repository
if [ ! -d ".git" ]; then
    print_error "Current directory is not a Git repository. Please run from the project root."
    exit 1
fi

print_status "Prerequisites check completed"

# Get GitHub repository information
echo ""
echo "📝 Repository Configuration"
echo "=========================="

read -p "Enter GitHub username/organization: " GITHUB_USER
read -p "Enter repository name: " REPO_NAME

# Validate inputs
if [ -z "$GITHUB_USER" ] || [ -z "$REPO_NAME" ]; then
    print_error "GitHub username and repository name are required."
    exit 1
fi

GITHUB_REPO_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

echo ""
echo "Repository URL: $GITHUB_REPO_URL"

# Check if remote origin exists
if git remote get-url origin &> /dev/null; then
    print_warning "Remote 'origin' already exists. Current URL: $(git remote get-url origin)"
    read -p "Do you want to update it? (y/N): " UPDATE_ORIGIN
    
    if [[ $UPDATE_ORIGIN =~ ^[Yy]$ ]]; then
        git remote set-url origin "$GITHUB_REPO_URL"
        print_status "Updated remote origin URL"
    fi
else
    git remote add origin "$GITHUB_REPO_URL"
    print_status "Added remote origin"
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "Creating .gitignore file..."
    cat > .gitignore << 'EOF'
# Dependencies
node_modules/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Environment variables
.env
.env.local
.env.production

# Build outputs
dist/
build/
.serverless/
htmlcov/

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Coverage reports
.coverage
.pytest_cache/
coverage.xml

# AWS
.aws/

# Test artifacts
processor_test_results.jsonl
gap_locations.jsonl
output.json
payload.txt
test_payload.json
test_payload.txt

# Python virtual environments
venv/
env/
sls_env/

# Temporary files
*.tmp
*.temp
EOF
    print_status "Created .gitignore file"
else
    print_status ".gitignore already exists"
fi

# Create GitHub workflows directory
mkdir -p .github/workflows
print_status "Created .github/workflows directory"

# Check if workflow files exist
if [ -f ".github/workflows/ci-cd.yml" ] && [ -f ".github/workflows/pr-checks.yml" ]; then
    print_status "GitHub Actions workflow files already exist"
else
    print_warning "GitHub Actions workflow files not found. Please ensure ci-cd.yml and pr-checks.yml are in .github/workflows/"
fi

# Prepare secrets checklist
echo ""
echo "🔐 GitHub Secrets Configuration"
echo "=============================="
echo "You'll need to configure these secrets in GitHub repository settings:"
echo ""
echo "Required secrets:"
echo "- AWS_ACCESS_KEY_ID"
echo "- AWS_SECRET_ACCESS_KEY"
echo "- DEV_API_BASE_URL"
echo "- PROD_API_BASE_URL"
echo "- VERCEL_TOKEN"
echo "- VERCEL_ORG_ID"
echo "- VERCEL_PROJECT_ID"
echo ""
echo "📍 Go to: https://github.com/${GITHUB_USER}/${REPO_NAME}/settings/secrets/actions"

# Create environment setup script
cat > scripts/configure-environments.sh << 'EOF'
#!/bin/bash

# Environment Configuration Script
echo "🌍 Setting up GitHub Environments"

# This script provides instructions for manual environment setup
# since GitHub API requires special permissions for environment creation

echo ""
echo "Manual steps required:"
echo "1. Go to https://github.com/GITHUB_USER/REPO_NAME/settings/environments"
echo "2. Create 'dev' environment"
echo "3. Create 'prod' environment"
echo "4. Add environment-specific secrets if needed"
echo ""
echo "Environment-specific variables:"
echo "dev:"
echo "  - API_BASE_URL: DEV_API_BASE_URL"
echo "prod:"
echo "  - API_BASE_URL: PROD_API_BASE_URL"
EOF

chmod +x scripts/configure-environments.sh
print_status "Created environment configuration script"

# Create deployment validation script
cat > scripts/validate-deployment.sh << 'EOF'
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
EOF

chmod +x scripts/validate-deployment.sh
print_status "Created deployment validation script"

# Stage and commit workflow files
echo ""
echo "📦 Staging Files for Commit"
echo "=========================="

git add .github/
git add scripts/
git add .gitignore
git add MIGRATION-GUIDE.md

# Check if there are changes to commit
if git diff --staged --quiet; then
    print_warning "No changes to commit"
else
    print_status "Files staged for commit"
    
    echo ""
    echo "Staged files:"
    git diff --staged --name-only
    
    echo ""
    read -p "Do you want to commit these changes? (y/N): " COMMIT_CHANGES
    
    if [[ $COMMIT_CHANGES =~ ^[Yy]$ ]]; then
        git commit -m "Add GitHub Actions workflows and migration setup

- Add CI/CD pipeline with backend/frontend testing and deployment
- Add pull request validation workflow
- Create migration guide and setup scripts
- Configure deployment automation for dev/prod environments"
        
        print_status "Changes committed"
        
        echo ""
        read -p "Do you want to push to GitHub? (y/N): " PUSH_CHANGES
        
        if [[ $PUSH_CHANGES =~ ^[Yy]$ ]]; then
            git push -u origin main
            print_status "Changes pushed to GitHub"
        fi
    fi
fi

echo ""
echo "🎉 Setup Complete!"
echo "================="
echo ""
echo "Next steps:"
echo "1. Configure GitHub secrets: https://github.com/${GITHUB_USER}/${REPO_NAME}/settings/secrets/actions"
echo "2. Set up GitHub environments: https://github.com/${GITHUB_USER}/${REPO_NAME}/settings/environments"
echo "3. Create Vercel project and get integration tokens"
echo "4. Run validation script: ./scripts/validate-deployment.sh"
echo "5. Monitor first deployment in GitHub Actions tab"
echo ""
echo "📚 For detailed instructions, see MIGRATION-GUIDE.md"
EOF