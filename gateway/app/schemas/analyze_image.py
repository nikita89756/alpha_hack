
from pydantic import BaseModel
class ImageAnalysisResponse(BaseModel):
    success: bool
    description: str
    error: str
    image_url: str