# GitHub Migration & CI/CD Setup Guide

## Overview
This guide walks through migrating the location tracker project to GitHub with automated deployment using GitHub Actions.

## Prerequisites

### 1. GitHub Repository Setup
- Create a new GitHub repository
- Push existing code to the repository
- Set up branch protection rules for `main` branch

### 2. AWS Account Access
- Ensure you have AWS credentials with permissions for:
  - Lambda functions
  - DynamoDB tables
  - API Gateway
  - CloudFormation stacks
  - S3 buckets (for deployment artifacts)

### 3. Vercel Account (for Frontend)
- Create Vercel account
- Get Vercel integration tokens

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings (Settings > Secrets and variables > Actions):

### AWS Configuration
```
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
```

### Environment-Specific API URLs
```
DEV_API_BASE_URL=https://your-dev-api.execute-api.eu-central-1.amazonaws.com
PROD_API_BASE_URL=https://your-prod-api.execute-api.eu-central-1.amazonaws.com
```

### Vercel Integration
```
VERCEL_TOKEN=your_vercel_token
VERCEL_ORG_ID=your_vercel_org_id
VERCEL_PROJECT_ID=your_vercel_project_id
```

## Environment Management

### Development Environment
- Stage name: `dev`
- Region: `eu-central-1`
- Automatic deployment on push to `main`

### Production Environment
- Stage name: `prod`
- Region: `eu-central-1`
- Automatic deployment after dev deployment succeeds

## Migration Steps

### Step 1: Repository Setup
```bash
# 1. Create GitHub repository
# 2. Add remote origin
git remote add origin https://github.com/yourusername/location-tracker.git

# 3. Push existing code
git push -u origin main
```

### Step 2: Configure GitHub Secrets
1. Go to repository Settings > Secrets and variables > Actions
2. Add all required secrets listed above
3. Verify secret names match exactly with workflow files

### Step 3: Set up GitHub Environments
1. Go to repository Settings > Environments
2. Create `dev` environment
3. Create `prod` environment
4. Add environment-specific secrets if needed

### Step 4: Initial Deployment
```bash
# The first deployment will be triggered automatically when:
# 1. Code is pushed to main branch
# 2. All tests pass
# 3. GitHub Actions workflows complete successfully
```

## Workflow Overview

### CI/CD Pipeline (`ci-cd.yml`)
- **Trigger**: Push to `main` or `develop`, PRs to `main`
- **Jobs**:
  1. Backend testing with coverage
  2. Frontend testing and building
  3. Backend deployment (dev → prod)
  4. Frontend deployment to Vercel
  5. Security scanning
  6. Performance testing

### Pull Request Checks (`pr-checks.yml`)
- **Trigger**: Pull requests to `main` or `develop`
- **Jobs**:
  1. Code quality checks (linting, formatting)
  2. Test coverage validation (minimum 75%)
  3. Security scanning
  4. Infrastructure validation
  5. Documentation checks
  6. Bundle size analysis

## Testing the Setup

### 1. Test Backend Deployment
```bash
# After deployment, test endpoints:
curl https://your-api-endpoint/dev/vehicles
curl https://your-api-endpoint/prod/vehicles
```

### 2. Test Frontend Deployment
- Visit dev frontend URL (provided by Vercel)
- Visit prod frontend URL (provided by Vercel)
- Verify API connectivity

### 3. Monitor Deployments
- Check GitHub Actions tabs for deployment status
- Monitor AWS CloudWatch logs
- Verify DynamoDB tables are created/updated

## Troubleshooting

### Common Issues
1. **AWS Permissions**: Ensure IAM user has sufficient permissions
2. **Vercel Integration**: Verify project ID and organization ID
3. **API URLs**: Ensure frontend environment variables point to correct backend
4. **Test Failures**: Check coverage meets 75% minimum requirement

### Debug Steps
1. Check GitHub Actions logs for detailed error messages
2. Verify all secrets are configured correctly
3. Test serverless deployment locally first
4. Validate CloudFormation templates

## Monitoring & Maintenance

### Post-Migration Tasks
1. Set up CloudWatch alarms for Lambda functions
2. Configure SNS notifications for deployment failures
3. Set up log aggregation and monitoring
4. Plan regular dependency updates

### Regular Maintenance
- Update GitHub Actions versions quarterly
- Review and update security scanning rules
- Monitor bundle size growth
- Update test coverage requirements as needed

## Security Considerations

### Secrets Management
- Never commit secrets to repository
- Use GitHub environments for sensitive deployments
- Rotate AWS credentials regularly
- Monitor secret access logs

### Access Control
- Enable branch protection rules
- Require PR reviews for production deployments
- Use least-privilege IAM policies
- Enable GitHub Security tab monitoring

## Performance Optimization

### Backend
- Monitor Lambda cold starts
- Optimize DynamoDB queries
- Set up API Gateway caching
- Configure Lambda reserved concurrency

### Frontend
- Monitor bundle size (current threshold: 5MB)
- Implement code splitting if needed
- Use Vercel analytics for performance insights
- Set up performance budgets

## Next Steps

1. Complete initial migration
2. Test all workflows thoroughly
3. Set up monitoring and alerting
4. Plan future enhancements (staging environment, blue-green deployments)
5. Document operational procedures