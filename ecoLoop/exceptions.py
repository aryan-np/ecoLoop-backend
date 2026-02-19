"""
Custom exception handler for Django REST Framework
Location: ecoLoop/exceptions.py
"""

from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from loguru import logger
from .utils import api_response


def format_error_messages(error_data):
    """
    Format DRF error messages into clean, readable strings.
    Handles nested errors, field errors, and non-field errors.
    """
    if isinstance(error_data, dict):
        messages = []
        for field, errors in error_data.items():
            if field == "non_field_errors":
                # Don't prefix non-field errors
                messages.extend(format_error_messages(errors))
            else:
                # Prefix field-specific errors with field name
                field_errors = format_error_messages(errors)
                messages.extend([f"{field}: {err}" for err in field_errors])
        return messages
    elif isinstance(error_data, list):
        messages = []
        for error in error_data:
            if isinstance(error, str):
                messages.append(error)
            elif hasattr(error, "code"):
                # Handle ErrorDetail objects
                messages.append(str(error))
            elif isinstance(error, dict):
                messages.extend(format_error_messages(error))
            else:
                messages.append(str(error))
        return messages
    elif isinstance(error_data, str):
        return [error_data]
    elif hasattr(error_data, "code"):
        # Handle single ErrorDetail object
        return [str(error_data)]
    else:
        return [str(error_data)]


def custom_exception_handler(exc, context):
    """
    Custom exception handler that:
    1. Formats the response using api_response
    2. Logs all exceptions to Loguru
    3. Properly formats validation errors
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Prepare logging context
    request = context.get("request")
    view = context.get("view")

    # Escape curly braces in exception message to prevent format() errors
    exc_message = str(exc).replace("{", "{{").replace("}", "}}")

    log_context = {
        "exception_class": exc.__class__.__name__,
        "exception_message": exc_message,
        "path": request.path if request else "N/A",
        "method": request.method if request else "N/A",
        "view": view.__class__.__name__ if view else "N/A",
        "user": (
            str(request.user) if request and hasattr(request, "user") else "Anonymous"
        ),
    }

    if response is not None:
        # Add status code to context
        log_context["status_code"] = response.status_code

        # Extract clean error messages
        error_messages = format_error_messages(response.data)

        # Format response using your api_response function
        response.data = api_response(
            result=None,  # Don't include error details in Result
            is_success=False,
            error_message=error_messages,
            status_code=response.status_code,
        ).data

        # Log based on status code severity
        if response.status_code >= 500:
            # Server errors (500+) - log as ERROR with full traceback
            logger.error(
                f"Server Error [{response.status_code}]: {log_context['exception_class']} - {log_context['exception_message']}",
                extra=log_context,
            )
            logger.exception(f"Full traceback for {log_context['exception_class']}")
        elif response.status_code >= 400:
            # Client errors (400-499) - log as WARNING (no traceback needed)
            logger.warning(
                f"Client Error [{response.status_code}]: {log_context['exception_class']} - {log_context['exception_message']}",
                extra=log_context,
            )
    else:
        # Unhandled exception (no response) - log as CRITICAL
        logger.critical(
            f"Unhandled Exception: {log_context['exception_class']} - {log_context['exception_message']}",
            extra=log_context,
        )
        logger.exception(
            f"Full traceback for unhandled {log_context['exception_class']}"
        )

    return response
