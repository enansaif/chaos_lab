from django.urls import path

from apps.orders.views import (
    OrderAsyncCreateView,
    OrderCreateView,
    OrderDetailView,
    TaskStatusView,
)

urlpatterns = [
    path("", OrderCreateView.as_view(), name="order-create"),
    path("async/", OrderAsyncCreateView.as_view(), name="order-async-create"),
    path("tasks/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
    path("<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
]
