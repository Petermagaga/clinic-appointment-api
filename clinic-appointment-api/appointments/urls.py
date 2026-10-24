from django.urls import path

from .views import AppointmentCreateView,DoctorAvailabilityView

urlpatterns = [
    path("appointments/",AppointmentCreateView.as_view(),name="appointment-create",),
    path("doctors/<int:doctor_id>/availability/",
         DoctorAvailabilityView.as_view(),
         name="doctor-availability"),
]
