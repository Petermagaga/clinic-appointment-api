from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F,Q


class Doctor(models.Model):
    name=models.CharField(max_length=100)
    speciality=models.CharField(max_length=200,blank=True)
    is_active=models.BooleanField(default=True)

    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=["name"]

    def __str__(self):
        return self.name


class Patient(models.Model):
    full_name=models.CharField(max_length=100)
    email=models.EmailField()
    phone=models.CharField(max_length=15,blank=True)

    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=["full_name"]
    def __str__(self):
        return self.full_name

class DoctorWorkingHours(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY=0,"Monday"
        TUESDAY=1,"Tuesday"
        WEDNESDAY=2,"Wednesday"
        THURSDAY=3,"Thursday"
        FRIDAY=4,"Friday"
        SATURDAY=5,"Saturday"
        SUNDAY=6,"Sunday"

    doctor=models.ForeignKey(Doctor,on_delete=models.CASCADE,related_name="working_hours",)
    weekday=models.IntegerField(choices=Weekday.choices)
    start_time=models.TimeField()
    end_time=models.TimeField()

    class Meta:
        ordering=["weekday","start_time"]
        constraints=[
            models.UniqueConstraint(
                fields=["doctor","weekday"],
                name="unique_doctor_working_day",
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="working_hours_end_after_start",
            ),

        ]

    def clean(self):
        super().clean()

        if (self.start_time is not None and self.end_time is not None and self.end_time<=self.start_time):

            raise ValidationError(
                {
                    "end_time":"End time must be later thaan start time."
                }
            )

    def __str__(self):
        return (f"{self.doctor.name} - {self.get_weekday_dispaly()}",
                f"({self.start_time} to {self.end_time})")
    

class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED="booked","Booked"
        CANCELLED="cancelled","Cancelled"

    SLOT_DURATION=timedelta(minutes=30)
    doctor=models.ForeignKey(Doctor,on_delete=models.PROTECT,related_name="appontments",)
    patient=models.ForeignKey(Patient,on_delete=models.PROTECT,related_name="appointments")
    starts_at=models.DateTimeField()
    ends_at=models.DateTimeField()

    status=models.CharField(max_length=20,choices=Status.choices,default=Status.BOOKED,)
    cancellation_reason=models.TextField(blank=True)

    created_at=models.DateTimeField(auto_now_add=True)
    updated_at =models.DateTimeField(auto_now=True)

    class Meta:
        ordering=["starts_at"]
        constraints=[
            models.CheckConstraint(condition=Q(ends_at__gt=F("starts_at")),
                                   name="appointment_end_after_start",
                                ),
            models.UniqueConstraint(
                fields=["doctor","starts_at"],
                condition=Q(status="booked"),
                name="unique_active_doctor_slot",
            ),
        ]

    def clean(self):
        super().clean()
        errors={}

        if self.starts_at and self.ends_at:
            if self.ends_at <=self.starts_at:

                errors["ends_at"]=(
                    "Appointment end must be later than its start"
                )
            elif self.ends_at -self.starts_at !=self.SLOT_DURATION:
                errors["ends_at"]=(
                    "Appointments must last exactly 30 minutes."
                )        
        if (self.starts_at and self.starts_at.minute%30 !=0):
            errors["starts_at"] =(
                "Appointment must start on a 30 minute boundary"
            )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.patient.full_name} with {self.doctor.name}"
            f"at {self.starts_at}"
        )





    