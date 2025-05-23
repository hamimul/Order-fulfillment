from django.urls import path
from . import views

urlpatterns = [
    path('', views.health_check, name='health-check'),
    path('metrics/', views.system_metrics, name='system-metrics'),
]