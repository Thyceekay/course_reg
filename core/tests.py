"""Django test suite for models, authentication, registration, and admin workflows."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import (
    IntegrityError,
    OperationalError,
    connection,
    connections,
    transaction,
)
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from .models import (
    Course,
    Registration,
    RegistrationAudit,
    RegistrationItem,
    StudentLevel,
    StudentProfile,
)


class HomepageTests(TestCase):
    """Verify that the starter page is available to visitors."""

    def test_homepage_renders(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")


class HealthEndpointTests(TestCase):
    def test_health_endpoint_reports_readiness(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @patch(
        "core.views.connection.cursor",
        side_effect=OperationalError("private database details"),
    )
    def test_health_endpoint_hides_database_errors(self, _mock_cursor):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn(b"private database details", response.content)


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

    def test_registered_student_user_cannot_be_deleted_with_registration_history(self):
        registration = Registration.objects.create(student=self.student)
        item = RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )

        with self.assertRaises(ProtectedError):
            self.student_user.delete()

        self.assertTrue(
            self.student_user.__class__.objects.filter(
                pk=self.student_user.pk
            ).exists()
        )
        self.assertTrue(Registration.objects.filter(pk=registration.pk).exists())
        self.assertTrue(RegistrationItem.objects.filter(pk=item.pk).exists())

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


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.signup_url = reverse("signup")
        self.login_url = reverse("login")
        self.dashboard_url = reverse("student_dashboard")

    def signup_data(self, **overrides):
        data = {
            "username": "new-student",
            "full_name": "Avery Student",
            "level": str(StudentLevel.LEVEL_200),
            "password1": "Strong-unique-passphrase-42!",
            "password2": "Strong-unique-passphrase-42!",
        }
        data.update(overrides)
        return data

    def create_student(self, username, full_name, level=StudentLevel.LEVEL_100):
        user = self.user_model.objects.create_user(
            username=username,
            password="Strong-unique-passphrase-42!",
            first_name=full_name,
        )
        StudentProfile.objects.create(user=user, level=level)
        return user

    def test_signup_creates_profile_hashes_password_and_signs_student_in(self):
        response = self.client.post(self.signup_url, self.signup_data(), follow=True)

        user = self.user_model.objects.get(username="new-student")
        profile = StudentProfile.objects.get(user=user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(profile.level, StudentLevel.LEVEL_200)
        self.assertEqual(user.get_full_name(), "Avery Student")
        self.assertTrue(user.check_password("Strong-unique-passphrase-42!"))
        self.assertTrue(response.context["user"].is_authenticated)
        self.assertContains(response, "Avery Student")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_signup_rejects_mismatched_password_and_invalid_level(self):
        response = self.client.post(
            self.signup_url,
            self.signup_data(password2="Different-strong-passphrase-43!"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password fields", status_code=200)
        self.assertContains(response, 'aria-describedby="id_password2_helptext id_password2_error"')
        self.assertFalse(self.user_model.objects.filter(username="new-student").exists())

        response = self.client.post(self.signup_url, self.signup_data(level="250"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice", status_code=200)
        self.assertFalse(self.user_model.objects.filter(username="new-student").exists())

    def test_signup_rejects_weak_password(self):
        response = self.client.post(
            self.signup_url,
            self.signup_data(
                password1="password",
                password2="password",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password", status_code=200)
        self.assertFalse(self.user_model.objects.filter(username="new-student").exists())

    def test_empty_signup_shows_required_field_errors(self):
        response = self.client.post(self.signup_url, {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.", status_code=200)
        self.assertFalse(self.user_model.objects.exists())

    def test_signup_rejects_duplicate_username(self):
        self.user_model.objects.create_user(
            username="new-student",
            password="Existing-strong-passphrase-44!",
        )

        response = self.client.post(self.signup_url, self.signup_data())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists", status_code=200)
        self.assertEqual(self.user_model.objects.filter(username="new-student").count(), 1)

    def test_signup_ignores_submitted_privileged_fields(self):
        response = self.client.post(
            self.signup_url,
            self.signup_data(
                is_staff="true",
                is_superuser="true",
                is_active="false",
                groups="1",
                user_permissions="1",
            ),
        )

        user = self.user_model.objects.get(username="new-student")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.groups.exists())
        self.assertFalse(user.user_permissions.exists())

    def test_valid_credentials_log_student_in(self):
        user = self.create_student("login-student", "Login Student")

        response = self.client.post(
            self.login_url,
            {
                "username": user.username,
                "password": "Strong-unique-passphrase-42!",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)
        self.assertContains(response, "Login Student")

    def test_incorrect_password_does_not_authenticate(self):
        self.create_student("login-student", "Login Student")

        response = self.client.post(
            self.login_url,
            {"username": "login-student", "password": "incorrect-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "incorrect", status_code=200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_admin_login_accepts_staff_credentials_and_rejects_invalid_password(self):
        admin = self.user_model.objects.create_superuser(
            username="secure-admin",
            email="secure-admin@example.com",
            password="Admin-unique-passphrase-47!",
        )
        admin_login_url = reverse("admin:login")
        valid_client = Client(enforce_csrf_checks=True)
        self.assertEqual(valid_client.get(admin_login_url).status_code, 200)
        token = valid_client.cookies["csrftoken"].value
        data = {"username": admin.username, "password": "Admin-unique-passphrase-47!"}
        rejected = valid_client.post(admin_login_url, data)
        self.assertEqual(rejected.status_code, 403)

        response = valid_client.post(
            admin_login_url,
            data,
            HTTP_X_CSRFTOKEN=token,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_staff)
        self.assertTrue(response.wsgi_request.user.is_superuser)

        invalid_client = Client(enforce_csrf_checks=True)
        self.assertEqual(invalid_client.get(admin_login_url).status_code, 200)
        invalid_token = invalid_client.cookies["csrftoken"].value
        response = invalid_client.post(
            admin_login_url,
            {"username": admin.username, "password": "incorrect-password"},
            HTTP_X_CSRFTOKEN=invalid_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter the correct username and password")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_anonymous_user_is_redirected_from_student_page(self):
        response = self.client.get(self.dashboard_url)

        self.assertRedirects(
            response,
            f"{self.login_url}?next={self.dashboard_url}",
        )

    def test_student_cannot_access_django_admin(self):
        user = self.create_student("regular-student", "Regular Student")
        self.client.force_login(user)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_dashboard_never_exposes_another_students_profile(self):
        current_student = self.create_student("current", "Current Student")
        self.create_student("other", "Other Student", StudentLevel.LEVEL_300)
        self.client.force_login(current_student)

        response = self.client.get(self.dashboard_url, {"student_id": 2})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current Student")
        self.assertNotContains(response, "Other Student")

    def test_logout_requires_post_and_ends_the_session(self):
        user = self.create_student("logout-student", "Logout Student")
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(user)

        self.assertEqual(csrf_client.get(reverse("logout")).status_code, 405)
        csrf_client.get(reverse("home"))
        csrf_token = csrf_client.cookies["csrftoken"].value
        self.assertEqual(csrf_client.post(reverse("logout")).status_code, 403)
        response = csrf_client.post(
            reverse("logout"),
            HTTP_X_CSRFTOKEN=csrf_token,
            follow=True,
        )

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(response.context["user"].is_authenticated)
        self.assertRedirects(
            csrf_client.get(self.dashboard_url),
            f"{self.login_url}?next={self.dashboard_url}",
        )

    def test_authentication_forms_enforce_csrf_tokens(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.get(self.signup_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrfmiddlewaretoken", response.content.decode())

        rejected = csrf_client.post(self.signup_url, self.signup_data())
        self.assertEqual(rejected.status_code, 403)

        token = csrf_client.cookies["csrftoken"].value
        accepted = csrf_client.post(
            self.signup_url,
            self.signup_data(),
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(accepted.status_code, 302)

        login_client = Client(enforce_csrf_checks=True)
        login_page = login_client.get(self.login_url)
        self.assertEqual(login_page.status_code, 200)
        self.assertIn("csrfmiddlewaretoken", login_page.content.decode())
        rejected_login = login_client.post(
            self.login_url,
            {"username": "new-student", "password": "Strong-unique-passphrase-42!"},
        )
        self.assertEqual(rejected_login.status_code, 403)


class StudentRegistrationFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="registration-student",
            password="Strong-unique-passphrase-42!",
            first_name="Registration Student",
        )
        self.student = StudentProfile.objects.create(
            user=self.user,
            level=StudentLevel.LEVEL_100,
        )
        self.course = Course.objects.create(
            code="CS101",
            title="Introduction to Computing",
            level=StudentLevel.LEVEL_100,
        )
        self.second_course = Course.objects.create(
            code="CS102",
            title="Computing II",
            level=StudentLevel.LEVEL_100,
        )
        self.other_level_course = Course.objects.create(
            code="MATH201",
            title="Mathematics II",
            level=StudentLevel.LEVEL_200,
        )
        self.dashboard_url = reverse("student_dashboard")
        self.client.force_login(self.user)

    def registration_data(self, action, *course_ids):
        return {"action": action, "courses": [str(course_id) for course_id in course_ids]}

    def test_dashboard_lists_only_student_level_courses_with_labelled_checkboxes(self):
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CS101 - Introduction to Computing")
        self.assertNotContains(response, "MATH201")
        self.assertContains(response, '<input type="checkbox" name="courses"')
        self.assertContains(response, '<label for="id_courses_0">')
        self.assertContains(response, "Select at least one course")

    def test_student_sees_informative_empty_state_when_no_courses_are_available(self):
        self.student.level = StudentLevel.LEVEL_300
        self.student.save()

        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "No courses are currently available for your level.")
        self.assertNotContains(response, 'name="courses"')

    def test_valid_submission_is_reviewed_saved_once_and_survives_relogin(self):
        review = self.client.post(
            self.dashboard_url,
            self.registration_data("review", self.course.pk, self.second_course.pk),
        )
        self.assertEqual(review.status_code, 200)
        self.assertContains(review, "Review your course choices")
        self.assertContains(review, "Your submission is final.")
        self.assertContains(review, "CS101")
        self.assertContains(review, "CS102")
        self.assertFalse(Registration.objects.filter(student=self.student).exists())

        response = self.client.post(
            self.dashboard_url,
            self.registration_data(
                "finalize", self.course.pk, self.second_course.pk
            ),
        )
        self.assertRedirects(response, self.dashboard_url)
        registration = Registration.objects.get(student=self.student)
        self.assertEqual(
            list(registration.items.values_list("course_id", flat=True)),
            [self.course.pk, self.second_course.pk],
        )
        self.assertIsNotNone(registration.submitted_at)

        saved_page = self.client.get(self.dashboard_url)
        self.assertEqual(saved_page.context["registration"], registration)
        self.assertContains(saved_page, "Your submitted registration")
        self.assertContains(saved_page, "CS101")
        self.assertContains(saved_page, "Submitted on")
        self.assertContains(saved_page, "You cannot edit your registered courses.")
        self.assertNotContains(saved_page, 'name="courses"')

        repeated = self.client.post(
            self.dashboard_url,
            self.registration_data("finalize", self.other_level_course.pk),
        )
        self.assertRedirects(repeated, self.dashboard_url)
        self.assertEqual(Registration.objects.filter(student=self.student).count(), 1)
        self.assertEqual(registration.items.count(), 2)

        self.client.post(reverse("logout"))
        self.client.post(
            reverse("login"),
            {
                "username": self.user.username,
                "password": "Strong-unique-passphrase-42!",
            },
        )
        returned_page = self.client.get(self.dashboard_url)
        self.assertContains(returned_page, "CS101")
        self.assertContains(returned_page, "Your submitted registration")

    def test_empty_selection_is_rejected(self):
        response = self.client.post(self.dashboard_url, {"action": "review"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertFalse(Registration.objects.filter(student=self.student).exists())

    def test_nonexistent_malformed_and_wrong_level_ids_are_rejected(self):
        invalid_submissions = (
            ("nonexistent", "999999"),
            ("malformed", "not-a-course-id"),
            ("wrong level", str(self.other_level_course.pk)),
        )
        for description, course_id in invalid_submissions:
            with self.subTest(description=description):
                response = self.client.post(
                    self.dashboard_url,
                    self.registration_data("review", course_id),
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    "Select only courses available for your student level.",
                )
                self.assertFalse(
                    Registration.objects.filter(student=self.student).exists()
                )

    def test_duplicate_course_ids_are_rejected(self):
        response = self.client.post(
            self.dashboard_url,
            self.registration_data("review", self.course.pk, self.course.pk),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select each course only once.")
        self.assertFalse(Registration.objects.filter(student=self.student).exists())

    def test_registration_and_items_roll_back_together_on_database_failure(self):
        create_item = RegistrationItem.objects.create

        def create_then_fail(*args, **kwargs):
            if kwargs["course"].pk == self.second_course.pk:
                raise IntegrityError("database detail must not be shown")
            return create_item(*args, **kwargs)

        with patch(
            "core.views.RegistrationItem.objects.create",
            side_effect=create_then_fail,
        ):
            response = self.client.post(
                self.dashboard_url,
                self.registration_data(
                    "finalize", self.course.pk, self.second_course.pk
                ),
                follow=True,
            )

        self.assertContains(
            response,
            "Your registration could not be saved. Please review your choices and try again.",
        )
        self.assertNotContains(response, "database detail")
        self.assertFalse(Registration.objects.filter(student=self.student).exists())
        self.assertFalse(RegistrationItem.objects.exists())

    def test_registration_submission_enforces_csrf_tokens(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", csrf_client.cookies)

        data = self.registration_data("finalize", self.course.pk)
        rejected = csrf_client.post(self.dashboard_url, data)
        self.assertEqual(rejected.status_code, 403)
        self.assertFalse(Registration.objects.filter(student=self.student).exists())

        token = csrf_client.cookies["csrftoken"].value
        accepted = csrf_client.post(
            self.dashboard_url,
            data,
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertRedirects(accepted, self.dashboard_url)
        self.assertTrue(Registration.objects.filter(student=self.student).exists())

    def test_student_cannot_view_another_students_registration(self):
        other_user = get_user_model().objects.create_user(
            username="another-student",
            first_name="Another Student",
        )
        other_student = StudentProfile.objects.create(
            user=other_user,
            level=StudentLevel.LEVEL_200,
        )
        registration = Registration.objects.create(student=other_student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.other_level_course,
        )

        response = self.client.get(
            self.dashboard_url,
            {"student_id": other_student.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Another Student")
        self.assertNotContains(response, "MATH201")
        self.assertNotContains(response, "Your submitted registration")


@skipUnless(
    connection.vendor == "postgresql",
    "Concurrent submission locking must be verified with PostgreSQL.",
)
class PostgreSQLConcurrentRegistrationTests(TransactionTestCase):
    reset_sequences = True

    def test_concurrent_submissions_create_one_registration_and_item(self):
        user = get_user_model().objects.create_user(
            username="concurrent-student",
            password="Strong-unique-passphrase-42!",
        )
        student = StudentProfile.objects.create(
            user=user,
            level=StudentLevel.LEVEL_100,
        )
        course = Course.objects.create(
            code="CS101",
            title="Introduction to Computing",
            level=StudentLevel.LEVEL_100,
        )
        barrier = Barrier(2)
        data = {"action": "finalize", "courses": str(course.pk)}

        def submit_registration():
            try:
                connections.close_all()
                client = Client()
                client.force_login(user)
                barrier.wait(timeout=10)
                return client.post(reverse("student_dashboard"), data).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: submit_registration(), range(2)))

        self.assertEqual(responses, [302, 302])
        registration = Registration.objects.get(student=student)
        self.assertEqual(registration.items.count(), 1)


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

    def test_admin_course_creation_enforces_csrf_tokens(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        add_url = reverse("admin:core_course_add")
        response = csrf_client.get(add_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", csrf_client.cookies)

        data = {
            "code": "CS102",
            "title": "Computing II",
            "level": str(StudentLevel.LEVEL_100),
            "_save": "Save",
        }
        rejected = csrf_client.post(add_url, data)
        self.assertEqual(rejected.status_code, 403)
        self.assertFalse(Course.objects.filter(code="CS102").exists())

        token = csrf_client.cookies["csrftoken"].value
        accepted = csrf_client.post(add_url, data, HTTP_X_CSRFTOKEN=token)

        self.assertRedirects(accepted, reverse("admin:core_course_changelist"))
        self.assertTrue(Course.objects.filter(code="CS102").exists())

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

    def test_admin_correction_preserves_submission_and_audits_course_changes(self):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )
        original_submitted_at = registration.submitted_at
        corrected_course = Course.objects.create(
            code="CS102",
            title="Computing II",
            level=StudentLevel.LEVEL_100,
        )
        url = reverse(
            "admin:core_registration_correct",
            args=(registration.pk,),
        )

        form_page = self.client.get(url)
        self.assertEqual(form_page.status_code, 200)
        self.assertContains(form_page, "Original submission")
        self.assertContains(form_page, "CS101")

        response = self.client.post(
            url,
            {
                "courses": [str(corrected_course.pk)],
                "reason": "The original course was entered in error.",
            },
        )

        self.assertRedirects(response, reverse("admin:core_registration_changelist"))
        registration.refresh_from_db()
        self.assertEqual(registration.submitted_at, original_submitted_at)
        self.assertIsNotNone(registration.corrected_at)
        self.assertEqual(
            list(
                registration.items.values_list("course__code", flat=True)
            ),
            ["CS102"],
        )

        audit = RegistrationAudit.objects.get(
            target_registration_id=str(registration.pk)
        )
        self.assertEqual(audit.actor, self.admin)
        self.assertEqual(audit.action, RegistrationAudit.Action.COURSE_CORRECTION)
        self.assertEqual(audit.reason, "The original course was entered in error.")
        self.assertEqual(audit.submitted_at, original_submitted_at)
        self.assertEqual(
            audit.before_courses,
            [
                {
                    "id": self.course.pk,
                    "code": "CS101",
                    "title": "Introduction to Computing",
                    "level": StudentLevel.LEVEL_100,
                }
            ],
        )
        self.assertEqual(
            audit.after_courses,
            [
                {
                    "id": corrected_course.pk,
                    "code": "CS102",
                    "title": "Computing II",
                    "level": StudentLevel.LEVEL_100,
                }
            ],
        )

    def test_admin_correction_requires_courses_at_the_students_level(self):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )
        wrong_level_course = Course.objects.create(
            code="MATH201",
            title="Mathematics",
            level=StudentLevel.LEVEL_200,
        )
        url = reverse(
            "admin:core_registration_correct",
            args=(registration.pk,),
        )

        invalid_submissions = (
            ([], "Attempted invalid correction."),
            ([str(wrong_level_course.pk)], "Attempted invalid correction."),
            ([str(self.course.pk)], ""),
        )
        for selected_courses, reason in invalid_submissions:
            with self.subTest(selected_courses=selected_courses, reason=reason):
                response = self.client.post(
                    url,
                    {
                        "courses": selected_courses,
                        "reason": reason,
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    list(
                        registration.items.values_list(
                            "course__code", flat=True
                        )
                    ),
                    ["CS101"],
                )
                self.assertFalse(RegistrationAudit.objects.exists())

    @patch("core.admin.RegistrationAudit.objects.create")
    def test_admin_correction_failure_rolls_back_items_and_audit(
        self, create_audit
    ):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )
        corrected_course = Course.objects.create(
            code="CS102",
            title="Computing II",
            level=StudentLevel.LEVEL_100,
        )
        create_audit.side_effect = RuntimeError("simulated audit failure")
        url = reverse(
            "admin:core_registration_correct",
            args=(registration.pk,),
        )

        with self.assertLogs("django.request", level="ERROR"):
            with self.assertRaisesRegex(RuntimeError, "simulated audit failure"):
                self.client.post(
                    url,
                    {
                        "courses": [str(corrected_course.pk)],
                        "reason": "The original course was entered in error.",
                    },
                )

        registration.refresh_from_db()
        self.assertIsNone(registration.corrected_at)
        self.assertEqual(
            list(registration.items.values_list("course__code", flat=True)),
            ["CS101"],
        )
        self.assertFalse(RegistrationAudit.objects.exists())

    def test_registered_student_deletion_is_blocked_in_admin(self):
        registration = Registration.objects.create(student=self.student)
        item = RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )
        delete_url = reverse("admin:auth_user_delete", args=(self.student_user.pk,))

        self.assertEqual(self.client.get(delete_url).status_code, 200)
        self.client.post(delete_url, {"post": "yes"})

        self.assertTrue(self.user_model.objects.filter(pk=self.student_user.pk).exists())
        self.assertTrue(Registration.objects.filter(pk=registration.pk).exists())
        self.assertTrue(RegistrationItem.objects.filter(pk=item.pk).exists())

    def test_registration_change_permission_is_limited_to_correction_workflow(self):
        registration = Registration.objects.create(student=self.student)
        RegistrationItem.objects.create(
            registration=registration,
            course=self.course,
        )
        correction_staff = self.user_model.objects.create_user(
            username="registration-corrector",
            is_staff=True,
        )
        correction_permission = Permission.objects.get(
            content_type__app_label="core",
            codename="change_registration",
        )
        correction_staff.user_permissions.add(correction_permission)
        self.client.force_login(correction_staff)

        list_url = reverse("admin:core_registration_changelist")
        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Correct")

        change_url = reverse(
            "admin:core_registration_change",
            args=(registration.pk,),
        )
        change_response = self.client.get(change_url)
        self.assertEqual(change_response.status_code, 200)
        self.assertNotContains(change_response, 'name="_save"')

        correction_url = reverse(
            "admin:core_registration_correct",
            args=(registration.pk,),
        )
        self.assertEqual(self.client.get(correction_url).status_code, 200)

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
        self.assertEqual(
            self.client.get(
                reverse("admin:core_registration_correct", args=(registration.pk,))
            ).status_code,
            403,
        )
