from django.urls import path

from .views import (AppointmentCreateView,DoctorAvailabilityView,AppointmentCancelView)

urlpatterns = [
    path("appointments/",
         AppointmentCreateView.as_view(),
         name="appointment-create",),
    path("doctors/<int:doctor_id>/availability/",
         DoctorAvailabilityView.as_view(),
         name="doctor-availability"),
    path("appointments/<int:appointment_id>/cancel/",
         AppointmentCancelView.as_view(),
         name="appointment-cancel",),
]
