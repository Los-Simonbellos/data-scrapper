from django.urls import path

from pacientes import views

urlpatterns = [
    path("", views.health, name="health"),
    path("api/patients", views.patients_json, name="patients-json"),
]
