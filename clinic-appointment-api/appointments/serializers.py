from rest_framework import serializers

from .models import Appointment,Doctor, Patient

class AppointmentCreateSerializer(serializers.Serializer):
    doctor_id=serializers.IntegerField(min_value=1)
    patient_id=serializers.IntegerField(min_value=1)
    starts_at=serializers.DateTimeField()

    def validate_doctor_id(self,value):
        if not Doctor.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "The selected doctor does not exist"
            )
        return value

    def validate_patient_id(self,value):
        if not Patient.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "The selected Patient does not exist"
            )
        return value


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name=serializers.CharField(source="doctor.name",read_only=True)
    patient_name=serializers.CharField(source="patient.full_name",read_only=True)

    class Meta:
        model= Appointment
        fields=[
            "id",
            "doctor",
            "doctor_name",
            "patient",
            "patient_name",
            "starts_at",
            "ends_at",
            "status",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields=fields

class AppointmentCancelSerializer(serializers.Serializer):
    reason=serializers.CharField(
        required=True,allow_blank=False,trim_whitespace=True,
        max_length=1000,
    )

    def validate_reason(self,value):
        if not value.strip():
            raise serializers.ValidationError(
                "A cancellation reason is required."
            )
        return value.strip()
    