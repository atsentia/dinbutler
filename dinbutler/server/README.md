# Colima E2B FastAPI Server

This directory contains the FastAPI server implementation for the Colima E2B package.

## Quick Start

### 1. Start the Server

```bash
# Using the CLI (recommended)
colima-e2b server

# Or directly with uvicorn
uvicorn colima_e2b.server:app --reload
```

### 2. Access API Documentation

Open your browser to:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Directory Structure

```
server/
├── __init__.py          # Package exports (app, create_app)
├── app.py               # Main FastAPI application
└── routes/
    ├── __init__.py      # Routes exports
    ├── sandbox.py       # Sandbox CRUD operations
    ├── files.py         # File operations
    └── commands.py      # Command execution + WebSocket
```

## API Endpoints

### Sandboxes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sandboxes/` | Create sandbox |
| GET | `/sandboxes/` | List sandboxes |
| GET | `/sandboxes/{id}` | Get sandbox info |
| DELETE | `/sandboxes/{id}` | Kill sandbox |
| POST | `/sandboxes/{id}/timeout` | Update timeout |

### Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sandboxes/{id}/files/write` | Write file |
| GET | `/sandboxes/{id}/files/read` | Read file |
| GET | `/sandboxes/{id}/files/list` | List directory |
| GET | `/sandboxes/{id}/files/exists` | Check file exists |
| DELETE | `/sandboxes/{id}/files/` | Remove file |

### Commands

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sandboxes/{id}/commands/run` | Run command |
| POST | `/sandboxes/{id}/commands/run/background` | Run in background |
| GET | `/sandboxes/{id}/commands/` | List processes |
| DELETE | `/sandboxes/{id}/commands/{pid}` | Kill process |
| WS | `/sandboxes/{id}/commands/stream/{pid}` | Stream output |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Server health check |

## Usage Examples

### Create a Sandbox

```bash
curl -X POST http://localhost:8000/sandboxes/ \
  -H "Content-Type: application/json" \
  -d '{
    "template": "python",
    "timeout": 600,
    "envs": {"DEBUG": "1"},
    "metadata": {"purpose": "test"}
  }'
```

Response:
```json
{
  "sandbox_id": "clm_abc123",
  "template_id": "python",
  "state": "running",
  "started_at": "2024-12-02T10:30:00",
  "metadata": {"purpose": "test"}
}
```

### Write a File

```bash
curl -X POST http://localhost:8000/sandboxes/clm_abc123/files/write \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/home/user/script.py",
    "data": "print(\"Hello, World!\")"
  }'
```

### Run a Command

```bash
curl -X POST http://localhost:8000/sandboxes/clm_abc123/commands/run \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "python script.py",
    "timeout": 30,
    "cwd": "/home/user"
  }'
```

Response:
```json
{
  "stdout": "Hello, World!\n",
  "stderr": "",
  "exit_code": 0,
  "error": null
}
```

### Stream Command Output (WebSocket)

```python
import websocket
import json

ws = websocket.create_connection(
    f"ws://localhost:8000/sandboxes/{sandbox_id}/commands/stream/{pid}"
)

while True:
    msg = ws.recv()
    data = json.loads(msg)

    if data["type"] == "stdout":
        print(data["data"], end="")
    elif data["type"] == "stderr":
        print(data["data"], end="", file=sys.stderr)
    elif data["type"] == "exit":
        print(f"\nProcess exited with code {data['code']}")
        break
    elif data["type"] == "error":
        print(f"Error: {data['message']}")
        break

ws.close()
```

## Configuration

### Environment Variables

```bash
# Docker socket (auto-detected by default)
export DOCKER_HOST=unix:///var/run/docker.sock

# Server settings
export HOST=127.0.0.1
export PORT=8000
```

### CLI Options

```bash
# Custom host and port
colima-e2b server --host 0.0.0.0 --port 9000

# Enable auto-reload for development
colima-e2b server --reload
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run server integration tests
pytest tests/test_server_integration.py -v

# Run with coverage
pytest tests/test_server_integration.py --cov=colima_e2b.server
```

### Adding New Routes

1. Create a new router in `routes/`:

```python
# routes/new_feature.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/example")
async def example_endpoint():
    return {"message": "Hello"}
```

2. Register in `app.py`:

```python
from colima_e2b.server.routes import new_feature

app.include_router(
    new_feature.router,
    prefix="/sandboxes/{sandbox_id}/feature",
    tags=["feature"]
)
```

### Code Style

The server follows these conventions:
- **Async handlers**: All route handlers are `async def`
- **Type hints**: Full type annotations with Pydantic models
- **Error handling**: Use custom exceptions from `colima_e2b.exceptions`
- **Docstrings**: Document all endpoints with clear descriptions

## Troubleshooting

### Server won't start

**Problem**: `Cannot connect to Docker`

**Solution**:
```bash
# Check Colima status
colima status

# Start Colima if needed
colima start --vm-type=vz

# Verify Docker connection
docker ps
```

### Import errors

**Problem**: `ModuleNotFoundError: No module named 'colima_e2b'`

**Solution**:
```bash
# Install package in editable mode
pip install -e .

# Verify installation
python -c "import colima_e2b; print(colima_e2b.__file__)"
```

### Port already in use

**Problem**: `Address already in use`

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
colima-e2b server --port 9000
```

## Architecture

### Request Flow

```
Client → FastAPI → Route Handler → Service Layer → Docker Client → Container
   ↑                                                                      ↓
   └────────────────────── Response ←──────────────────────────────────┘
```

### Key Components

1. **FastAPI App** (`app.py`):
   - Manages application lifecycle
   - Registers routes and middleware
   - Handles errors globally

2. **Routes** (`routes/*.py`):
   - Parse and validate requests (Pydantic models)
   - Call service layer methods
   - Format responses

3. **Services** (`../services/*.py`):
   - Business logic
   - Docker API interactions
   - State management

4. **Models** (`../models/*.py`):
   - Data structures
   - Validation rules
   - Type definitions

### Error Handling

The server uses a consistent error handling strategy:

```python
try:
    result = service.operation(sandbox_id, params)
    return SuccessResponse(**result)
except NotFoundException as e:
    raise HTTPException(status_code=404, detail=str(e))
except TimeoutException as e:
    raise HTTPException(status_code=408, detail=str(e))
except SandboxException as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**Status Codes**:
- `200` - Success
- `404` - Not Found (sandbox, file, process)
- `408` - Request Timeout (command timeout)
- `422` - Validation Error (invalid request data)
- `500` - Server Error (Docker issues, internal errors)

## Performance

### Concurrent Requests

The server can handle multiple requests concurrently thanks to FastAPI's async support:

```python
@router.post("/run")
async def run_command(...):
    # Non-blocking operation
    result = service.run(...)
    return result
```

### Connection Pooling

The Docker client uses a singleton pattern with connection pooling:

```python
# Shared client instance across all requests
client = get_docker_client()
```

### WebSocket Efficiency

WebSocket streaming uses:
- 100ms polling interval (balance between responsiveness and CPU)
- Small buffers to minimize memory usage
- Automatic cleanup on disconnect

## Security

### Current Implementation

The server is designed for **local development** and has:
- No authentication/authorization
- CORS enabled for all origins
- No rate limiting

### Production Considerations

For production use, add:

1. **Authentication**:
```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@router.post("/")
async def create_sandbox(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Verify token
```

2. **Rate Limiting**:
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/", dependencies=[Depends(limiter.limit("10/minute"))])
async def create_sandbox(...):
    ...
```

3. **Input Sanitization**:
```python
def sanitize_path(path: str) -> str:
    """Prevent path traversal attacks."""
    if ".." in path or path.startswith("/"):
        raise ValueError("Invalid path")
    return path
```

## Related Documentation

- [Project README](../../README.md) - Overall project documentation
- [Server Overview](../../SERVER_OVERVIEW.md) - Detailed server architecture
- [API Examples](../../examples/) - Usage examples
- [E2B API Docs](https://e2b.dev/docs) - E2B API specification

## Contributing

When contributing to the server:

1. **Add tests** for new endpoints
2. **Update OpenAPI spec** (automatically via Pydantic)
3. **Document** new routes in this README
4. **Follow conventions** (async, type hints, error handling)
5. **Test** with `pytest tests/test_server_integration.py`

## License

MIT License - See [LICENSE](../../LICENSE) file
