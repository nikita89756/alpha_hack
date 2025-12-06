from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

class BusinessBase(BaseModel):
    name: str
    description: str
    industry: Optional[str] = None

class BusinessCreate(BusinessBase):
    pass

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None

class BusinessResponse(BusinessBase):

    id: str = Field(alias="_id", serialization_alias="id") 
    user_id: str

    model_config = ConfigDict(
        populate_by_name=True, 
        extra='ignore'         
    )