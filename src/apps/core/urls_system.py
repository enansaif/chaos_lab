from django.urls import path

from apps.core.views_system import SystemConfigView

urlpatterns = [
    path("config/", SystemConfigView.as_view(), name="system-config"),
]
