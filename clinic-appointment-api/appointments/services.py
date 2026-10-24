from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError,transaction
from django.utils import timezone

from .models import (Appointment,DoctorWorkingHours,Doctor,Patient)

SLOT_DURATION=timedelta(minutes=30)
MINIMUM_BOOKING_NOTICE =timedelta(hours=1)

def validate_appointment_slot(*,doctor,starts_at,ends_at,exclude_appointment_id=None,):
    """
    Validate Whether a 30-minute appointment can be booked.
    Raises Django ValidationError when the slot is invalid or unavailable.
    """

    errors= {}

    if not doctor.is_active:
        
        
            raise ValidationError(
                {"doctor":"This doctor is not currently accepting appointments."}
            )

    if timezone.is_naive(starts_at) or timezone.is_naive(ends_at):
          raise ValidationError({
                "starts_at":"Appointment dates must include a timezone"
          })

    if ends_at-starts_at != SLOT_DURATION:
          errors["ends_at"] = "Appointments must last exactly 30 minutes." 

    local_start=timezone.localtime(starts_at)
    local_end=timezone.localtime(ends_at)

    if local_start.minute %30 !=0 or local_start.second !=0:
          errors["starts_at"]=(
                "Appointment must start on a 30 minute boundary"
          )

    if local_start.microsecond !=0:
          errors["starts_at"]="Appointment start cannot include microseconds."

    if starts_at <=timezone.now():
          errors["starts_at"] ="Appointment must be in the future."

    elif starts_at <timezone.now()+MINIMUM_BOOKING_NOTICE:
          errors["starts_at"]=(
                "Appointments must be booked at least one hour in advance."
          )

    if local_start.date() != local_end.date():
          errors["ends_at"]=(
                "An appointment must start and end on the same local date"
          )

    if errors:
          raise ValidationError(errors)

    schedule=DoctorWorkingHours.objects.filter(
          doctor=doctor,
          weekday=local_start.weekday(),
    ).first()

    if schedule is None:
          raise ValidationError(
                { "starts_at":"This doctor has no working hours on that day."}
          )

          
    if (local_start.time()<schedule.starts_time or local_end.time() > schedule.ends_time):
          raise ValidationError(
                {"starts_at":("the appointment must fail entirely within the doctor's"
                              "working Hours")
                              })


    conflicts= Appointment.objects.filter(
          doctor=doctor,
          status=Appointment.Status.BOOKED,
          starts_at__lt=ends_at,
          ends_at__gt=starts_at,
    )

    if exclude_appointment_id is not None:
          conflicts =conflicts.exclude(pk=exclude_appointment_id)

    if conflicts.exists():
          raise ValidationError({
                "starts_at":"This appointment slot is already booked."
          })
          

def book_appointment(*,doctor_id,patient_id,starts_at):
      """
      validate and create an appointment.

      the doctor row is locked within the transaction on databases that support row-level locking helping serialize
      bookings for that doctor .

      """
      try:
            with transaction.atomic():
                  doctor=Doctor.objects.select_for_update().get(pk=doctor_id)
                  patient=Patient.objects.get(pk=patient_id)
                  ends_at=starts_at+ SLOT_DURATION

                  validate_appointment_slot(
                        doctor=doctor,
                        starts_at=starts_at,
                        ends_at=ends_at,
                  )

                  appointment=Appointment(
                        doctor=doctor,
                        patient=patient,
                        starts_at=starts_at,
                        ends_at=ends_at,
                        status=Appointment.Status.BOOKED,
                  )
                  appointment.full_clean()
                  appointment.save()

                  return appointment
      except Doctor.DoesNotExist:
            raise ValidationError(
                  {"doctor_id":"The selected doctor does not exist."}
            )

      except Patient.DoesNotExist:
            raise ValidationError(
                  {"patient_id":"The selected patient does not exist."}
            )

      except IntegrityError:
            #the Database constraint is the final defense against a 
            #duplicate native appointment with the same doctor and start.
            raise ValidationError({
                  "starts_at":"This appointment slot is no longer available"
            })


def cancel_appointment(*,appointment_id,reason):
      """
      Cancel an existing booked appointment without deleting its record.
      """

      try:
            with transaction.atomic():
                  appointment=(
                        Appointment.objects.select_for_update().get(pk=appointment_id)
                  )

                  if appointment.status == Appointment.Status.CANCELLED:
                        raise ValidationError({
                              "detail":"This appointment has already been cancelled"

                        })
                  appointment.status=Appointment.Status.CANCELLED
                  appointment.cancellation_reason= reason.strip()
                  appointment.full_clean()
                  appointment.save(
                        update_fields=[
                              "status",
                              "cancellation_reason",
                              "updated_at",
                        ]
                  )
                  return appointment

      except Appointment.DoesNotExist:
            raise ValidationError(
                  {"appointment_id":"The selected appointment does not exist."}
            )    