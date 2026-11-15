from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class StudentLevel(models.IntegerChoices):
    LEVEL_100 = 100, "100"
    LEVEL_200 = 200, "200"
    LEVEL_300 = 300, "300"
    LEVEL_400 = 400, "400"
    LEVEL_500 = 500, "500"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    level = models.PositiveSmallIntegerField(choices=StudentLevel.choices)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(level__in=StudentLevel.values),
                name="core_studentprofile_supported_level",
            )
        ]

    def clean(self):
        super().clean()
        if self.pk and self.level is not None:
            previous_level = (
                type(self).objects.filter(pk=self.pk).values_list("level", flat=True).first()
            )
            if (
                previous_level is not None
                and previous_level != self.level
                and Registration.objects.filter(student_id=self.pk).exists()
            ):
                raise ValidationError(
                    {"level": "A student's level cannot change after registration."}
                )

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "level" in update_fields:
            self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.user.get_full_name() or self.user.get_username()


class Course(models.Model):
    code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=200)
    level = models.PositiveSmallIntegerField(choices=StudentLevel.choices)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(level__in=StudentLevel.values),
                name="core_course_supported_level",
            )
        ]
        ordering = ["code"]

    @staticmethod
    def normalize_code(code):
        return (code or "").strip().upper()

    def _validate_registered_level_change(self):
        if not self.pk:
            return

        previous_level = (
            type(self).objects.filter(pk=self.pk).values_list("level", flat=True).first()
        )
        if previous_level is None or previous_level == self.level:
            return

        has_incompatible_registration = RegistrationItem.objects.filter(
            course_id=self.pk
        ).exclude(registration__student__level=self.level).exists()
        if has_incompatible_registration:
            raise ValidationError(
                {"level": "This course's level cannot change while registrations depend on it."}
            )

    def clean(self):
        super().clean()
        self.code = self.normalize_code(self.code)
        self._validate_registered_level_change()

    def save(self, *args, **kwargs):
        self.code = self.normalize_code(self.code)
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "level" in update_fields:
            self._validate_registered_level_change()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.title}"


class Registration(models.Model):
    student = models.OneToOneField(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="registration",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    corrected_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Registration for {self.student}"


class RegistrationAudit(models.Model):
    class Action(models.TextChoices):
        COURSE_CORRECTION = "course_correction", "Course correction"
        REGISTRATION_RESET = "registration_reset", "Registration reset"
        ACCOUNT_DELETION = "account_deletion", "Account deletion"

    actor_username = models.CharField(max_length=150)
    target_user_id = models.CharField(max_length=64)
    target_username = models.CharField(max_length=150)
    target_full_name = models.CharField(max_length=150, blank=True)
    target_profile_id = models.CharField(max_length=64, blank=True)
    target_registration_id = models.CharField(max_length=64, blank=True)
    target_level = models.PositiveSmallIntegerField(blank=True, null=True)
    action = models.CharField(max_length=32, choices=Action.choices)
    reason = models.TextField()
    before_courses = models.JSONField(default=list)
    after_courses = models.JSONField(default=list)
    submitted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="registration_audit_events",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-created_at", "-pk"]


class RegistrationItem(models.Model):
    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name="items",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="registration_items",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["registration", "course"],
                name="core_registrationitem_unique_course",
            )
        ]

    def clean(self):
        super().clean()
        if not self.registration_id or not self.course_id:
            return

        student_level = Registration.objects.filter(pk=self.registration_id).values_list(
            "student__level", flat=True
        ).first()
        course_level = Course.objects.filter(pk=self.course_id).values_list(
            "level", flat=True
        ).first()
        if (
            student_level is not None
            and course_level is not None
            and student_level != course_level
        ):
            raise ValidationError(
                {"course": "The selected course must match the student's level."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.registration}: {self.course}"
