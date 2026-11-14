from django.contrib import admin

from .models import Course, Registration, StudentProfile


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

    def has_delete_permission(self, request, obj=None):
        return False

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
