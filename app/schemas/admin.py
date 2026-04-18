from pydantic import BaseModel, Field


class AdminCommandRequest(BaseModel):
    command: str = Field(min_length=2, max_length=200)


class AdminCommandResponse(BaseModel):
    status: str
    output: str
    document_path: str | None = None

