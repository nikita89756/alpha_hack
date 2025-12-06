from typing import Optional, Any, Dict
from pydantic import BaseModel

class WBKeyRequest(BaseModel):
    business_id: str
    api_key: Optional[str] = None

class WBPnLResponse(BaseModel):
    status: str
    user_id: str
    business_id: str
    key_source: Optional[str] = None  
    data: Dict[str, Any]
