from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

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


class AdminWorkflowTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_superuser(
            username="admin-test",
            email="admin-test@example.com",
            password=None,
        )
        self.client.force_login(self.admin)
        self.student_user = self.user_model.objects.create_user(
            username="has-submission",
            first_name="Registered Student",
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            level=StudentLevel.LEVEL_100,
        )
        self.course = Course.objects.create(
            code="CS101",
            title="Introduction to Computing",
            level=StudentLevel.LEVEL_100,
        )

    def test_admin_can_create_search_and_filter_courses_without_bulk_actions(self):
        add_url = reverse("admin:core_course_add")
        response = self.client.post(
            add_url,
            {
                "code": "CS102",
                "title": "Computing II",
                "level": str(StudentLevel.LEVEL_100),
                "_save": "Save",
            },
        )

        self.assertRedirects(response, reverse("admin:core_course_changelist"))
        self.assertTrue(Course.objects.filter(code="CS102").exists())

        Course.objects.create(
            code="MATH201",
            title="Mathematics",
            level=StudentLevel.LEVEL_200,
        )
        changelist_url = reverse("admin:core_course_changelist")
        for search_term, expected_codes in (
            ("CS", {"CS101", "CS102"}),
            ("Computing II", {"CS102"}),
        ):
            with self.subTest(search_term=search_term):
                response = self.client.get(
                    changelist_url,
                    {
                        "q": search_term,
                        "level__exact": str(StudentLevel.LEVEL_100),
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    set(response.context["cl"].queryset.values_list("code", flat=True)),
                    expected_codes,
                )
        self.assertNotContains(response, 'name="action"')

    def test_admin_lists_registered_and_unregistered_students_and_searches_them(self):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )
        unregistered_user = self.user_model.objects.create_user(
            username="no-submission",
            first_name="No Registration",
        )
        unregistered_student = StudentProfile.objects.create(
            user=unregistered_user,
            level=StudentLevel.LEVEL_200,
        )

        changelist_url = reverse("admin:core_studentprofile_changelist")
        response = self.client.get(changelist_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registered Student")
        self.assertContains(response, "No Registration")
        self.assertContains(response, "Submitted")
        self.assertContains(response, "Not submitted")
        self.assertContains(response, "CS101")
        self.assertNotContains(response, 'name="action"')

        for search_term, expected_profile in (
            ("has-submission", self.student),
            ("No Registration", unregistered_student),
        ):
            with self.subTest(search_term=search_term):
                response = self.client.get(changelist_url, {"q": search_term})
                self.assertEqual(
                    list(response.context["cl"].queryset),
                    [expected_profile],
                )

    def test_student_level_is_read_only_after_submission_even_on_tampered_post(self):
        Registration.objects.create(student=self.student)
        change_url = reverse(
            "admin:core_studentprofile_change",
            args=(self.student.pk,),
        )

        response = self.client.get(change_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="level"')

        self.client.post(
            change_url,
            {"level": str(StudentLevel.LEVEL_200), "_save": "Save"},
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.level, StudentLevel.LEVEL_100)

    def test_admin_cannot_delete_or_invalidate_a_registered_course(self):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )
        change_url = reverse("admin:core_course_change", args=(self.course.pk,))

        response = self.client.post(
            change_url,
            {
                "code": self.course.code,
                "title": self.course.title,
                "level": str(StudentLevel.LEVEL_200),
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.level, StudentLevel.LEVEL_100)

        delete_url = reverse("admin:core_course_delete", args=(self.course.pk,))
        self.client.post(delete_url, {"post": "yes"})
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())
        self.assertTrue(
            RegistrationItem.objects.filter(
                registration=registration,
                course=self.course,
            ).exists()
        )

    def test_submitted_registration_is_read_only_in_admin(self):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )
        change_url = reverse("admin:core_registration_change", args=(registration.pk,))

        response = self.client.get(change_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CS101")
        self.assertNotContains(response, 'name="_save"')
        self.assertEqual(
            self.client.get(reverse("admin:core_registration_add")).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:core_registration_delete", args=(registration.pk,))
            ).status_code,
            403,
        )

        self.client.post(
            change_url,
            {"submitted_at": "2000-01-01 00:00:00"},
        )
        registration.refresh_from_db()
        self.assertNotEqual(
            registration.submitted_at.strftime("%Y-%m-%d"),
            "2000-01-01",
        )

    def test_staff_model_permissions_allow_review_but_not_ungranted_actions(self):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )
        staff_user = self.user_model.objects.create_user(
            username="course-reviewer",
            is_staff=True,
        )
        view_permissions = Permission.objects.filter(
            content_type__app_label="core",
            codename__in=(
                "view_course",
                "view_studentprofile",
                "view_registration",
            ),
        )
        staff_user.user_permissions.add(*view_permissions)
        self.client.force_login(staff_user)

        self.assertEqual(
            self.client.get(reverse("admin:core_course_changelist")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("admin:core_course_add")).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:core_studentprofile_changelist")
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:core_registration_change", args=(registration.pk,))
            ).status_code,
            200,
        )
