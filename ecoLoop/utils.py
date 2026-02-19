from rest_framework.response import Response
from rest_framework import status


def api_response(
    result=None,
    is_success=False,
    error_message=None,
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
):
    return Response(
        {
            "StatusCode": status_code,
            "IsSuccess": is_success,
            "ErrorMessage": error_message if error_message else [],
            "Result": result,
        },
        status=status_code,
    )


def log_admin_action(
    admin,
    action,
    target_type,
    target_id,
    target_name,
    result="success",
    reason=None,
):
    """
    Helper function to log admin activities.

    Args:
        admin: The admin User object who performed the action
        action: Action type (must match AdminActivityLog.ACTION_CHOICES)
        target_type: Type of target entity (e.g., "User", "Listing", "NGO")
        target_id: ID of the target entity
        target_name: Name or description of the target
        result: Result of the action ("success", "failed", "pending")
        details: Additional details about the action
        reason: Reason for performing the action
        request: Django request object to extract IP address

    Returns:
        AdminActivityLog object

    Example:
        log_admin_action(
            admin=request.user,
            action="user_blocked",
            target_type="User",
            target_id=str(user.id),
            target_name=f"{user.full_name} ({user.email})",
            reason="Multiple reports of fraudulent activity",
            request=request
        )
    """
    from accounts.models import AdminActivityLog


    return AdminActivityLog.objects.create(
        admin=admin,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        target_name=target_name,
        result=result,
        reason=reason,
    )
