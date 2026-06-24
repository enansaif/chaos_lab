from django.urls import path

from apps.core.views_health import live, ready

urlpatterns = [
    path("live/", live, name="health-live"),
    path("ready/", ready, name="health-ready"),
]
