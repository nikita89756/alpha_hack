from typing import Optional, List, Annotated
import os
from fastapi import FastAPI, HTTPException, Body, status, Header
from fastapi.responses import Response
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
DB_NAME = os.getenv("DB_NAME", "chatbot_db")
client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]
business_collection = db["businesses"]

app = FastAPI(title="Business Service (Header Auth)")

PyObjectId = Annotated[str, BeforeValidator(str)]

class BusinessBase(BaseModel):
    name: str = Field(..., example="My Cool Startup")
    description: str = Field(..., example="We sell AI solutions")
    industry: Optional[str] = Field(None, example="IT")

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None

class BusinessDB(BusinessBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str = Field(..., description="Владелец (из заголовка)")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

@app.post("/businesses/", response_model=BusinessDB, status_code=status.HTTP_201_CREATED)
async def create_business(
    business_in: BusinessBase,
    x_user_id: Annotated[str, Header()]
):
    """
    Создать бизнес. Владелец берется из заголовка X-User-Id.
    В теле запроса user_id передавать НЕ нужно.
    """
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")

    business_dict = business_in.model_dump()

    business_dict["user_id"] = x_user_id
    
    new_business = await business_collection.insert_one(business_dict)
    
    created_doc = await business_collection.find_one({"_id": new_business.inserted_id})
    return created_doc


@app.get("/businesses/", response_model=List[BusinessDB])
async def list_my_businesses(
    x_user_id: Annotated[str, Header()]
):
    """
    Получить ВСЕ бизнесы текущего пользователя (того, чей ID в заголовке).
    """
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")

    businesses = await business_collection.find({"user_id": x_user_id}).to_list(100)
    return businesses


@app.get("/businesses/{business_id}", response_model=BusinessDB)
async def get_business(
    business_id: str,
    x_user_id: Annotated[str, Header()] 
):
    """
    Получить конкретный бизнес по ID.
    Мы также проверяем, принадлежит ли он пользователю из заголовка.
    """
    try:
        oid = ObjectId(business_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    doc = await business_collection.find_one({"_id": oid})
    
    if not doc:
        raise HTTPException(status_code=404, detail="Business not found")

    if doc["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Access denied: You do not own this business")

    return doc


@app.patch("/businesses/{business_id}", response_model=BusinessDB)
async def update_business(
    business_id: str,
    update_data: BusinessUpdate,
    x_user_id: Annotated[str, Header()]
):
    """
    Обновить бизнес. Можно менять только свои бизнесы.
    """
    try:
        oid = ObjectId(business_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    existing_doc = await business_collection.find_one({"_id": oid})
    if not existing_doc:
        raise HTTPException(status_code=404, detail="Business not found")
    
    if existing_doc["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    data_to_update = {k: v for k, v in update_data.model_dump(exclude_unset=True).items()}
    
    if data_to_update:
        await business_collection.update_one({"_id": oid}, {"$set": data_to_update})

    updated_doc = await business_collection.find_one({"_id": oid})
    return updated_doc


@app.delete("/businesses/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business(
    business_id: str,
    x_user_id: Annotated[str, Header()]
):
    try:
        oid = ObjectId(business_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    result = await business_collection.delete_one({
        "_id": oid,
        "user_id": x_user_id 
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Business not found or access denied")
        
    return Response(status_code=status.HTTP_204_NO_CONTENT)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)