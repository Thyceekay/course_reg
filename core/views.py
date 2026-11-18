"""Public, authentication, and student-registration HTTP views."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import StudentRegistrationForm, StudentSignupForm
from .models import Course, Registration, RegistrationItem, StudentProfile


def home(request):
    """Render the public starter page."""
    return render(request, "core/home.html")


def health(request):
    """Report application and database readiness without exposing details."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


def signup(request):
    """Create a student account and its profile in one transaction."""
    if request.user.is_authenticated:
        return redirect("home")

    form = StudentSignupForm(
        request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("student_dashboard")

    return render(request, "core/signup.html", {"form": form})


@login_required
def student_dashboard(request):
    """Show the student's courses or their immutable final registration."""
    try:
        student = StudentProfile.objects.select_related("user").get(
            user=request.user
        )
    except StudentProfile.DoesNotExist:
        raise PermissionDenied("A student profile is required to view this page.")

    registration = (
        Registration.objects.filter(student=student)
        .prefetch_related("items__course")
        .first()
    )
    if registration:
        if request.method == "POST":
            messages.info(request, "Your registration has already been submitted.")
            return redirect("student_dashboard")
        return render(
            request,
            "core/student_dashboard.html",
            {"student": student, "registration": registration},
        )

    courses = Course.objects.filter(level=student.level)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            with transaction.atomic():
                student = StudentProfile.objects.select_for_update().get(
                    user=request.user
                )
                courses = Course.objects.filter(level=student.level)
                if Registration.objects.filter(student=student).exists():
                    messages.info(
                        request,
                        "Your registration has already been submitted.",
                    )
                    return redirect("student_dashboard")

                form = StudentRegistrationForm(request.POST, level=student.level)
                if not form.is_valid():
                    return render(
                        request,
                        "core/student_dashboard.html",
                        {"student": student, "courses": courses, "form": form},
                    )

                selected_courses = form.cleaned_data["courses"]
                if action == "review":
                    return render(
                        request,
                        "core/student_dashboard.html",
                        {
                            "student": student,
                            "courses": courses,
                            "form": form,
                            "review_courses": selected_courses,
                        },
                    )
                if action == "edit":
                    return render(
                        request,
                        "core/student_dashboard.html",
                        {"student": student, "courses": courses, "form": form},
                    )
                if action != "finalize":
                    form.add_error(
                        None,
                        "Review your course choices before submitting.",
                    )
                    return render(
                        request,
                        "core/student_dashboard.html",
                        {"student": student, "courses": courses, "form": form},
                    )

                selected_ids = {course.pk for course in selected_courses}
                eligible_courses = list(
                    Course.objects.select_for_update()
                    .filter(pk__in=selected_ids, level=student.level)
                    .order_by("code")
                )
                if {course.pk for course in eligible_courses} != selected_ids:
                    form.add_error(
                        "courses",
                        "Course availability changed. Review your choices and try again.",
                    )
                    return render(
                        request,
                        "core/student_dashboard.html",
                        {"student": student, "courses": courses, "form": form},
                    )

                registration = Registration.objects.create(student=student)
                for course in eligible_courses:
                    RegistrationItem.objects.create(
                        registration=registration,
                        course=course,
                    )
        except IntegrityError:
            if Registration.objects.filter(student__user=request.user).exists():
                messages.info(request, "Your registration has already been submitted.")
            else:
                messages.error(
                    request,
                    "Your registration could not be saved. Please review your choices and try again.",
                )
            return redirect("student_dashboard")

        messages.success(request, "Your registration was submitted successfully.")
        return redirect("student_dashboard")

    form = StudentRegistrationForm(level=student.level)
    return render(
        request,
        "core/student_dashboard.html",
        {"student": student, "courses": courses, "form": form},
    )
