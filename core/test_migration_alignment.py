"""Tests that keep migration state aligned with the audited model history."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Course,
    Registration,
    RegistrationAudit,
    StudentLevel,
    StudentProfile,
)


class RegistrationAuditModelTests(TestCase):
    def test_migration_fields_persist(self):
        user_model = get_user_model()
        actor = user_model.objects.create_user(username="reviewer")
        student_user = user_model.objects.create_user(username="audit-target")
        student = StudentProfile.objects.create(
            user=student_user,
            level=StudentLevel.LEVEL_100,
        )
        registration = Registration.objects.create(student=student)
        audit = RegistrationAudit.objects.create(
            actor=actor,
            actor_username=actor.username,
            target_user_id=str(student_user.pk),
            target_username=student_user.username,
            target_profile_id=str(student.pk),
            target_registration_id=str(registration.pk),
            target_level=student.level,
            action=RegistrationAudit.Action.COURSE_CORRECTION,
            reason="Documented test correction.",
            before_courses=[{"code": "CS100"}],
            after_courses=[{"code": "CS101"}],
        )

        registration.refresh_from_db()
        audit.refresh_from_db()
        self.assertIsNone(registration.corrected_at)
        self.assertEqual(audit.action, RegistrationAudit.Action.COURSE_CORRECTION)
        self.assertEqual(audit.before_courses, [{"code": "CS100"}])
        self.assertEqual(audit.after_courses, [{"code": "CS101"}])
        self.assertEqual(audit.actor, actor)


class CourseSelectionErrorAccessibilityTests(TestCase):
    def test_empty_selection_error_is_associated_with_checkbox_group(self):
        user = get_user_model().objects.create_user(username="a11y-student")
        StudentProfile.objects.create(user=user, level=StudentLevel.LEVEL_100)
        Course.objects.create(
            code="CS101",
            title="Introduction to Computing",
            level=StudentLevel.LEVEL_100,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("student_dashboard"),
            {"action": "review"},
        )

        self.assertContains(
            response,
            '<fieldset class="course-fieldset" aria-invalid="true" aria-describedby="id_courses_error">',
        )
