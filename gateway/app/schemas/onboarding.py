from typing import List, Union, Optional
from pydantic import BaseModel
class OnboardingCompleteRequest(BaseModel):
    business_id: str

    business_goals: List[str]
    business_description: str

    daily_tasks: List[str]
    daily_routine_description: str

    business_type: str  
    business_name: str
    city: str

    primary_pain_point: List[str]
    pain_description: str