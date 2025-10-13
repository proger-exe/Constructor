from typing import Any, Dict, Union

from aiogram.utils.token import TokenValidationError, validate_token


def is_bot_token(value: str) -> Union[bool, Dict[str, Any]]:
    try:
        validate_token(value)
    except TokenValidationError:
        return False
    return True
