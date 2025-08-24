from functools import wraps
from django.core.exceptions import PermissionDenied


def staff_or_committee_required(view_func):
    """
    Decorator that requires the user to be either staff or committee member.
    Similar to staff_member_required but also allows committee members.
    """

    def check_permissions(user):
        if not user.is_authenticated:
            return False
        return user.is_staff or user.is_committee

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not check_permissions(request.user):
            raise PermissionDenied(
                "You need to be staff or committee member to access this page."
            )
        return view_func(request, *args, **kwargs)

    return wrapped_view
