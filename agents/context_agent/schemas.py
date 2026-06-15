from pydantic import BaseModel, Field
from typing import List


class Skill(BaseModel):
    name: str
    importance: float = Field(
        ge=0.0,
        le=1.0,
    )


class JobContext(BaseModel):
    role: str

    required_skills: List[Skill]

    preferred_skills: List[Skill]