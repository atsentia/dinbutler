# Gemini CLI Quick Reference

This guide provides a quick reference for using the Gemini CLI within the DinButler sandbox.

## Quick Start

```bash
# Initialize the sandbox
gemini sandbox init

# Create a sandbox
gemini sandbox create --template=python --timeout=300

# Run a command
gemini sandbox exec --id=<sandbox_id> -- "python --version"

# Write a file
gemini sandbox files write --id=<sandbox_id> --path=/app/script.py --content="print('Hello from sandbox!')"

# Read a file
gemini sandbox files read --id=<sandbox_id> --path=/app/script.py

# List files
gemini sandbox files list --id=<sandbox_id> --path=/app

# Kill the sandbox
gemini sandbox kill --id=<sandbox_id>
```

## Available Templates

- **default** - Ubuntu 22.04 with bash, curl, git, vim
- **python** - Python 3.11 + pip, numpy, pandas, requests
- **node** - Node.js 20 + npm, TypeScript, common packages
- **gemini** - Includes the Gemini CLI and its dependencies
- **custom** - Build your own with a Dockerfile

For more detailed tool documentation, use `gemini sandbox prime`.
