"""Application configuration for the course-registration domain."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Application configuration for the public foundation pages."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
