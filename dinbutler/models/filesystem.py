from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class FileType(str, Enum):
    FILE = "file"
    DIR = "dir"
    SYMLINK = "symlink"

class FilesystemEventType(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"
    CHMOD = "chmod"

@dataclass
class WriteInfo:
    name: str
    path: str
    type: Optional[FileType] = None

@dataclass
class EntryInfo:
    name: str
    path: str
    type: FileType
    size: int
    mode: int
    permissions: str  # "rwxr-xr-x" format
    owner: str
    group: str
    modified_time: datetime
    symlink_target: Optional[str] = None

@dataclass
class FilesystemEvent:
    name: str  # relative path
    type: FilesystemEventType
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
