from typing import Dict, Type, Any
from services.admin.interfaces import CommandHandler
from core.logger import get_logger

logger = get_logger(__name__)

class ActionRegistry:
    """
    A singleton-style registry that allows command handlers to register 
    themselves using decorators.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ActionRegistry, cls).__new__(cls)
            cls._instance._handlers = {}
        return cls._instance

    def register(self, *intents: str):
        """Decorator to register a CommandHandler for one or more intents."""
        def decorator(handler_cls: Type[CommandHandler]):
            for intent in intents:
                self._handlers[intent.lower()] = handler_cls
                logger.info(f"🆕 Handler '{handler_cls.__name__}' -> /{intent}", extra={"intent": intent, "handler": handler_cls.__name__})
            return handler_cls
        return decorator

    def get_handler_classes(self) -> Dict[str, Type[CommandHandler]]:
        return self._handlers

# Global instance for use across the admin module
action_registry = ActionRegistry()
