# Colima E2B Templates

Docker templates for sandbox environments.

## Available Templates

### default
Basic Ubuntu 22.04 with essential tools:
- curl, wget, git
- vim, nano
- inotify-tools (for file watching)
- procps, htop (for process management)

### python
Python 3.11 with data science stack:
- numpy, pandas, matplotlib, seaborn
- scipy, scikit-learn
- jupyter, ipython
- requests, httpx, pydantic

### node
Node.js 20 LTS with common tooling:
- TypeScript, ts-node
- ESLint, Prettier
- nodemon

## Building Templates

```bash
# Build all templates
colima-e2b build-templates

# Build specific template
docker build -t colima-e2b-default:latest templates/default/
docker build -t colima-e2b-python:latest templates/python/
docker build -t colima-e2b-node:latest templates/node/
```

## Creating Custom Templates

1. Create a new directory: `templates/mytemplate/`
2. Add a `Dockerfile`
3. Build with: `docker build -t colima-e2b-mytemplate:latest templates/mytemplate/`
4. Use with: `Sandbox.create(template="colima-e2b-mytemplate:latest")`
