from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (AppointmentSerializer,AppointmentCreateSerializer)

from .services import book_appointment
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
