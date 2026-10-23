from django.contrib import admin
from .models import (Appointment,Doctor,Patient,DoctorWorkingHours)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display=('name','speciality','is_active')
    search_fields=('name','speciality')
    list_filter=('is_active',)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display=("full_name","email","phone")
    search_fields=("full_name","email")

admin.register(DoctorWorkingHours)
class DoctorWorkingHoursAdmin(admin.ModelAdmin):
    list_display=(
        "doctor","weekday","starts_time","ends_time"
    )
    list_filter=("weekday","doctor")

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display =("doctor","patient","starts_at","ends_at","status")
    list_filter=("status","doctor")
    search_fields=("doctor_name","patient__full_name")
    readonly_fields=("created_at","updated_at")