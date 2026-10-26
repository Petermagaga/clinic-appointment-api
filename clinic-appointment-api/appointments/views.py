from datetime import datetime,timedelta
from django.utils import timezone

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

from .serializers import (AppointmentSerializer,
                          AppointmentCreateSerializer,
                          AppointmentCancelSerializer,
                          AppointmentRescheduleSerializer)
from .models import (Appointment,
                     Doctor,DoctorWorkingHours)

from .services import (book_appointment,
                       cancel_appointment,
                       reschedule_appointment)
class AppointmentCreateView(APIView):
    def post(self,request):
        serializer = AppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            appointment=book_appointment(
                doctor_id=serializer.validated_data["doctor_id"],
                patient_id=serializer.validated_data["patient_id"],
                starts_at=serializer.validated_data["starts_at"]
            )

        except DjangoValidationError as exc:
            if hasattr(exc,"message_dict"):
                details=exc.message_dict
            else:
                details={"detail":exc.messages}
            raise ValidationError(details) from exc

        response_serializer=AppointmentSerializer(appointment)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )



class DoctorAvailabilityView(APIView):
    def get(self,request,doctor_id):
        date_value=request.query_params.get("date")

        if not date_value:
            return Response(
                {"date":["This query parameter is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            requested_date=datetime.strptime(
                date_value,"%Y-%m-%d"
            ).date()

        except ValueError: 
            return Response(
                {"date":["use the YYYY-MM-DD format."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            doctor=Doctor.objects.get(pk=doctor_id,is_active=True)
        except Doctor.DoesNotExist:
            return Response(
                {"detail":"Active doctor not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        schedule=DoctorWorkingHours.objects.filter(
            doctor=doctor,
            weekday=requested_date.weekday(),
        ).first()

        if schedule is None:
            return Response ({
                "doctor_id":doctor_id,
                "doctor_name":doctor.name,
                "date":requested_date.isoformat(),
                "available_slots":[],
            })

        current_timezone=timezone.get_current_timezone()
        opening=timezone.make_aware(
            datetime.combine(requested_date,schedule.starts_time),
            current_timezone,
        )
        closing =timezone.make_aware(
            datetime.combine(requested_date,schedule.ends_time),
            current_timezone
        )

        now=timezone.now()
        minimum_start =now+timedelta(hours=1)

        bookings=Appointment.objects.filter(
            doctor=doctor,
            status=Appointment.Status.BOOKED,
            starts_at__lt=closing,
            ends_at__gt=opening,

        ).values_list("starts_at","ends_at")

        booked_ranges=list(bookings)
        available_slots=[]
        slot_start=opening

        while slot_start + timedelta(minutes=30) <= closing:
            slot_end = slot_start + timedelta(minutes=30)

            overlaps_booking = any(
                booked_start < slot_end and booked_end > slot_start
                for booked_start, booked_end in booked_ranges
            )

            if slot_start >= minimum_start and not overlaps_booking:
                available_slots.append({
                    "starts_at": slot_start.isoformat(),
                    "ends_at": slot_end.isoformat(),
                })

            slot_start = slot_end

        return Response({
            "doctor_id": doctor.id,
            "doctor_name": doctor.name,
            "date": requested_date.isoformat(),
            "available_slots": available_slots,
        })


class AppointmentCancelView(APIView):
    def patch(self,request,appointment_id):
        request_serializer =AppointmentCancelSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        try:
            appointment=cancel_appointment(
                appointment_id=appointment_id,
                reason=request_serializer.validated_data["reason"],
            )

        except DjangoValidationError as exc:
            details=(
                exc.message_dict
                if hasattr(exc,"message_dict")
                else {"detail":exc.messages} )

            if "appointment_id" in details:
                raise NotFound(details) from exc

            raise ValidationError(details) from exc
        response_serializer=AppointmentSerializer(appointment)
        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )


class AppointmentRescheduleView(APIView):
    def patch(self,request,appointment_id):
        request_serializer=AppointmentRescheduleSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        try:
            appointment=reschedule_appointment(
                appointment_id=appointment_id,
                new_starts_at=request_serializer.validated_data[
                    "new_starts_at"
                ],
            )

        except DjangoValidationError as exc:
            details=(
                exc.message_dict
                if hasattr(exc,"message_dict")
                else {"detail":exc.messages}
            )

            if "appointment_id" in details:
                raise NotFound(details) from exc

            raise ValidationError(details) from exc

        response_serializer = AppointmentSerializer(appointment)
        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )



    

        