"""
Custom model fields that ensure corrected timestamps
"""

from django.db import models
from django.utils import timezone


class CorrectedDateTimeField(models.DateTimeField):
    """DateTimeField that always uses Django's timezone.now() instead of database time"""

    def __init__(self, *args, **kwargs):
        # Force db_default to None so Django uses Python defaults
        kwargs["db_default"] = None
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        """Override to ensure we always use timezone.now()"""
        # Always set the value explicitly using timezone.now()
        value = getattr(model_instance, self.attname)
        if value is None:
            value = timezone.now()
            setattr(model_instance, self.attname, value)
        return value
