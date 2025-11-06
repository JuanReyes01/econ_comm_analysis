from pydantic import BaseModel, Field
from typing import List

class Degree(BaseModel):
    degree_type: str = Field(..., description="...")
    degree_field: List[str] = Field(..., description="...")

class AuthorDegrees(BaseModel):
    studies: List[Degree]