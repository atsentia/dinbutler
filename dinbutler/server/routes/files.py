"""File operations routes."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from dinbutler.services.filesystem import get_filesystem_service
from dinbutler.models.filesystem import EntryInfo, WriteInfo, FileType
from dinbutler.exceptions import NotFoundException, SandboxException

router = APIRouter()


class WriteFileRequest(BaseModel):
    """Request to write a file."""
    path: str = Field(..., description="File path")
    data: str = Field(..., description="File content")
    user: Optional[str] = Field(default=None, description="User to write as")


class WriteFileResponse(BaseModel):
    """Response after writing a file."""
    name: str
    path: str
    type: Optional[str] = None


class FileInfoResponse(BaseModel):
    """File/directory information response."""
    name: str
    path: str
    type: str
    size: int
    permissions: str
    owner: str
    group: str
    modified_time: str


class ReadFileResponse(BaseModel):
    """Response with file content."""
    content: str
    path: str


@router.post("/write", response_model=WriteFileResponse)
async def write_file(sandbox_id: str, request: WriteFileRequest):
    """Write content to a file."""
    try:
        service = get_filesystem_service()
        info = service.write(sandbox_id, request.path, request.data, request.user)
        return WriteFileResponse(
            name=info.name,
            path=info.path,
            type=info.type.value if info.type else None,
        )
    except SandboxException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read", response_model=ReadFileResponse)
async def read_file(
    sandbox_id: str,
    path: str = Query(..., description="File path"),
    user: Optional[str] = Query(None, description="User to read as"),
):
    """Read file content."""
    try:
        service = get_filesystem_service()
        content = service.read(sandbox_id, path, format="text", user=user)
        return ReadFileResponse(content=content, path=path)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SandboxException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=List[FileInfoResponse])
async def list_directory(
    sandbox_id: str,
    path: str = Query(..., description="Directory path"),
    depth: int = Query(1, ge=1, le=10, description="Listing depth"),
    user: Optional[str] = Query(None, description="User to list as"),
):
    """List directory contents."""
    try:
        service = get_filesystem_service()
        entries = service.list(sandbox_id, path, depth, user)
        return [
            FileInfoResponse(
                name=e.name,
                path=e.path,
                type=e.type.value,
                size=e.size,
                permissions=e.permissions,
                owner=e.owner,
                group=e.group,
                modified_time=e.modified_time.isoformat(),
            )
            for e in entries
        ]
    except SandboxException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exists")
async def file_exists(
    sandbox_id: str,
    path: str = Query(..., description="File path"),
    user: Optional[str] = Query(None, description="User to check as"),
):
    """Check if file exists."""
    service = get_filesystem_service()
    exists = service.exists(sandbox_id, path, user)
    return {"exists": exists, "path": path}


@router.delete("/")
async def remove_file(
    sandbox_id: str,
    path: str = Query(..., description="File path"),
    user: Optional[str] = Query(None, description="User to remove as"),
):
    """Remove a file or directory."""
    try:
        service = get_filesystem_service()
        service.remove(sandbox_id, path, user)
        return {"success": True, "path": path}
    except SandboxException as e:
        raise HTTPException(status_code=500, detail=str(e))
