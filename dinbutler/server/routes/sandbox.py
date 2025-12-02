"""Sandbox management routes."""

from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from dinbutler.services.sandbox_manager import get_sandbox_manager
from dinbutler.models.sandbox import SandboxInfo, SandboxState
from dinbutler.exceptions import NotFoundException, SandboxException

router = APIRouter()


class CreateSandboxRequest(BaseModel):
    """Request to create a sandbox."""
    template: str = Field(default="default", description="Template name or Docker image")
    timeout: int = Field(default=300, ge=1, le=86400, description="Timeout in seconds")
    envs: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="Custom metadata")


class SandboxResponse(BaseModel):
    """Sandbox information response."""
    sandbox_id: str
    template_id: str
    state: str
    started_at: str
    metadata: Dict[str, str] = {}

    class Config:
        from_attributes = True


class KillResponse(BaseModel):
    """Kill sandbox response."""
    success: bool


@router.post("/", response_model=SandboxResponse)
async def create_sandbox(request: CreateSandboxRequest):
    """Create a new sandbox."""
    try:
        manager = get_sandbox_manager()
        info = manager.create(
            template=request.template,
            timeout=request.timeout,
            envs=request.envs,
            metadata=request.metadata,
        )
        return SandboxResponse(
            sandbox_id=info.sandbox_id,
            template_id=info.template_id,
            state=info.state.value,
            started_at=info.started_at.isoformat(),
            metadata=info.metadata,
        )
    except SandboxException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[SandboxResponse])
async def list_sandboxes(
    state: Optional[str] = Query(None, description="Filter by state")
):
    """List all sandboxes."""
    manager = get_sandbox_manager()
    sandboxes = manager.list()

    if state:
        sandboxes = [s for s in sandboxes if s.state.value == state]

    return [
        SandboxResponse(
            sandbox_id=s.sandbox_id,
            template_id=s.template_id,
            state=s.state.value,
            started_at=s.started_at.isoformat(),
            metadata=s.metadata,
        )
        for s in sandboxes
    ]


@router.get("/{sandbox_id}", response_model=SandboxResponse)
async def get_sandbox(sandbox_id: str):
    """Get sandbox information."""
    manager = get_sandbox_manager()
    info = manager.get_info(sandbox_id)

    if info is None:
        raise HTTPException(status_code=404, detail=f"Sandbox {sandbox_id} not found")

    return SandboxResponse(
        sandbox_id=info.sandbox_id,
        template_id=info.template_id,
        state=info.state.value,
        started_at=info.started_at.isoformat(),
        metadata=info.metadata,
    )


@router.delete("/{sandbox_id}", response_model=KillResponse)
async def kill_sandbox(sandbox_id: str):
    """Kill a sandbox."""
    manager = get_sandbox_manager()
    success = manager.kill(sandbox_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Sandbox {sandbox_id} not found")

    return KillResponse(success=True)


@router.post("/{sandbox_id}/timeout")
async def set_timeout(sandbox_id: str, timeout: int = Query(..., ge=1, le=86400)):
    """Update sandbox timeout."""
    try:
        manager = get_sandbox_manager()
        manager.set_timeout(sandbox_id, timeout)
        return {"success": True, "timeout": timeout}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
