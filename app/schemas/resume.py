from pydantic import BaseModel, Field


class ResumeQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class ResumeAnswer(BaseModel):
    answer: str
    provider: str
    used_fallback: bool = False
