"""
Custom model fields that ensure corrected timestamps
"""

from django.db import models
from django.utils import timezone


class CorrectedDateTimeField(models.DateTimeField):
    """DateTimeField that uses globally corrected timezone.now()"""

    def __init__(self, *args, **kwargs):
        # Remove db_default if present (not supported in older Django versions)
        kwargs.pop("db_default", None)
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        """Override to ensure we use corrected timezone.now() for auto fields"""
        # Handle auto_now and auto_now_add fields
        if self.auto_now or (self.auto_now_add and add):
            value = timezone.now()
            setattr(model_instance, self.attname, value)
            return value

        # Handle default=timezone.now fields when value is None
        value = getattr(model_instance, self.attname)
        if value is None and callable(self.default):
            # Call the default function (timezone.now) to get corrected time
            value = self.default()
            setattr(model_instance, self.attname, value)

        return super().pre_save(model_instance, add)
