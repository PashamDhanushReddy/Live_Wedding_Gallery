from django.urls import path
from .views import (
    ObservabilityDashboardView,
    ObservabilityMetricsView,
    ObservabilityAlertsView,
    ObservabilityTraceView,
    ObservabilityRetryJobView,
    ObservabilityRetryAllDeadLettersView,
)

app_name = 'observability'

urlpatterns = [
    path('dashboard/', ObservabilityDashboardView.as_view(), name='dashboard'),
    path('metrics/', ObservabilityMetricsView.as_view(), name='metrics'),
    path('alerts/', ObservabilityAlertsView.as_view(), name='alerts'),
    path('trace/', ObservabilityTraceView.as_view(), name='trace'),
    path('jobs/<uuid:job_id>/retry/', ObservabilityRetryJobView.as_view(), name='retry_job'),
    path('jobs/retry-dead-letters/', ObservabilityRetryAllDeadLettersView.as_view(), name='retry_all_dead_letters'),
]

