# Admin Activity Logging - Usage Guide

## Overview
The `AdminActivityLog` model tracks all administrative actions performed on the platform, providing a complete audit trail.

## Database Model

The model includes:
- **admin**: The admin who performed the action
- **action**: Type of action (blocked user, approved NGO, etc.)
- **target_type**: Type of entity (User, Listing, NGO, etc.)
- **target_id**: ID of the target entity
- **target_name**: Name/description of the target
- **result**: Success, failed, or pending
- **details**: Additional information
- **reason**: Reason for the action
- **ip_address**: Admin's IP address
- **timestamp**: When the action occurred

## Available Actions

```python
ACTION_CHOICES = [
    ("user_blocked", "Blocked User"),
    ("user_unblocked", "Unblocked User"),
    ("user_deleted", "Deleted User"),
    ("user_role_changed", "Changed User Role"),
    ("ngo_approved", "Approved NGO"),
    ("ngo_rejected", "Rejected NGO"),
    ("recycler_approved", "Approved Recycler"),
    ("recycler_rejected", "Rejected Recycler"),
    ("listing_removed", "Removed Listing"),
    ("listing_restored", "Restored Listing"),
    ("report_resolved", "Resolved Report"),
    ("report_closed", "Closed Report"),
    ("dispute_resolved", "Resolved Dispute"),
    ("verification_approved", "Approved Verification"),
    ("verification_rejected", "Rejected Verification"),
    ("other", "Other Action"),
]
```

## Usage Examples

### Example 1: Blocking a User

```python
from ecoLoop.utils import log_admin_action

# In your view where you block a user
@action(detail=True, methods=['post'])
def block_user(self, request, pk=None):
    user = self.get_object()
    user.is_active = False
    user.save()
    
    # Log the admin action
    log_admin_action(
        admin=request.user,
        action="user_blocked",
        target_type="User",
        target_id=str(user.id),
        target_name=f"{user.full_name} (ID: {user.id})",
        reason=request.data.get('reason', 'No reason provided'),
        details=f"User {user.email} blocked",
        request=request
    )
    
    return Response({"message": "User blocked successfully"})
```

### Example 2: Approving an NGO Application

```python
from ecoLoop.utils import log_admin_action
from accounts.models import RoleApplication, Role

@action(detail=True, methods=['post'])
def approve_application(self, request, pk=None):
    application = self.get_object()
    application.status = 'approved'
    application.reviewed_by = request.user
    application.reviewed_at = timezone.now()
    application.save()
    
    # Grant the role
    ngo_role, _ = Role.objects.get_or_create(name='NGO')
    application.user.roles.add(ngo_role)
    
    # Log the admin action
    log_admin_action(
        admin=request.user,
        action="ngo_approved",
        target_type="NGO",
        target_id=str(application.id),
        target_name=f"{application.organization_name} (ID: {application.id})",
        details="All verification documents approved",
        request=request
    )
    
    return Response({"message": "Application approved"})
```

### Example 3: Removing a Listing

```python
from ecoLoop.utils import log_admin_action

@action(detail=True, methods=['delete'])
def remove_listing(self, request, pk=None):
    listing = self.get_object()
    listing_name = listing.name
    listing_id = listing.id
    
    listing.delete()
    
    # Log the admin action
    log_admin_action(
        admin=request.user,
        action="listing_removed",
        target_type="Listing",
        target_id=str(listing_id),
        target_name=f"Prohibited item (ID: {listing_id})",
        reason="Violated platform policies",
        request=request
    )
    
    return Response({"message": "Listing removed"})
```

### Example 4: Resolving a Dispute

```python
from ecoLoop.utils import log_admin_action

@action(detail=True, methods=['post'])
def resolve_dispute(self, request, pk=None):
    dispute = self.get_object()
    dispute.status = 'resolved'
    dispute.resolution = request.data.get('resolution')
    dispute.save()
    
    # Log the admin action
    log_admin_action(
        admin=request.user,
        action="dispute_resolved",
        target_type="Dispute",
        target_id=str(dispute.id),
        target_name=f"Case #{dispute.case_number}",
        details="Refund processed to buyer",
        request=request
    )
    
    return Response({"message": "Dispute resolved"})
```

## Querying Admin Logs

### Get all logs for a specific admin
```python
from accounts.models import AdminActivityLog

admin_logs = AdminActivityLog.objects.filter(admin=admin_user)
```

### Get logs for a specific action type
```python
blocked_users = AdminActivityLog.objects.filter(action='user_blocked')
```

### Get logs for a specific target
```python
user_logs = AdminActivityLog.objects.filter(
    target_type='User',
    target_id=str(user_id)
)
```

### Get logs within a date range
```python
from django.utils import timezone
from datetime import timedelta

last_week = timezone.now() - timedelta(days=7)
recent_logs = AdminActivityLog.objects.filter(
    timestamp__gte=last_week
)
```

## Displaying Logs (Like Your Table)

```python
# In your admin dashboard view
def get_admin_logs(request):
    logs = AdminActivityLog.objects.select_related('admin').order_by('-timestamp')
    
    # Format for display
    formatted_logs = []
    for log in logs:
        formatted_logs.append({
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'admin': log.admin.full_name if log.admin else 'System',
            'action': log.get_action_display(),
            'target_entity': f"{log.target_type}: {log.target_name}",
            'result': log.get_result_display(),
            'details': log.details or log.reason or '-'
        })
    
    return formatted_logs
```

## Next Steps

1. Run migrations:
   ```bash
   python manage.py makemigrations accounts
   python manage.py migrate
   ```

2. Add the logging calls to your existing admin views

3. Access logs via Django admin at `/admin/accounts/adminactivitylog/`

4. Create custom views/API endpoints to display logs in your admin dashboard
