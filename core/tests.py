from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from .models import Course, Registration, RegistrationItem, StudentLevel, StudentProfile


class HomepageTests(TestCase):
    """Verify that the starter page is available to visitors."""

    def test_homepage_renders(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")


class RegistrationModelTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.student_user = user_model.objects.create_user(
            username="student",
            password="test-password",
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            level=StudentLevel.LEVEL_100,
        )
        self.course = Course.objects.create(
            code=" CS101 ",
            title="Introduction to Computing",
            level=StudentLevel.LEVEL_100,
        )

    def test_related_models_persist_with_expected_relationships(self):
        registration = Registration.objects.create(student=self.student)
        item = RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )

        self.assertEqual(self.student.registration, registration)
        self.assertEqual(registration.items.get(), item)
        self.assertEqual(item.course, self.course)
        self.assertIsNotNone(registration.submitted_at)
        self.assertEqual(
            Course.objects.get(pk=self.course.pk).code,
            "CS101",
        )

    def test_duplicate_course_code_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Course.objects.create(
                    code="cs101",
                    title="Duplicate code",
                    level=StudentLevel.LEVEL_100,
                )

    def test_student_profile_is_one_to_one_with_user(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentProfile.objects.create(
                    user=self.student_user,
                    level=StudentLevel.LEVEL_100,
                )

    def test_course_level_must_be_supported_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Course.objects.create(
                    code="INVALID",
                    title="Unsupported level",
                    level=250,
                )

    def test_student_level_must_be_supported_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentProfile.objects.create(
                    user=get_user_model().objects.create_user(username="other"),
                    level=250,
                )

    def test_student_can_have_only_one_registration(self):
        Registration.objects.create(student=self.student)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Registration.objects.create(student=self.student)

    def test_course_can_appear_only_once_per_registration(self):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RegistrationItem.objects.create(
                    registration=registration,
                    course=self.course,
                )

    def test_registered_course_cannot_be_deleted(self):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )

        with self.assertRaises(ProtectedError):
            self.course.delete()

        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())

    def test_registered_course_level_cannot_change_to_mismatch_student(self):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )
        self.course.level = StudentLevel.LEVEL_200

        with self.assertRaises(ValidationError):
            self.course.save()

        self.course.refresh_from_db()
        self.assertEqual(self.course.level, StudentLevel.LEVEL_100)

    def test_registration_item_rejects_course_at_another_level(self):
        registration = Registration.objects.create(student=self.student)
        other_level_course = Course.objects.create(
            code="MATH201",
            title="Mathematics",
            level=StudentLevel.LEVEL_200,
        )

        with self.assertRaises(ValidationError):
            RegistrationItem.objects.create(
                registration=registration,
                course=other_level_course,
            )

        self.assertFalse(
            RegistrationItem.objects.filter(
                registration=registration,
                course=other_level_course,
            ).exists()
        )

    def test_student_level_cannot_change_after_registration(self):
        Registration.objects.create(student=self.student)
        self.student.level = StudentLevel.LEVEL_200

        with self.assertRaises(ValidationError):
            self.student.save()

        self.student.refresh_from_db()
        self.assertEqual(self.student.level, StudentLevel.LEVEL_100)
