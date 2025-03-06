from sqlalchemy import Column, DateTime, BigInteger, String, ForeignKey, Boolean, func
from sqlmodel import SQLModel, Field
from datetime import datetime


# ✅ Модель пользователя (ОТДЕЛЬНО добавляем поля `created_at` и `updated_at`)
class User(SQLModel, table=True):
    __tablename__ = "users"

    user_id: int = Field(sa_column=Column(BigInteger, primary_key=True, nullable=False))
    username: str = Field(nullable=False, max_length=50)
    phone_number: str = Field(nullable=False, max_length=50, default="Не указан")
    is_admin: bool = Field(sa_column=Column(Boolean, default=False, nullable=False))

    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()))



# ✅ Модель каналов
class Channel(SQLModel, table=True):
    __tablename__ = "channels"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id"), nullable=False))
    name: str = Field(nullable=False, max_length=50)
    chat_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    language: str = Field(nullable=False, max_length=10)
    description: str = Field(default=None, nullable=True, max_length=255)

    # ✅ Явно добавляем `created_at` и `updated_at`
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()))


# ✅ Модель настроек
class Settings(SQLModel, table=True):
    __tablename__ = "settings"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id"), nullable=False))
    key: str = Field(sa_column=Column(String, unique=False, nullable=False))
    value: str = Field(sa_column=Column(String, nullable=True))
    value_name: str = Field(sa_column=Column(String, nullable=True))

    # ✅ Явно добавляем `created_at` и `updated_at`
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()))


# ✅ Модель статистики
class Statistics(SQLModel, table=True):
    __tablename__ = "statistics"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id"), nullable=False))
    messages_sent: int = Field(default=0, nullable=False)
    words_translated: int = Field(default=0, nullable=False)
    characters_translated: int = Field(default=0, nullable=False)

    # ✅ Явно добавляем `created_at` и `updated_at`
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()))
