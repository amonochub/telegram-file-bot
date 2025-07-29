"""
Enhanced error handling utilities for the bot.

Provides consistent error handling, logging, and user feedback
across the entire application.
"""

import inspect
import traceback
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union

import structlog
from aiogram.types import CallbackQuery, Message

from app.constants.messages import ERROR_GENERIC, ERROR_NETWORK, ERROR_INVALID_INPUT

log = structlog.get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class BotError(Exception):
    """Base exception for bot-specific errors."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message)
        self.user_message = user_message or message


class ValidationError(BotError):
    """Error in user input validation."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message, user_message or ERROR_INVALID_INPUT)


class NetworkError(BotError):
    """Network-related error."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message, user_message or ERROR_NETWORK)


class ServiceError(BotError):
    """Service-related error."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message, user_message or ERROR_GENERIC)


def handle_errors(
    user_error_message: Optional[str] = None,
    log_level: str = "error",
    suppress_exceptions: bool = False,
) -> Callable[[F], F]:
    """
    Decorator for consistent error handling in bot handlers.
    
    Args:
        user_error_message: Custom error message for users
        log_level: Logging level for errors (debug, info, warning, error)
        suppress_exceptions: Whether to suppress exceptions and return None
        
    Usage:
        @handle_errors("Failed to process your request")
        async def my_handler(message: Message):
            # handler code
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BotError as e:
                await _handle_bot_error(e, args, func.__name__, log_level)
                if not suppress_exceptions:
                    raise
                return None
            except Exception as e:
                await _handle_generic_error(
                    e, args, func.__name__, user_error_message, log_level
                )
                if not suppress_exceptions:
                    raise
                return None
        return wrapper
    return decorator


async def _handle_bot_error(
    error: BotError, 
    args: tuple, 
    func_name: str, 
    log_level: str
) -> None:
    """Handle bot-specific errors."""
    context = _extract_context(args)
    
    # Log the error
    logger_method = getattr(log, log_level, log.error)
    logger_method(
        "Bot error occurred",
        function=func_name,
        error_type=type(error).__name__,
        error_message=str(error),
        **context,
    )
    
    # Send user message if available
    message_obj = _get_message_object(args)
    if message_obj and error.user_message:
        try:
            await message_obj.answer(error.user_message)
        except Exception as send_error:
            log.warning(
                "Failed to send error message to user",
                error=str(send_error),
                **context,
            )


async def _handle_generic_error(
    error: Exception,
    args: tuple,
    func_name: str,
    user_error_message: Optional[str],
    log_level: str,
) -> None:
    """Handle generic exceptions."""
    context = _extract_context(args)
    
    # Log the error with traceback
    logger_method = getattr(log, log_level, log.error)
    logger_method(
        "Unexpected error occurred",
        function=func_name,
        error_type=type(error).__name__,
        error_message=str(error),
        traceback=traceback.format_exc(),
        **context,
    )
    
    # Send user message
    message_obj = _get_message_object(args)
    if message_obj:
        error_msg = user_error_message or ERROR_GENERIC
        try:
            await message_obj.answer(error_msg)
        except Exception as send_error:
            log.warning(
                "Failed to send error message to user",
                error=str(send_error),
                **context,
            )


def _extract_context(args: tuple) -> dict[str, Any]:
    """Extract context information from handler arguments."""
    context = {}
    
    for arg in args:
        if isinstance(arg, (Message, CallbackQuery)):
            context.update({
                "user_id": arg.from_user.id if arg.from_user else None,
                "chat_id": arg.message.chat.id if hasattr(arg, 'message') and arg.message else getattr(arg, 'chat', {}).get('id'),
                "message_id": arg.message.message_id if hasattr(arg, 'message') and arg.message else getattr(arg, 'message_id'),
            })
            break
    
    return context


def _get_message_object(args: tuple) -> Optional[Union[Message, CallbackQuery]]:
    """Get the message object from handler arguments."""
    for arg in args:
        if isinstance(arg, (Message, CallbackQuery)):
            return arg
    return None


def safe_async(
    default_return: Any = None,
    log_errors: bool = True,
) -> Callable[[F], F]:
    """
    Decorator to safely execute async functions with error handling.
    
    Args:
        default_return: Value to return on error
        log_errors: Whether to log errors
        
    Returns:
        Decorated function that won't raise exceptions
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    log.error(
                        "Error in safe async execution",
                        function=func.__name__,
                        error=str(e),
                        args=str(args)[:100],  # Limit log size
                        kwargs=str(kwargs)[:100],
                    )
                return default_return
        return wrapper
    return decorator


def validate_input(
    condition: bool,
    error_message: str,
    user_message: Optional[str] = None,
) -> None:
    """
    Validate input condition and raise ValidationError if false.
    
    Args:
        condition: Condition to validate
        error_message: Internal error message
        user_message: User-friendly error message
        
    Raises:
        ValidationError: If condition is False
    """
    if not condition:
        raise ValidationError(error_message, user_message)


def require_not_none(value: Any, name: str) -> Any:
    """
    Ensure value is not None.
    
    Args:
        value: Value to check
        name: Name of the value for error message
        
    Returns:
        The value if not None
        
    Raises:
        ValidationError: If value is None
    """
    if value is None:
        raise ValidationError(f"{name} cannot be None", f"Отсутствует обязательный параметр: {name}")
    return value