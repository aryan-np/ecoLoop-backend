from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return getattr(obj, "user_id", None) == getattr(request.user, "id", None)


class IsOwnerOrReadOnlyProduct(BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return getattr(obj, "owner_id", None) == getattr(request.user, "id", None)


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission:
    - Regular users can only access/modify their own profile
    - Admins/staff can access/modify any profile
    """

    def has_object_permission(self, request, view, obj):
        # Admins and staff can do anything
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Regular users can only access their own profile
        return getattr(obj, "user_id", None) == getattr(request.user, "id", None)


class IsSuperUser(BasePermission):
    """
    Allows access only to superusers (admins).
    """

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_superuser
        )


class IsNGO(BasePermission):
    """
    Allows access only to users with NGO role.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.roles.filter(name="NGO").exists()


class IsRecycler(BasePermission):
    """
    Allows access only to users with RECYCLER role.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.roles.filter(name="RECYCLER").exists()
