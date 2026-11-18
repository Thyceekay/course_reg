"""Django admin registrations and the audited registration-correction workflow."""

from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .forms import RegistrationCorrectionForm
from .models import (
    Course,
    Registration,
    RegistrationAudit,
    RegistrationItem,
    StudentProfile,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "level")
    list_filter = ("level",)
    search_fields = ("code", "title")
    actions = None


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "username",
        "level",
        "submission_status",
        "submitted_at",
        "selected_courses",
    )
    list_filter = ("level",)
    search_fields = ("user__first_name", "user__last_name", "user__username")
    fields = (
        "full_name",
        "username",
        "level",
        "submission_status",
        "submitted_at",
        "selected_courses",
    )
    readonly_fields = (
        "full_name",
        "username",
        "submission_status",
        "submitted_at",
        "selected_courses",
    )
    actions = None

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user", "registration")
            .prefetch_related("registration__items__course")
        )

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and Registration.objects.filter(student_id=obj.pk).exists():
            fields.append("level")
        return fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Full name", ordering="user__first_name")
    def full_name(self, obj):
        return obj.user.get_full_name() or "—"

    @admin.display(description="Username", ordering="user__username")
    def username(self, obj):
        return obj.user.get_username()

    @admin.display(description="Submission status")
    def submission_status(self, obj):
        return "Submitted" if self._registration(obj) else "Not submitted"

    @admin.display(description="Submitted at", ordering="registration__submitted_at")
    def submitted_at(self, obj):
        registration = self._registration(obj)
        return registration.submitted_at if registration else "—"

    @admin.display(description="Selected courses")
    def selected_courses(self, obj):
        registration = self._registration(obj)
        if not registration:
            return "—"
        return ", ".join(str(item.course) for item in registration.items.all()) or "—"

    @staticmethod
    def _registration(obj):
        try:
            return obj.registration
        except Registration.DoesNotExist:
            return None


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "student_name",
        "student_username",
        "student_level",
        "submitted_at",
        "selected_courses",
    )
    list_filter = ("student__level",)
    search_fields = (
        "student__user__first_name",
        "student__user__last_name",
        "student__user__username",
        "items__course__code",
        "items__course__title",
    )
    fields = (
        "student_name",
        "student_username",
        "student_level",
        "submitted_at",
        "selected_courses",
    )
    readonly_fields = fields
    actions = None

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("student__user")
            .prefetch_related("items__course")
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm(
            "core.view_registration"
        ) or request.user.has_perm("core.change_registration")

    @staticmethod
    def has_correction_permission(request):
        return request.user.has_perm("core.change_registration")

    def has_delete_permission(self, request, obj=None):
        return False

    def get_list_display(self, request):
        columns = super().get_list_display(request)
        if self.has_correction_permission(request):
            return (*columns, "correction_link")
        return columns

    def get_urls(self):
        custom_urls = [
            path(
                "<path:object_id>/correct/",
                self.admin_site.admin_view(self.correct_view),
                name="core_registration_correct",
            )
        ]
        return custom_urls + super().get_urls()

    def correct_view(self, request, object_id):
        if not self.has_correction_permission(request):
            raise PermissionDenied

        registration = get_object_or_404(
            self.get_queryset(request),
            pk=object_id,
        )
        initial = {
            "courses": registration.items.values_list("course_id", flat=True)
        }
        form = RegistrationCorrectionForm(
            request.POST if request.method == "POST" else None,
            initial=initial,
            level=registration.student.level,
        )
        if request.method == "POST" and form.is_valid():
            try:
                self.apply_correction(
                    registration.pk,
                    list(form.cleaned_data["courses"]),
                    actor=request.user,
                    reason=form.cleaned_data["reason"],
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, "The registration correction was saved.")
                return redirect("admin:core_registration_changelist")

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "original": registration,
            "title": f"Correct registration for {registration.student}",
            "form": form,
        }
        return TemplateResponse(
            request,
            "admin/core/registration/correct.html",
            context,
        )

    @transaction.atomic
    def apply_correction(self, registration_id, courses, *, actor, reason):
        """Replace courses, then write one audit record in the same transaction."""
        registration = (
            Registration.objects.select_for_update()
            .select_related("student__user")
            .get(pk=registration_id)
        )
        student = StudentProfile.objects.select_for_update().get(
            pk=registration.student_id
        )
        course_ids = {course.pk for course in courses}
        selected_courses = list(
            Course.objects.select_for_update()
            .filter(pk__in=course_ids, level=student.level)
            .order_by("code")
        )
        if {course.pk for course in selected_courses} != course_ids:
            raise ValidationError(
                "Course availability changed. Review the corrected course list."
            )

        existing_items = list(
            RegistrationItem.objects.select_for_update()
            .filter(registration=registration)
            .select_related("course")
            .order_by("course__code")
        )
        if {item.course_id for item in existing_items} == course_ids:
            raise ValidationError("The corrected course list is unchanged.")

        before_courses = [
            self.course_snapshot(item.course) for item in existing_items
        ]
        after_courses = [
            self.course_snapshot(course) for course in selected_courses
        ]
        RegistrationItem.objects.filter(registration=registration).delete()
        for course in selected_courses:
            RegistrationItem.objects.create(
                registration=registration,
                course=course,
            )

        corrected_at = timezone.now()
        RegistrationAudit.objects.create(
            actor=actor,
            actor_username=actor.get_username(),
            target_user_id=str(student.user_id),
            target_username=student.user.get_username(),
            target_full_name=student.user.get_full_name()[:150],
            target_profile_id=str(student.pk),
            target_registration_id=str(registration.pk),
            target_level=student.level,
            action=RegistrationAudit.Action.COURSE_CORRECTION,
            reason=reason,
            before_courses=before_courses,
            after_courses=after_courses,
            submitted_at=registration.submitted_at,
        )
        registration.corrected_at = corrected_at
        registration.save(update_fields=("corrected_at",))

    @staticmethod
    def course_snapshot(course):
        return {
            "id": course.pk,
            "code": course.code,
            "title": course.title,
            "level": course.level,
        }

    @admin.display(description="Correction")
    def correction_link(self, obj):
        url = reverse("admin:core_registration_correct", args=(obj.pk,))
        return format_html('<a href="{}">Correct</a>', url)

    @admin.display(description="Student", ordering="student__user__first_name")
    def student_name(self, obj):
        return obj.student.user.get_full_name() or "—"

    @admin.display(description="Username", ordering="student__user__username")
    def student_username(self, obj):
        return obj.student.user.get_username()

    @admin.display(description="Level", ordering="student__level")
    def student_level(self, obj):
        return obj.student.level

    @admin.display(description="Selected courses")
    def selected_courses(self, obj):
        return ", ".join(str(item.course) for item in obj.items.all()) or "—"


@admin.register(RegistrationAudit)
class RegistrationAuditAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "actor_username",
        "target_username",
        "reason",
    )
    list_filter = ("action", "created_at")
    search_fields = ("actor_username", "target_username", "reason")
    fields = (
        "created_at",
        "action",
        "actor",
        "actor_username",
        "target_user_id",
        "target_username",
        "target_full_name",
        "target_profile_id",
        "target_registration_id",
        "target_level",
        "reason",
        "before_courses",
        "after_courses",
        "submitted_at",
    )
    readonly_fields = fields
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
