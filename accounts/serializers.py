from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import (
    User,
    Role,
    UserProfile,
    OTPVerification,
    PendingRegistration,
    RoleApplication,
    RoleApplicationDocument,
    Report,
    AdminActivityLog,
)
from accounts.otp import generate_otp, hash_otp, verify_otp
from ecoLoop.mail import (
    send_login_otp,
    send_registration_otp,
    send_password_reset_otp,
    send_role_application_approved,
)

from ecoLoop.utils import log_admin_action

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
            "is_active",
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

        if PendingRegistration.objects.filter(email=email, is_used=False).exists():
            PendingRegistration.objects.filter(email=email, is_used=False).delete()

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
                password_hash=password,  # Store plain password, will be hashed by create_user
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

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            print("User not found for email:", email)
            raise serializers.ValidationError({"message": "Invalid credentials."})

        if not user.is_active:
            print("Inactive account for email:", email)
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
                print("Incorrect password for email:", email)
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
                "roles": [
                    {"id": role.id, "name": role.name} for role in user.roles.all()
                ],
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
                    password=pending.password_hash,  # Plain password, create_user will hash it
                )
                user.is_email_verified = True
                user.save()
                pending.is_used = True
                pending.save(update_fields=["is_used"])
                # UserProfile is auto-created by signal in models.py

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
    is_email_verified = serializers.BooleanField(
        source="user.is_email_verified", read_only=True
    )
    is_phone_verified = serializers.BooleanField(
        source="user.is_phone_verified", read_only=True
    )
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    roles = serializers.SerializerMethodField()
    can_apply_ngo = serializers.BooleanField(read_only=True)
    can_apply_recycler = serializers.BooleanField(read_only=True)
    has_applied_ngo = serializers.BooleanField(read_only=True)
    has_applied_recycler = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "email",
            "full_name",
            "phone_number",
            "roles",
            "profile_picture",
            "city",
            "area",
            "postal_code",
            "latitude",
            "longitude",
            "bio",
            "is_email_verified",
            "is_phone_verified",
            "can_apply_ngo",
            "can_apply_recycler",
            "has_applied_ngo",
            "has_applied_recycler",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "latitude",
            "longitude",
            "can_apply_ngo",
            "can_apply_recycler",
            "has_applied_ngo",
            "has_applied_recycler",
        ]

    def get_roles(self, obj):
        """Return list of role names and descriptions."""
        return [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
            }
            for role in obj.user.roles.all()
        ]

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


class RoleApplicationDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = RoleApplicationDocument
        fields = ["id", "document", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class RoleApplicationSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    applicant = serializers.SerializerMethodField(read_only=True)
    reviewed_by_details = serializers.SerializerMethodField(read_only=True)
    documents = RoleApplicationDocumentSerializer(many=True, read_only=True)
    document_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="Upload multiple documents for the application",
    )

    class Meta:
        model = RoleApplication
        fields = [
            "id",
            "user",
            "applicant",
            "role_type",
            "organization_name",
            "registration_number",
            "established_date",
            "address",
            "description",
            "documents",
            "document_files",
            "status",
            "admin_notes",
            "reviewed_by",
            "reviewed_by_details",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "applicant",
            "documents",
            "status",
            "admin_notes",
            "reviewed_by",
            "reviewed_by_details",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]

    def get_applicant(self, obj):
        """Return detailed information about the user who applied"""
        return {
            "id": str(obj.user.id),
            "email": obj.user.email,
            "full_name": obj.user.full_name,
            "phone_number": obj.user.phone_number,
        }

    def get_reviewed_by_details(self, obj):
        """Return detailed information about the admin who reviewed"""
        if obj.reviewed_by:
            return {
                "id": str(obj.reviewed_by.id),
                "email": obj.reviewed_by.email,
                "full_name": obj.reviewed_by.full_name,
            }
        return None

    def validate(self, data):
        # Check if user already has a pending application for this role
        user = self.context["request"].user
        role_type = data.get("role_type")

        if RoleApplication.objects.filter(
            user=user, role_type=role_type, status="pending"
        ).exists():
            raise serializers.ValidationError(
                f"You already have a pending {role_type} application."
            )

        # Check if user already has this role
        if user.roles.filter(name=role_type).exists():
            raise serializers.ValidationError(f"You already have the {role_type} role.")

        return data

    def create(self, validated_data):
        # Extract document-related fields
        document_files = validated_data.pop("document_files", [])

        # Set user from request context
        validated_data["user"] = self.context["request"].user

        # Create the application
        with transaction.atomic():
            application = super().create(validated_data)

            # Create associated documents
            if document_files:
                for doc_file in document_files:
                    RoleApplicationDocument.objects.create(
                        application=application,
                        document=doc_file,
                    )

        return application

    def update(self, instance, validated_data):
        # Extract document-related fields
        document_files = validated_data.pop("document_files", [])

        # Update the application
        with transaction.atomic():
            application = super().update(instance, validated_data)

            # Add new documents (don't delete existing ones)
            if document_files:
                for doc_file in document_files:
                    RoleApplicationDocument.objects.create(
                        application=application,
                        document=doc_file,
                    )

        return application


class RoleApplicationReviewSerializer(serializers.Serializer):
    """Serializer for admin to approve/reject applications"""

    action = serializers.ChoiceField(choices=["approve", "reject"], required=True)
    admin_notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data["action"] == "reject" and not data.get("admin_notes"):
            raise serializers.ValidationError(
                "Admin notes are required when rejecting an application."
            )
        return data

    def update(self, instance, validated_data):
        """Update the role application status and handle role assignment"""
        action = validated_data.get("action")
        admin_notes = validated_data.get("admin_notes", "")
        admin_user = self.context["request"].user

        # Check if application is already reviewed
        if instance.status != "pending":
            raise serializers.ValidationError(
                f"Cannot review application. Current status: {instance.status}"
            )

        with transaction.atomic():
            if action == "approve":
                # Set status to approved
                instance.status = "approved"
                instance.admin_notes = admin_notes
                instance.reviewed_by = admin_user
                instance.reviewed_at = timezone.now()
                instance.save()

                # Assign the role to the user
                role, created = Role.objects.get_or_create(
                    name=instance.role_type,
                    defaults={
                        "description": f"{instance.role_type} role",
                        "single_assignment": instance.role_type == "NGO",
                    },
                )
                instance.user.roles.add(role)
                log_admin_action(
                    admin=admin_user,
                    action=f"application_approved",
                    target_type="RoleApplication",
                    target_id=str(instance.id),
                    target_name=f"{instance.user.full_name} - {instance.role_type}",
                    reason=admin_notes,
                )

                # Send approval email notification
                try:
                    send_role_application_approved(
                        email=instance.user.email,
                        full_name=instance.user.full_name,
                        role_type=instance.role_type,
                    )
                except Exception as e:
                    pass

            elif action == "reject":
                # Set status to rejected
                instance.status = "rejected"
                instance.admin_notes = admin_notes
                instance.reviewed_by = admin_user
                instance.reviewed_at = timezone.now()
                instance.save()
                log_admin_action(
                    admin=admin_user,
                    action=f"application_rejected",
                    target_type="RoleApplication",
                    target_id=str(instance.id),
                    target_name=f"{instance.user.full_name} - {instance.role_type}",
                    reason=admin_notes,
                )

        return instance


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for user-facing report operations"""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.full_name", read_only=True, allow_null=True
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "user",
            "user_name",
            "user_email",
            "category",
            "listing_id",
            "target_user_id",
            "conversation_id",
            "subject",
            "description",
            "attachment",
            "status",
            "admin_notes",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_name",
            "user_email",
            "status",
            "admin_notes",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        category = data.get("category")
        listing_id = data.get("listing_id")
        conversation_id = data.get("conversation_id")
        target_user_id = data.get("target_user_id")

        # Validate required fields based on category
        if category == "product":
            if not listing_id:
                raise serializers.ValidationError(
                    {"listing_id": "Listing ID is required when category is 'product'."}
                )

        if category == "message":
            if not conversation_id:
                raise serializers.ValidationError(
                    {
                        "conversation_id": "Conversation ID is required when category is 'message'."
                    }
                )

        if category == "user_behavior":
            if not target_user_id:
                raise serializers.ValidationError(
                    {
                        "target_user_id": "Target user ID is required when category is 'user_behavior'."
                    }
                )

        return data

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ReportAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin operations on reports"""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.full_name", read_only=True, allow_null=True
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "user",
            "user_name",
            "user_email",
            "category",
            "subject",
            "description",
            "attachment",
            "status",
            "admin_notes",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_name",
            "user_email",
            "category",
            "subject",
            "description",
            "attachment",
            "reviewed_by_name",
            "created_at",
        ]

    def update(self, instance, validated_data):
        # If status is being changed, update reviewed_by and reviewed_at
        if "status" in validated_data and validated_data["status"] != instance.status:
            instance.reviewed_by = self.context["request"].user
            instance.reviewed_at = timezone.now()

        return super().update(instance, validated_data)


class ReportReviewSerializer(serializers.Serializer):
    """Serializer for admin to review reports"""

    action = serializers.ChoiceField(
        choices=["in_review", "resolve", "close"], required=True
    )
    admin_notes = serializers.CharField(required=False, allow_blank=True)


class AdminActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for viewing admin activity logs"""

    admin_name = serializers.CharField(source="admin.full_name", read_only=True)
    admin_email = serializers.CharField(source="admin.email", read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    result_display = serializers.CharField(source="get_result_display", read_only=True)

    class Meta:
        model = AdminActivityLog
        fields = [
            "id",
            "admin",
            "admin_name",
            "admin_email",
            "action",
            "action_display",
            "target_type",
            "target_id",
            "target_name",
            "result",
            "result_display",
            "reason",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin to manage users - allows blocking/unblocking"""

    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone_number",
            "roles",
            "is_active",
            "is_email_verified",
            "is_phone_verified",
            "date_joined",
        ]
        read_only_fields = ["id", "email", "date_joined"]

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

    def update(self, instance, validated_data):
        """Update user and log blocking/unblocking actions"""
        request = self.context.get("request")
        
        # Check if is_active is being changed
        if "is_active" in validated_data:
            old_is_active = instance.is_active
            new_is_active = validated_data["is_active"]
            
            # Only log if there's an actual change
            if old_is_active != new_is_active:
                # Update the instance first
                instance = super().update(instance, validated_data)
                
                # Log the action
                if new_is_active is False:
                    # User was blocked
                    action = "user_blocked"
                    details = f"User {instance.email} has been blocked"
                else:
                    # User was unblocked
                    action = "user_unblocked"
                    details = f"User {instance.email} has been unblocked"
                
                # Get reason from request data if provided
                reason = None
                if request and hasattr(request, "data"):
                    reason = request.data.get("reason", None)
                
                # Log the admin action
                if request and hasattr(request, "user"):
                    log_admin_action(
                        admin=request.user,
                        action=action,
                        target_type="User",
                        target_id=str(instance.id),
                        target_name=f"{instance.full_name} (ID: {instance.id})",
                        result="success",
                        reason=reason,
                    )
                
                return instance
        
        # If is_active wasn't changed, just do normal update
        return super().update(instance, validated_data)
