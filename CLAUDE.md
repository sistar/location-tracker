# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build, Lint & Test Commands

### Frontend (React/TypeScript)
- Build: `cd frontend && npm run build`
- Dev server: `cd frontend && npm run dev`
- Lint: `cd frontend && npm run lint`

### Backend (Python/Serverless)
- Deploy: `cd backend && serverless deploy`
- Test a specific Lambda: `cd backend && serverless invoke local -f functionName`
- Test API endpoints: Use Postman or curl against the deployed endpoints

## Code Style Guidelines

### Frontend (TypeScript/React)
- Use TypeScript interfaces for prop types and states
- Follow React hooks pattern for component state management
- Use camelCase for variable/function names and PascalCase for components/types
- Structure imports: React imports first, then external packages, then local imports
- Use ESLint for code quality (`npm run lint`)

### Backend (Python)
- Follow PEP 8 style guide
- Group imports: standard library, then third-party packages, then local modules
- Use snake_case for variables/functions and PascalCase for classes
- Handle errors with appropriate try/except blocks
- Include docstrings for functions and modules
- Print debug information with descriptive prefixes for easier log parsing