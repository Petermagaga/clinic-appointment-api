
from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Doctor, DoctorWorkingHours, Patient, Appointment
from .services import book_appointment


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
