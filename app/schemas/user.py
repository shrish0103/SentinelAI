from enum import Enum

class UserRole(str, Enum):
    GUEST = "guest"
    DEMO = "demo"
    ADMIN = "admin"
