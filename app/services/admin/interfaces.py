from typing import Protocol, Optional, List, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel
from schemas.user import UserRole

# Improve type safety for LLM without circular imports
class LLMServiceProtocol(Protocol):
    async def answer_question(self, q: str) -> tuple[str, str, bool]: ...
    async def answer_general_question(self, q: str) -> tuple[str, str, bool]: ...

class CommandContext(BaseModel):
    """Metadata about the command execution."""
    raw_command: str
    intent: str
    cmd_args: List[str]
    user_id: int
    role: UserRole
    is_ai_mode: bool

class CommandResult(BaseModel):
    """Structured data returned by handlers (Service Layer)."""
    success: bool
    data: Optional[Any] = None
    message: str
    document_path: Optional[str] = None

class CommandHandler(ABC):
    """Base interface for all admin command units."""
    @abstractmethod
    async def handle(self, ctx: CommandContext) -> CommandResult:
        pass
