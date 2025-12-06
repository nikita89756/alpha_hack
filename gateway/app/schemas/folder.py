"""Folder schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreateFolderRequest(BaseModel):
    """Request to create a new folder"""
    name: str = Field(..., min_length=1, max_length=100, description="Folder name")
    description: Optional[str] = Field(None, max_length=500, description="Optional folder description")
    target_date: Optional[datetime] = Field(None, description="Target date for the folder")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Support Tickets",
                "description": "All support conversations"
            }
        }


class UpdateFolderRequest(BaseModel):
    """Request to update folder information"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Folder Name",
                "description": "Updated description"
            }
        }


class MoveChatRequest(BaseModel):
    """Request to move a chat to a different folder"""
    folder_id: Optional[str] = Field(None, description="Target folder ID (null to move to root)")

    class Config:
        json_schema_extra = {
            "example": {
                "folder_id": "folder-abc123"
            }
        }


class FolderResponse(BaseModel):
    """Folder response model"""
    folder_id: str = Field(..., description="Unique folder identifier")
    user_id: str = Field(..., description="User who owns this folder")
    name: str = Field(..., description="Folder name")
    description: Optional[str] = Field(None, description="Folder description")
    target_date: Optional[datetime] = Field(None, description="Target date for the folder")
    chat_count: int = Field(default=0, description="Number of chats in folder")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(default=True, description="Whether folder is active")

    class Config:
        json_schema_extra = {
            "example": {
                "folder_id": "folder-abc123",
                "user_id": "user-123",
                "name": "Support Tickets",
                "description": "All support conversations",
                "chat_count": 5,
                "created_at": "2025-11-29T10:00:00Z",
                "updated_at": "2025-11-29T10:30:00Z",
                "is_active": True
            }
        }
