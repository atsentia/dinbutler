"""Command execution routes."""

from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
import asyncio

from dinbutler.services.commands import get_commands_service
from dinbutler.models.commands import CommandResult, ProcessInfo
from dinbutler.exceptions import NotFoundException, SandboxException, TimeoutException

router = APIRouter()


class RunCommandRequest(BaseModel):
    """Request to run a command."""
    cmd: str = Field(..., description="Command to execute")
    background: bool = Field(default=False, description="Run in background")
    envs: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")
    cwd: Optional[str] = Field(default=None, description="Working directory")
    user: Optional[str] = Field(default=None, description="User to run as")
    timeout: float = Field(default=60, ge=1, le=3600, description="Timeout in seconds")


class CommandResultResponse(BaseModel):
    """Command execution result."""
    stdout: str
    stderr: str
    exit_code: int
    error: Optional[str] = None


class BackgroundCommandResponse(BaseModel):
    """Background command started response."""
    pid: int
    exec_id: str
    sandbox_id: str


class ProcessInfoResponse(BaseModel):
    """Process information response."""
    pid: int
    cmd: str
    args: List[str] = []


@router.post("/run", response_model=CommandResultResponse)
async def run_command(sandbox_id: str, request: RunCommandRequest):
    """Run a command in the sandbox."""
    if request.background:
        raise HTTPException(
            status_code=400,
            detail="Use /run/background for background commands"
        )

    try:
        service = get_commands_service()
        result = service.run(
            sandbox_id=sandbox_id,
            cmd=request.cmd,
            background=False,
            envs=request.envs,
            cwd=request.cwd,
            user=request.user,
            timeout=request.timeout,
        )
        return CommandResultResponse(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            error=result.error,
        )
    except TimeoutException as e:
        raise HTTPException(status_code=408, detail=str(e))
    except SandboxException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/background", response_model=BackgroundCommandResponse)
async def run_background_command(sandbox_id: str, request: RunCommandRequest):
    """Run a command in the background."""
    try:
        service = get_commands_service()
        handle = service.run(
            sandbox_id=sandbox_id,
            cmd=request.cmd,
            background=True,
            envs=request.envs,
            cwd=request.cwd,
            user=request.user,
        )
        return BackgroundCommandResponse(
            pid=handle.pid,
            exec_id=handle.exec_id,
            sandbox_id=sandbox_id,
        )
    except SandboxException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ProcessInfoResponse])
async def list_processes(sandbox_id: str):
    """List running processes."""
    try:
        service = get_commands_service()
        processes = service.list(sandbox_id)
        return [
            ProcessInfoResponse(
                pid=p.pid,
                cmd=p.cmd,
                args=p.args,
            )
            for p in processes
        ]
    except SandboxException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{pid}")
async def kill_process(sandbox_id: str, pid: int, signal: str = Query("KILL")):
    """Kill a process."""
    service = get_commands_service()
    success = service.kill(sandbox_id, pid, signal)
    return {"success": success, "pid": pid}


@router.websocket("/stream/{pid}")
async def stream_output(websocket: WebSocket, sandbox_id: str, pid: int):
    """WebSocket endpoint for streaming command output."""
    await websocket.accept()

    try:
        service = get_commands_service()
        handle = service.connect(sandbox_id, pid)

        # Stream output
        while True:
            # Check if process is still running
            try:
                info = handle._docker.exec_inspect(handle.exec_id) if handle.exec_id else {}
                running = info.get("Running", False)
            except Exception:
                running = False

            # Send any buffered output
            if hasattr(handle, '_stdout_buffer') and handle._stdout_buffer:
                for line in handle._stdout_buffer:
                    await websocket.send_json({"type": "stdout", "data": line})
                handle._stdout_buffer.clear()

            if not running:
                await websocket.send_json({"type": "exit", "code": info.get("ExitCode", -1)})
                break

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        pass
    except NotFoundException as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()
