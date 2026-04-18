from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from .database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """
    Auth user table managed by FastAPI Users.
    Inherits: id (UUID), email, hashed_password, is_active, is_superuser, is_verified.
    """
    pass
