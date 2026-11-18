"""Top-level URL routes for public pages, authentication, student, and admin views."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from core import views


# Keep the public landing page and Django admin separate.
urlpatterns = [
    path('healthz/', views.health, name='health'),
    path('admin/', admin.site.urls),
    path('accounts/signup/', views.signup, name='signup'),
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(
            template_name='core/login.html',
            next_page='student_dashboard',
        ),
        name='login',
    ),
    path(
        'accounts/logout/',
        auth_views.LogoutView.as_view(),
        name='logout',
    ),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('', views.home, name='home'),
]
