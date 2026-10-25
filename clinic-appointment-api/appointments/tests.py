
from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from rest_framework.test  import APIRequestFactory
from  rest_framework import status

from .views import AppointmentCancelView
from .models import (Doctor, DoctorWorkingHours, 
                     Patient, 
                     Appointment)
from .services import (book_appointment,
                       cancel_appointment,
                       reschedule_appointment)


class BookingServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = Doctor.objects.create(
            name="Dr. Amina Hassan",
            speciality="General Practice",
            is_active=True,
        )

        cls.patient = Patient.objects.create(
            full_name="Mary Wanjiku",
            email="mary.test@example.com",
            phone="0712345678",
        )

        # Monday to Friday, 09:00–17:00.
        for weekday in range(5):
            DoctorWorkingHours.objects.create(
                doctor=cls.doctor,
                weekday=weekday,
                starts_time=time(9, 0),
                ends_time=time(17, 0),
            )

    def future_weekday_at(self, hour=10, minute=0):
        """Return an aware datetime on a future weekday."""
        day = timezone.localdate() + timedelta(days=2)

        while day.weekday() >= 5:
            day += timedelta(days=1)

        return timezone.make_aware(
            datetime.combine(day, time(hour, minute)),
            timezone.get_current_timezone(),
        )

    def test_valid_booking_succeeds(self):
        starts_at = self.future_weekday_at()

        appointment = book_appointment(
            doctor_id=self.doctor.id,
            patient_id=self.patient.id,
            starts_at=starts_at,
        )

        self.assertEqual(appointment.doctor, self.doctor)
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(
            appointment.ends_at,
            starts_at + timedelta(minutes=30),
        )
        self.assertEqual(
            appointment.status,
            Appointment.Status.BOOKED,
        )

    def test_duplicate_slot_is_rejected(self):
        starts_at = self.future_weekday_at()

        book_appointment(
            doctor_id=self.doctor.id,
            patient_id=self.patient.id,
            starts_at=starts_at,
        )

        another_patient = Patient.objects.create(
            full_name="John Kamau",
            email="john.test@example.com",
        )

        with self.assertRaises(ValidationError):
            book_appointment(
                doctor_id=self.doctor.id,
                patient_id=another_patient.id,
                starts_at=starts_at,
            )

    def test_booking_outside_working_hours_is_rejected(self):
        starts_at = self.future_weekday_at(hour=17, minute=0)

        with self.assertRaises(ValidationError):
            book_appointment(
                doctor_id=self.doctor.id,
                patient_id=self.patient.id,
                starts_at=starts_at,
            )

    def test_booking_within_one_hour_is_rejected(self):
        starts_at = timezone.now() + timedelta(minutes=30)

        # If this instant falls on a weekend, the one-hour rule still
        # applies; the service should reject it before schedule lookup.
        with self.assertRaises(ValidationError):
            book_appointment(
                doctor_id=self.doctor.id,
                patient_id=self.patient.id,
                starts_at=starts_at,
            )

    def test_inactive_doctor_cannot_be_booked(self):
        self.doctor.is_active = False
        self.doctor.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            book_appointment(
                doctor_id=self.doctor.id,
                patient_id=self.patient.id,
                starts_at=self.future_weekday_at(),

            )



class AppointmentCancellationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = Doctor.objects.create(
            name="Dr. Amina Hassan",
            speciality="General Practice",
            is_active=True,
        )
        cls.patient = Patient.objects.create(
            full_name="Mary Wanjiku",
            email="mary.cancel@example.com",
        )

        for weekday in range(5):
            DoctorWorkingHours.objects.create(
                doctor=cls.doctor,
                weekday=weekday,
                starts_time=time(9, 0),
                ends_time=time(17, 0),
            )

    def create_appointment(self):
        day = timezone.localdate() + timedelta(days=2)

        while day.weekday() >= 5:
            day += timedelta(days=1)

        starts_at = timezone.make_aware(
            datetime.combine(day, time(10, 0)),
            timezone.get_current_timezone(),
        )

        return book_appointment(
            doctor_id=self.doctor.id,
            patient_id=self.patient.id,
            starts_at=starts_at,
        )

    def test_cancellation_saves_reason_and_preserves_record(self):
        appointment = self.create_appointment()

        cancelled = cancel_appointment(
            appointment_id=appointment.id,
            reason="Patient requested cancellation",
        )

        cancelled.refresh_from_db()

        self.assertEqual(
            cancelled.status,
            Appointment.Status.CANCELLED,
        )
        self.assertEqual(
            cancelled.cancellation_reason,
            "Patient requested cancellation",
        )
        self.assertTrue(
            Appointment.objects.filter(pk=appointment.id).exists()
        )

    def test_already_cancelled_appointment_is_rejected(self):
        appointment = self.create_appointment()

        cancel_appointment(
            appointment_id=appointment.id,
            reason="Patient requested cancellation",
        )

        with self.assertRaises(ValidationError):
            cancel_appointment(
                appointment_id=appointment.id,
                reason="Trying to cancel again",
            )

    def test_nonexistent_appointment_is_rejected(self):
        with self.assertRaises(ValidationError):
            cancel_appointment(
                appointment_id=999999,
                reason="Not applicable",
            )

    def test_api_rejects_missing_cancellation_reason(self):
        appointment = self.create_appointment()
        factory = APIRequestFactory()

        request = factory.patch(
            f"/api/appointments/{appointment.id}/cancel/",
            {},
            format="json",
        )
        response = AppointmentCancelView.as_view()(
            request,
            appointment_id=appointment.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        appointment.refresh_from_db()
        self.assertEqual(
            appointment.status,
            Appointment.Status.BOOKED,
        )


class AppointmentReschedulingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = Doctor.objects.create(
            name="Dr. Amina Hassan",
            speciality="General Practice",
            is_active=True,
        )
        cls.patient = Patient.objects.create(
            full_name="Mary Wanjiku",
            email="mary.reschedule@example.com",
        )

        for weekday in range(5):
            DoctorWorkingHours.objects.create(
                doctor=cls.doctor,
                weekday=weekday,
                starts_time=time(9, 0),
                ends_time=time(17, 0),
            )

    def future_weekday_at(self, hour=10, minute=0, days_ahead=2):
        day = timezone.localdate() + timedelta(days=days_ahead)

        while day.weekday() >= 5:
            day += timedelta(days=1)

        return timezone.make_aware(
            datetime.combine(day, time(hour, minute)),
            timezone.get_current_timezone(),
        )

    def create_appointment(self):
        return book_appointment(
            doctor_id=self.doctor.id,
            patient_id=self.patient.id,
            starts_at=self.future_weekday_at(),
        )

    def test_reschedule_succeeds_and_updates_existing_record(self):
        appointment = self.create_appointment()
        original_id = appointment.id
        new_starts_at = self.future_weekday_at(
            hour=11,
            days_ahead=3,
        )

        updated = reschedule_appointment(
            appointment_id=appointment.id,
            new_starts_at=new_starts_at,
        )

        self.assertEqual(updated.id, original_id)
        self.assertEqual(updated.starts_at, new_starts_at)
        self.assertEqual(
            updated.ends_at,
            new_starts_at + timedelta(minutes=30),
        )
        self.assertEqual(
            updated.status,
            Appointment.Status.BOOKED,
        )
        self.assertEqual(Appointment.objects.count(), 1)

    def test_reschedule_to_an_occupied_slot_is_rejected(self):
        first = self.create_appointment()
        occupied_start = self.future_weekday_at(
            hour=11,
            days_ahead=3,
        )

        book_appointment(
            doctor_id=self.doctor.id,
            patient_id=self.patient.id,
            starts_at=occupied_start,
        )

        original_start = first.starts_at

        with self.assertRaises(ValidationError):
            reschedule_appointment(
                appointment_id=first.id,
                new_starts_at=occupied_start,
            )

        first.refresh_from_db()
        self.assertEqual(first.starts_at, original_start)

    def test_cancelled_appointment_cannot_be_rescheduled(self):
        appointment = self.create_appointment()

        cancel_appointment(
            appointment_id=appointment.id,
            reason="Patient requested cancellation",
        )

        with self.assertRaises(ValidationError):
            reschedule_appointment(
                appointment_id=appointment.id,
                new_starts_at=self.future_weekday_at(
                    hour=11,
                    days_ahead=3,
                ),
            )

    def test_nonexistent_appointment_cannot_be_rescheduled(self):
        with self.assertRaises(ValidationError):
            reschedule_appointment(
                appointment_id=999999,
                new_starts_at=self.future_weekday_at(
                    hour=11,
                    days_ahead=3,
                ),
            )
