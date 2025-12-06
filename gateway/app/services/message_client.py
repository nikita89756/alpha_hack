import httpx
import logging
import json
from datetime import datetime
import os
from confluent_kafka import Producer
from fastapi import HTTPException, status
from typing import List, Optional
from fastapi import BackgroundTasks


from app.core.config import Config
from app.schemas.chat import  ChatResponse
from app.schemas.message import SendMessageRequest, MessageResponse

logger = logging.getLogger(__name__)


class MessageServiceClient:
    def __init__(self, config: Config):
        self.base_url = config.MESSAGE_SERVICE_URL
        self.timeout = config.REQUEST_TIMEOUT
        self.kafka_producer = Producer({
                'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
                'client.id': 'api-gateway-title-requester'
            })
        
    async def create_chat(self, user_id: str) -> ChatResponse:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            request = {"title":"Новый чат"}
            try:
                response = await client.post(
                    f"{self.base_url}/chats/create",
                    params={"user_id": user_id},
                    json=request
                )
                response.raise_for_status()
                logger.info(f"Chat created for user: {user_id}")
                return ChatResponse(**response.json())
            except Exception as e:
                logger.error(f"Chat creation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create chat"
                )
    
    async def list_chats(self, user_id: str, limit: int, skip: int) -> List[ChatResponse]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/chats/list",
                    params={"user_id": user_id, "limit": limit, "skip": skip}
                )
                response.raise_for_status()
                return [ChatResponse(**chat) for chat in response.json()]
            except Exception as e:
                logger.error(f"Failed to fetch chats: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch chats"
                )
    
    async def get_chat(self, chat_id: str, user_id: str) -> ChatResponse:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/chats/{chat_id}",
                    params={"user_id": user_id}
                )
                response.raise_for_status()
                return ChatResponse(**response.json())
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Chat not found"
                    )
                raise
    async def delete_chat(self, chat_id: str, user_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/chats/{chat_id}",
                    params={"user_id": user_id}
                )
                response.raise_for_status()
                logger.info(f"Chat {chat_id} marked for deletion by user {user_id}")
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Chat to delete not found"
                    )
                logger.error(f"Failed to delete chat {chat_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete chat"
                )
            except Exception as e:
                logger.error(f"An unexpected error occurred while deleting chat {chat_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred while deleting chat"
                )
                
    async def check_if_first_message(self, chat_id: str) -> bool:
        """Проверяет, является ли это первым сообщением от пользователя (игнорируя сообщения от бота)"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/messages/history/{chat_id}",
                    params={"limit": 100}  
                )
                if response.status_code == 200:
                    data = response.json()
                    messages = data.get('messages', [])
                    
                    user_message_count = sum(1 for msg in messages if msg.get('message_type') == 'user')
                    
                    return user_message_count == 0
                return False
            except Exception as e:
                logger.error(f"Error checking message count: {e}")
                return False
    
    def request_title_generation(self, chat_id: str, user_id: str, message: str):
        try:
            request_data = {
                "chat_id": chat_id,
                "user_id": user_id,
                "first_message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.kafka_producer.produce(
                'chat_title_request',
                key=chat_id.encode('utf-8'),
                value=json.dumps(request_data).encode('utf-8')
            )
            self.kafka_producer.flush(timeout=5)
            
            logger.info(f"Title generation request sent for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error sending title request to Kafka: {e}")
    
    async def send_message(self, user_id: str, request: SendMessageRequest,background_tasks: BackgroundTasks) -> MessageResponse:

        is_first_message = await self.check_if_first_message(request.chat_id)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/messages/send",
                    json={
                        "user_id": user_id,
                        "message": request.message,
                        "chat_type": request.chat_type if request.chat_type else "",
                        "chat_id": request.chat_id,
                        "business_id": request.business_id if request.business_id else "",
                        "photo_description": request.photo_description if request.photo_description else "",
                        "photo_url": request.photo_url if request.photo_url else "",
                        "parsed_document": request.parsed_document if request.parsed_document else ""
                    }
                )
                response.raise_for_status()
                logger.info(f"Message sent in chat: {request.chat_id}")
                if is_first_message:
                    logger.info(f"First message detected, requesting title generation")
                    background_tasks.add_task(
                    self.request_title_generation,
                    request.chat_id,
                    user_id,
                    request.message
                )
                
                return MessageResponse(**response.json())
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Chat not found. Create a chat first using /chats/create"
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send message"
                )
    
    async def get_message_history(self, chat_id: str, user_id: str, limit: int) -> list:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/messages/history/{chat_id}",
                    params={"limit": limit, "user_id": user_id}
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to fetch message history: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch message history"
                )
    
    async def check_health(self) -> bool:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
            except:
                return False

    async def create_folder(self, user_id: str, request) -> dict:
        """Create a new folder"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                request_dict = request.model_dump()
                if request_dict.get('target_date') is not None:
                    if isinstance(request_dict['target_date'], datetime):
                        request_dict['target_date'] = request_dict['target_date'].isoformat()
                    elif isinstance(request_dict['target_date'], str):
                        pass
                response = await client.post(
                    f"{self.base_url}/folders/create",
                    params={"user_id": user_id},
                    json=request_dict
                )
                response.raise_for_status()
                logger.info(f"Folder created for user: {user_id}")
                return response.json()
            except Exception as e:
                logger.error(f"Folder creation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create folder"
                )

    async def list_folders(self, user_id: str, limit: int, skip: int) -> List[dict]:
        """List all folders for a user"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/folders/list",
                    params={"user_id": user_id, "limit": limit, "skip": skip}
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to fetch folders: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch folders"
                )

    async def get_folder(self, folder_id: str, user_id: str) -> dict:
        """Get folder details"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/folders/{folder_id}",
                    params={"user_id": user_id}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Folder not found"
                    )
                logger.error(f"Failed to fetch folder: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch folder"
                )

    async def get_folder_chats(self, folder_id: str, user_id: str, limit: int, skip: int) -> List[dict]:
        """Get all chats in a folder"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/folders/{folder_id}/chats",
                    params={"user_id": user_id, "limit": limit, "skip": skip}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Folder not found"
                    )
                logger.error(f"Failed to fetch folder chats: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch folder chats"
                )

    async def update_folder(self, folder_id: str, user_id: str, request) -> dict:
        """Update folder information"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.put(
                    f"{self.base_url}/folders/{folder_id}",
                    params={"user_id": user_id},
                    json=request.dict(exclude_none=True)
                )
                response.raise_for_status()
                logger.info(f"Folder {folder_id} updated by user {user_id}")
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Folder not found"
                    )
                logger.error(f"Failed to update folder: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update folder"
                )

    async def delete_folder(self, folder_id: str, user_id: str) -> dict:
        """Delete a folder (soft delete)"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/folders/{folder_id}",
                    params={"user_id": user_id}
                )
                response.raise_for_status()
                logger.info(f"Folder {folder_id} deleted by user {user_id}")
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Folder not found"
                    )
                logger.error(f"Failed to delete folder: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete folder"
                )

    async def move_chat_to_folder(self, chat_id: str, user_id: str, folder_id: Optional[str]) -> dict:
        """Move a chat to a different folder or to root"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.put(
                    f"{self.base_url}/chats/{chat_id}/move",
                    params={"user_id": user_id, "chat_id": chat_id},
                    json={"folder_id": folder_id}
                )
                response.raise_for_status()
                logger.info(f"Chat {chat_id} moved to folder {folder_id} by user {user_id}")
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Chat or folder not found"
                    )
                logger.error(f"Failed to move chat: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to move chat"
                )

    async def export_chat(self, chat_id: str, user_id: str, fmt: str = "md") -> httpx.Response:
        """Request chat export from Message Service and return the raw httpx.Response"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/chats/{chat_id}/export",
                    params={"user_id": user_id, "format": fmt}
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Chat not found"
                    )
                logger.error(f"Failed to export chat: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to export chat"
                )

    async def export_message(self, message_id: str, user_id: str, fmt: str = "md") -> httpx.Response:
        """Request message export from Message Service and return the raw httpx.Response"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/messages/{message_id}/export",
                    params={"user_id": user_id, "format": fmt}
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Message not found"
                    )
                elif e.response.status_code == 403:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this message"
                    )
                logger.error(f"Failed to export message: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to export message"
                )
