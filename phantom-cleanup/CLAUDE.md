# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build, Lint & Test Commands

### Python Data Analysis
- Setup virtual environment: `python -m venv venv && source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Run notebook: `jupyter notebook phantom_cleanup.ipynb`
- Run tests: `pytest`
- Lint: `flake8 *.py`

### Backend (Python/Serverless)
- Deploy: `cd ../backend && serverless deploy`
- Test a specific Lambda: `cd ../backend && serverless invoke local -f functionName`
- Lint: `cd ../backend && flake8 src/`

### Frontend (React/TypeScript)
- Dev server: `cd ../frontend && npm run dev`
- Build: `cd ../frontend && npm run build`
- Lint: `cd ../frontend && npm run lint`

## Code Style Guidelines

### Python
- Follow PEP 8 style guide
- Group imports: standard library, then third-party packages, then local modules
- Use snake_case for variables/functions and PascalCase for classes
- Document functions with docstrings
- Handle errors with appropriate try/except blocks

### TypeScript/React 
- Use TypeScript interfaces for prop types and states
- Follow React hooks pattern for component state management
- Use camelCase for variables/functions and PascalCase for components/types
- Structure imports: React imports first, then external packages, then local imports