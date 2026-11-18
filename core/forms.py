"""Student and registration forms with server-side validation."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import Course, StudentLevel, StudentProfile


class StudentSignupForm(UserCreationForm):
    """Accept student-only fields and persist the account/profile atomically."""

    full_name = forms.CharField(max_length=150, label="Full name")
    level = forms.TypedChoiceField(
        choices=StudentLevel.choices,
        coerce=int,
        label="Student level",
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username",)

    def save(self, commit=True):
        """Create the user/profile pair atomically when commit is enabled."""
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["full_name"]

        if commit:
            with transaction.atomic():
                user.save()
                StudentProfile.objects.create(
                    user=user,
                    level=self.cleaned_data["level"],
                )
                self.save_m2m()

        return user


class StudentRegistrationForm(forms.Form):
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Available courses",
        error_messages={
            "invalid_choice": "Select only courses available for your student level.",
            "invalid_pk_value": "Select only courses available for your student level.",
        },
    )

    def __init__(self, *args, level, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["courses"].queryset = Course.objects.filter(level=level)

    def clean_courses(self):
        courses = self.cleaned_data["courses"]
        submitted_ids = self.data.getlist(self.add_prefix("courses"))
        if (
            len(courses) != len(submitted_ids)
            or len({course.pk for course in courses}) != len(courses)
        ):
            raise forms.ValidationError("Select each course only once.")
        return courses


class RegistrationCorrectionForm(forms.Form):
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Corrected courses",
    )
    reason = forms.CharField(
        label="Correction reason",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Record the reason without including passwords or other secrets.",
    )

    def __init__(self, *args, level, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["courses"].queryset = Course.objects.filter(
            level=level
        ).order_by("code")
