"""
Custom model fields that ensure corrected timestamps
"""

from django.db import models
from django.utils import timezone


class CorrectedDateTimeField(models.DateTimeField):
    """DateTimeField that uses globally corrected timezone.now() - simplified for admin compatibility"""

    def __init__(self, *args, **kwargs):
        # Remove db_default if present (not supported in older Django versions)
        kwargs.pop("db_default", None)
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        """Simplified pre_save that relies on global timezone.now() patching"""
        # For fields with default=timezone.now, ensure we call it when value is None
        if self.default == timezone.now:
            value = getattr(model_instance, self.attname)
            if value is None:
                value = timezone.now()
                setattr(model_instance, self.attname, value)
                return value

        return super().pre_save(model_instance, add)
