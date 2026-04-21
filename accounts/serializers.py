from rest_framework import serializers


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email address to send the OTP to.")


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email address used to request the OTP.")
    otp = serializers.CharField(
        min_length=6,
        max_length=6,
        help_text="6-digit OTP code.",
    )
