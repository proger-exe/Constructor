"""Database initialisation helpers."""

from __future__ import annotations

from typing import Final

from tortoise import Tortoise

from tgbot.common.logging_setup import log

__all__ = ["start_db", "close_db"]


_DB_MODELS: Final = {"models": ["tgbot.database.models"]}
_DB_INITIALIZED: bool = False


async def start_db(db_dsn: str, *, generate_schemas: bool = True) -> None:
    """Initialise Tortoise ORM using provided DSN.

    Args:
        db_dsn: Database connection string compatible with Tortoise.
        generate_schemas: Whether to create database tables automatically.

    The function is idempotent: repeated calls with the same DSN are ignored.
    """

    global _DB_INITIALIZED

    if not db_dsn:
        raise ValueError("Database DSN must be provided")

    if _DB_INITIALIZED:
        return

    await Tortoise.init(db_url=db_dsn, modules=_DB_MODELS)
    if generate_schemas:
        await Tortoise.generate_schemas()

    _DB_INITIALIZED = True
    log.info("db_initialized")


async def close_db() -> None:
    """Close all database connections if they were initialised."""

    global _DB_INITIALIZED

    if not _DB_INITIALIZED:
        return

    await Tortoise.close_connections()
    _DB_INITIALIZED = False
    log.info("db_closed")
