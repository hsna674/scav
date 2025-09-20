"""
Custom model fields that ensure corrected timestamps
"""

from django.db import models
from django.utils import timezone


class CorrectedDateTimeField(models.DateTimeField):
    """DateTimeField that always uses Django's timezone.now() (which includes middleware offset)"""

    def __init__(self, *args, **kwargs):
        # Remove db_default if present (not supported in older Django versions)
        kwargs.pop("db_default", None)
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        """Override to ensure we always use timezone.now() (corrected by middleware)"""
        # If this is a default field (like timestamp or created_at)
        if self.auto_now or self.auto_now_add or (add and self.default == timezone.now):
            value = timezone.now()
            setattr(model_instance, self.attname, value)
            return value

        # For other cases, check if value is None and apply default
        value = getattr(model_instance, self.attname)
        if value is None and self.default == timezone.now:
            value = timezone.now()
            setattr(model_instance, self.attname, value)

        return value

    def get_prep_value(self, value):
        """Ensure the value is properly prepared for database storage"""
        value = super().get_prep_value(value)
        if value is not None:
            # Make sure timezone-aware datetimes are properly handled
            if timezone.is_naive(value):
                value = timezone.make_aware(value)
        return value
