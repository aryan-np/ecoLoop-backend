from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.hashers import make_password

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import (
    User,
    Role,
    UserProfile,
    OTPVerification,
    PendingRegistration,
)
from accounts.otp import generate_otp, hash_otp, verify_otp
from ecoLoop.mail import (
    send_login_otp,
    send_registration_otp,
    send_password_reset_otp,
)


MAX_ATTEMPTS = 5


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone_number",
            "roles",
            "is_email_verified",
            "is_phone_verified",
            "date_joined",
        ]

    def get_roles(self, obj):
        """Return list of role names and descriptions."""
        return [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
            }
            for role in obj.roles.all()
        ]


class UserRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    full_name = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)

    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate_phone_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if len(value) != 10:
            raise serializers.ValidationError("Phone number must be 10 digits long.")
        return value

    def validate(self, data):
        email = data["email"]

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {"email": "User with this email already exists."}
            )

        try:
            validate_password(data["password"])
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})

        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        return data

    def create(self, validated_data):
        """
        INIT REGISTER:
        - Create PendingRegistration (store data + hashed password)
        - Create REGISTER OTP in OTPVerification
        - Send registration OTP email
        - Return registration_id (frontend uses it in OTP verify)
        """
        email = validated_data["email"]
        full_name = validated_data["full_name"]
        phone_number = validated_data["phone_number"]
        password = validated_data["password"]

        otp = generate_otp(6)
        otp_hash_value = hash_otp(otp)

        with transaction.atomic():
            # invalidate older pending requests (optional)
            PendingRegistration.objects.filter(email=email, is_used=False).update(
                is_used=True
            )

            pending = PendingRegistration.objects.create(
                email=email,
                full_name=full_name,
                phone_number=phone_number,
                password_hash=make_password(password),
                expires_at=PendingRegistration.default_expiry(minutes=10),
            )

            # invalidate old unused REGISTER OTPs
            OTPVerification.objects.filter(
                email=email, purpose="REGISTER", is_used=False
            ).update(is_used=True)

            OTPVerification.objects.create(
                email=email,
                purpose="REGISTER",
                otp_hash=otp_hash_value,
                expires_at=OTPVerification.default_expiry(minutes=5),
            )

        send_registration_otp(email=email, otp=otp)

        return {
            "message": "OTP sent to your email. Verify OTP to complete registration.",
            "registration_id": str(pending.id),
            "email": email,
        }


class UserLoginSerializer(serializers.Serializer):
    METHOD_CHOICES = (("PASSWORD", "PASSWORD"), ("OTP", "OTP"))

    email = serializers.EmailField(required=True)
    method = serializers.ChoiceField(choices=METHOD_CHOICES, default="PASSWORD")

    # only required when method=PASSWORD
    password = serializers.CharField(write_only=True, required=False)

    def validate(self, data):
        email = data["email"]
        method = data["method"]

        print("Login method:", method)

        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError({"message": "Invalid credentials."})

        if not user.is_active:
            raise serializers.ValidationError(
                {"message": "Account is inactive. Please contact support."}
            )

        if method == "PASSWORD":
            password = data.get("password")
            if not password:
                raise serializers.ValidationError(
                    {"password": "This field is required for login."}
                )
            if not user.check_password(password):
                raise serializers.ValidationError({"message": "Invalid credentials."})

        self.user = user
        return data

    def create(self, validated_data):
        """
        If method=OTP -> send OTP, return message
        If method=PASSWORD -> return tokens
        """
        method = validated_data["method"]
        email = validated_data["email"]
        user = self.user
        print("method", method)
        if method == "OTP":
            print("here")
            otp = generate_otp(6)
            otp_hash_value = hash_otp(otp)

            with transaction.atomic():
                OTPVerification.objects.filter(
                    email=email, purpose="LOGIN", is_used=False
                ).update(is_used=True)

                OTPVerification.objects.create(
                    email=email,
                    purpose="LOGIN",
                    otp_hash=otp_hash_value,
                    expires_at=OTPVerification.default_expiry(minutes=5),
                )

            print("Generated OTP for login:", otp)  # For testing; remove in production
            send_login_otp(email=email, otp=otp)

            return {
                "message": "Login OTP sent to your email. Verify OTP to get tokens.",
                "email": email,
            }

        # PASSWORD login -> tokens now
        refresh = RefreshToken.for_user(user)
        return {
            "message": "Login successful.",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
            },
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
        }


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    purpose = serializers.ChoiceField(choices=["REGISTER", "LOGIN", "RESET_PASSWORD"])
    otp = serializers.CharField(min_length=4, max_length=10)

    # only for RESET_PASSWORD
    new_password = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    confirm_new_password = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )

    # only for REGISTER (to find pending registration)
    registration_id = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        purpose = data["purpose"]
        email = data["email"]
        otp = data["otp"]

        # Ignore registration_id if purpose is LOGIN
        if purpose == "LOGIN":
            data.pop("registration_id", None)

        if purpose == "RESET_PASSWORD":
            new_password = data.get("new_password")
            confirm_new_password = data.get("confirm_new_password")

            if not new_password or not confirm_new_password:
                raise serializers.ValidationError(
                    {
                        "new_password": "new_password and confirm_new_password are required for RESET_PASSWORD."
                    }
                )

            if new_password != confirm_new_password:
                raise serializers.ValidationError(
                    {"new_password": "Passwords do not match."}
                )

            try:
                validate_password(new_password)
            except ValidationError as e:
                raise serializers.ValidationError({"new_password": e.messages})

        if purpose == "REGISTER":
            registration_id = data.get("registration_id", "").strip()
            if not registration_id:
                raise serializers.ValidationError(
                    {
                        "registration_id": "registration_id is required for REGISTER verification."
                    }
                )
            # Validate UUID format
            try:
                import uuid

                uuid.UUID(registration_id)
                data["registration_id"] = registration_id
            except ValueError:
                raise serializers.ValidationError(
                    {"registration_id": "Invalid registration_id format."}
                )

        # Verify OTP here (before create is called)
        otp_obj = self._get_latest_active_otp(email=email, purpose=purpose)
        self._verify_common(otp_obj=otp_obj, otp=otp)

        return data

    def _get_latest_active_otp(self, email: str, purpose: str):
        return (
            OTPVerification.objects.filter(email=email, purpose=purpose, is_used=False)
            .order_by("-created_at")
            .first()
        )

    def _verify_common(self, otp_obj: OTPVerification, otp: str):
        if not otp_obj:
            raise serializers.ValidationError({"otp": "No active OTP found."})

        if otp_obj.is_expired():
            otp_obj.is_used = True
            otp_obj.save(update_fields=["is_used"])
            raise serializers.ValidationError({"otp": "OTP expired."})

        if otp_obj.attempts >= MAX_ATTEMPTS:
            otp_obj.is_used = True
            otp_obj.save(update_fields=["is_used"])
            raise serializers.ValidationError({"otp": "Too many attempts."})

        if not verify_otp(otp, otp_obj.otp_hash):
            otp_obj.attempts += 1
            otp_obj.save(update_fields=["attempts"])
            raise serializers.ValidationError({"otp": "Invalid OTP."})

        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])

    def create(self, validated_data):
        email = validated_data["email"]
        purpose = validated_data["purpose"]

        # OTP already verified in validate(), get it again to process the result
        otp_obj = self._get_latest_active_otp(email=email, purpose=purpose)

        # =========================
        # REGISTER: create user from pending
        # =========================
        if purpose == "REGISTER":
            registration_id = validated_data["registration_id"]

            pending = PendingRegistration.objects.filter(
                id=registration_id, email=email, is_used=False
            ).first()

            if not pending:
                raise serializers.ValidationError(
                    {"registration_id": "Invalid or already used registration request."}
                )

            if pending.is_expired():
                pending.is_used = True
                pending.save(update_fields=["is_used"])
                raise serializers.ValidationError(
                    {
                        "registration_id": "Registration request expired. Please register again."
                    }
                )

            with transaction.atomic():
                user = User.objects.create_user(
                    email=pending.email,
                    full_name=pending.full_name,
                    phone_number=pending.phone_number,
                    password=pending.password_hash,  # This is already hashed
                )
                user.is_email_verified = True
                user.save()
                pending.is_used = True
                pending.save(update_fields=["is_used"])

            return {
                "message": "Registration completed successfully.",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "is_email_verified": user.is_email_verified,
                },
            }

        # =========================
        # LOGIN: issue tokens
        # =========================
        if purpose == "LOGIN":
            user = User.objects.filter(email=email).first()
            if not user:
                raise serializers.ValidationError({"email": "User not found."})

            refresh = RefreshToken.for_user(user)
            return {
                "message": "Login successful.",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            }

        # =========================
        # RESET_PASSWORD: set new password
        # =========================
        if purpose == "RESET_PASSWORD":
            user = User.objects.filter(email=email).first()
            if not user:
                raise serializers.ValidationError({"email": "User not found."})

            new_password = validated_data["new_password"]
            user.set_password(new_password)
            user.save()

            return {"message": "Password reset successfully."}

        return {"message": "OTP verified successfully."}


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True, help_text="Refresh token to blacklist"
    )

    def validate(self, data):
        """Validate the refresh token."""
        self.token = data["refresh"]
        return data

    def save(self, **kwargs):
        """Blacklist the refresh token."""
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except Exception as e:
            raise serializers.ValidationError({"message": "Invalid or expired token."})


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email")
    full_name = serializers.CharField(source="user.full_name")
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "email",
            "full_name",
            "phone_number",
            "profile_picture",
            "city",
            "area",
            "postal_code",
            "latitude",
            "longitude",
            "bio",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "latitude", "longitude"]

    def update(self, instance, validated_data):
        # Handle nested user fields
        user_data = {}
        if "user" in validated_data:
            user_data = validated_data.pop("user")

        # Update User model fields
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # Update UserProfile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
