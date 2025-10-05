# backend/app/models/video.py
from pydantic import BaseModel, Field
from typing import List

class VideoGenerationRequest(BaseModel):
    student_name: str = Field(..., example="Rohan")
    topic: str = Field(..., example="Simple addition with numbers up to 10")
    artifacts: List[str] = Field(..., example=["Apple", "Banana"])
    character_preset: str = Field(..., example="doraemon")
    lang: str = Field(..., example="en", description="Language code: 'en', 'hi', or 'mr'")