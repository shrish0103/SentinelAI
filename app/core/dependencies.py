from functools import lru_cache

from core.config import Settings, get_settings as load_settings
from services.admin import AdminService
from services.event_store import EventStore
from services.health import HealthService
from services.llm import LLMService
from services.notifier import TelegramNotifier
from services.demo import DemoService


@lru_cache
def get_event_store() -> EventStore:
    return EventStore()


@lru_cache
def get_notifier() -> TelegramNotifier:
    return TelegramNotifier(settings=load_settings())


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService(settings=load_settings())


@lru_cache
def get_health_service() -> HealthService:
    return HealthService(
        settings=load_settings(),
        notifier=get_notifier(),
        event_store=get_event_store(),
    )


@lru_cache
def get_demo_service() -> DemoService:
    return DemoService(settings=load_settings())



@lru_cache
def get_admin_service() -> AdminService:
    return AdminService(
        event_store=get_event_store(),
        health_service=get_health_service(),
        llm_service=get_llm_service(),
        notifier=get_notifier(),
        demo_service=get_demo_service(),
        settings=load_settings(),
    )


def get_settings_dependency() -> Settings:
    return load_settings()


get_settings = get_settings_dependency
