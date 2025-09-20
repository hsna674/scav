import logging

from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.utils import timezone as tz

from ..main.models import Challenge
from ..logging.fields import CorrectedDateTimeField

logger = logging.getLogger(__name__)


class UserManager(DjangoUserManager):
    pass


class User(AbstractBaseUser):
    objects = UserManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "is_student", "graduation_year"]

    id = models.AutoField(primary_key=True)

    username = models.CharField(unique=True, max_length=32, null=False, blank=False)
    first_name = models.CharField(max_length=35, null=False, blank=False)
    last_name = models.CharField(max_length=70, null=False, blank=False)
    is_student = models.BooleanField(default=False, null=False)
    graduation_year = models.IntegerField(null=True)
    email = models.EmailField(max_length=50, null=False, blank=False)
    is_superuser = models.BooleanField(default=False, null=False)
    _is_staff = models.BooleanField(default=False, null=False)
    is_committee = models.BooleanField(default=False, null=False)
    dark_mode = models.BooleanField(default=False, null=False)

    challenges_done = models.ManyToManyField(
        Challenge, related_name="users_that_completed", blank=True
    )

    last_submission_time = CorrectedDateTimeField(default=tz.now)

    date_joined = CorrectedDateTimeField(auto_now_add=True)

    def has_perm(self, perm, obj=None) -> bool:  # pylint: disable=unused-argument
        return self.is_superuser

    def has_module_perms(self, app_label) -> bool:  # pylint: disable=unused-argument
        return self.is_superuser

    @property
    def is_staff(self) -> bool:
        return self._is_staff or self.is_superuser

    @is_staff.setter
    def is_staff(self, staff: bool) -> None:
        self._is_staff = staff

    @property
    def full_name(self) -> str:
        return self.first_name + " " + self.last_name

    @property
    def short_name(self) -> str:
        return self.first_name

    def get_full_name(self) -> str:
        return self.full_name

    def get_short_name(self) -> str:
        return self.short_name

    def get_social_auth(self):
        return self.social_auth.get(provider="ion")

    def __str__(self):
        return self.username

    def __repr__(self):
        return "<User: {} ({})>".format(self.username, self.id)

    def is_participant(self):
        return self.is_student and not self.is_superuser

    class Meta:
        indexes = [
            models.Index(fields=["graduation_year"], name="user_graduation_year_idx"),
        ]


class Group(models.Model):
    id = models.AutoField(primary_key=True)
    is_service = models.BooleanField(default=False)
    name = models.CharField(max_length=32)
    users = models.ManyToManyField(User, related_name="unix_groups")

    def __str__(self):
        return self.name
