from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import PageNumberPagination


class MessagePagination(PageNumberPagination):
    page_size = 20


from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)

from communications.serializers import (
    ThreadSerializer,
    MessageSerializer,
    ThreadDetailSerializer,
    OfferSerializer,
)
from communications.models import Thread, Message, Offer
from ecoLoop.utils import api_response
from ecoLoop.utils import log_admin_action
from django.db.models import Q, Prefetch
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from accounts.permissions import IsSuperUser
from accounts.models import Report
from django.utils import timezone
from ecoLoop.mail import (
    send_chat_cleared_notice,
    send_chat_restored_notice,
    send_report_reviewed,
)

from loguru import logger


def _as_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


@extend_schema(tags=["Communications"])
@extend_schema_view(
    list=extend_schema(
        summary="List user threads",
        description="List all chat threads for the authenticated user.",
        responses={200: ThreadSerializer(many=True)},
    ),
    create=extend_schema(
        summary="Create or get thread",
        description="Create a new thread between two users or get existing thread.",
        request=ThreadSerializer,
        responses={201: ThreadSerializer, 200: ThreadSerializer},
    ),
    retrieve=extend_schema(
        summary="Get thread with messages",
        description="Get a specific thread with all its messages.",
        responses={200: ThreadDetailSerializer},
    ),
)
class ThreadViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = ThreadSerializer
    lookup_field = "id"

    def get_queryset(self):
        """Get threads where the user is either user1 or user2"""
        user = self.request.user
        return (
            Thread.objects.filter(Q(user1=user) | Q(user2=user))
            .select_related("user1", "user2", "product")
            .prefetch_related(
                Prefetch("messages", queryset=Message.objects.filter(is_deleted=False)),
                "offers",
            )
            .order_by("-updated_at")
        )

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return api_response(
                result=serializer.data,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception(
                f"Error listing threads for user {request.user.id}: {str(e)}"
            )
            return api_response(
                error_message=str(e),
                is_success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(
                data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                return api_response(
                    result=None,
                    is_success=False,
                    error_message=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            thread = serializer.save()
            result_serializer = self.get_serializer(
                thread, context={"request": request}
            )

            # Check if thread was just created
            created = request.data.get("user2") is not None
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

            return api_response(
                result=result_serializer.data,
                is_success=True,
                status_code=status_code,
            )
        except Exception as e:
            logger.exception(
                f"Error creating thread for user {request.user.id}: {str(e)}"
            )
            return api_response(
                error_message=str(e),
                is_success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            thread = self.get_object()
            # Check if user is part of this thread
            if thread.user1 != request.user and thread.user2 != request.user:
                return api_response(
                    error_message="Not allowed",
                    is_success=False,
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            serializer = ThreadDetailSerializer(thread, context={"request": request})
            # Mark messages as read
            thread.messages.filter(is_read=False, is_deleted=False).exclude(
                sender=request.user
            ).update(is_read=True)

            return api_response(
                result=serializer.data,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )
        except Thread.DoesNotExist:
            return api_response(
                error_message="Thread not found",
                is_success=False,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return api_response(
                error_message=str(e),
                is_success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="admin-clear-messages",
        permission_classes=[IsSuperUser],
    )
    def admin_clear_messages(self, request, *args, **kwargs):
        thread = Thread.objects.filter(id=kwargs.get("id")).first()
        if not thread:
            return api_response(
                result=None,
                is_success=False,
                error_message="Thread not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        report_id = request.data.get("report_id")
        if report_id:
            report = (
                Report.objects.filter(id=report_id)
                .select_related("user", "conversation_id")
                .first()
            )
            if not report:
                return api_response(
                    result=None,
                    is_success=False,
                    error_message="Report not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            if report.status not in {"pending", "reopened"}:
                return api_response(
                    result=None,
                    is_success=False,
                    error_message="Only pending or reopened reports can be actioned",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if report.conversation_id_id and report.conversation_id_id != thread.id:
                return api_response(
                    result=None,
                    is_success=False,
                    error_message="Report does not match this thread",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        if not Message.objects.filter(thread=thread, is_deleted=False).exists():
            if not thread.is_admin_reviewed:
                thread.is_admin_reviewed = True
                thread.save(update_fields=["is_admin_reviewed"])
            return api_response(
                result={"cleared_count": 0, "is_admin_reviewed": True},
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        cleared_count = Message.objects.filter(thread=thread).update(is_deleted=True)

        if not thread.is_admin_reviewed:
            thread.is_admin_reviewed = True
            thread.save(update_fields=["is_admin_reviewed"])

        log_admin_action(
            admin=request.user,
            action="other",
            target_type="Thread",
            target_id=thread.id,
            target_name=f"Thread {thread.id}",
            reason=request.data.get("reason"),
        )

        notify_user = _as_bool(request.data.get("notify_user"), default=True)
        if notify_user:
            for participant in [thread.user1, thread.user2]:
                if participant and participant.email:
                    send_chat_cleared_notice(
                        participant.email,
                        participant.full_name,
                        str(thread.id),
                    )

        if report_id:
            report.status = "resolved"
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save(update_fields=["status", "reviewed_by", "reviewed_at"])
            if notify_user and report.user and report.user.email:
                send_report_reviewed(
                    report.user.email,
                    report.user.full_name,
                    report.subject,
                )

        return api_response(
            result={"cleared_count": cleared_count, "is_admin_reviewed": True},
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="admin-restore-messages",
        permission_classes=[IsSuperUser],
    )
    def admin_restore_messages(self, request, *args, **kwargs):
        thread = Thread.objects.filter(id=kwargs.get("id")).first()
        if not thread:
            return api_response(
                result=None,
                is_success=False,
                error_message="Thread not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        report_id = request.data.get("report_id")
        if report_id:
            report = (
                Report.objects.filter(id=report_id)
                .select_related("user", "conversation_id")
                .first()
            )
            if not report:
                return api_response(
                    result=None,
                    is_success=False,
                    error_message="Report not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            if report.status != "resolved":
                return api_response(
                    result=None,
                    is_success=False,
                    error_message="Only resolved reports can be undone",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if report.conversation_id_id and report.conversation_id_id != thread.id:
                return api_response(
                    result=None,
                    is_success=False,
                    error_message="Report does not match this thread",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        if not Message.objects.filter(thread=thread, is_deleted=True).exists():
            if not thread.is_admin_reviewed:
                thread.is_admin_reviewed = True
                thread.save(update_fields=["is_admin_reviewed"])
            return api_response(
                result={"restored_count": 0, "is_admin_reviewed": True},
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        restored_count = Message.objects.filter(thread=thread).update(is_deleted=False)

        if not thread.is_admin_reviewed:
            thread.is_admin_reviewed = True
            thread.save(update_fields=["is_admin_reviewed"])

        log_admin_action(
            admin=request.user,
            action="other",
            target_type="Thread",
            target_id=thread.id,
            target_name=f"Thread {thread.id}",
            reason=request.data.get("reason"),
        )

        notify_user = _as_bool(request.data.get("notify_user"), default=True)
        if notify_user:
            for participant in [thread.user1, thread.user2]:
                if participant and participant.email:
                    send_chat_restored_notice(
                        participant.email,
                        participant.full_name,
                        str(thread.id),
                    )

        if report_id:
            report.status = "reopened"
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save(update_fields=["status", "reviewed_by", "reviewed_at"])
            if notify_user and report.user and report.user.email:
                send_report_reviewed(
                    report.user.email,
                    report.user.full_name,
                    report.subject,
                )

        return api_response(
            result={"restored_count": restored_count, "is_admin_reviewed": True},
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


@extend_schema(tags=["Communications"])
@extend_schema_view(
    list=extend_schema(
        summary="List thread messages",
        description="List all messages in a specific thread.",
        responses={200: MessageSerializer(many=True)},
    ),
    create=extend_schema(
        summary="Send message",
        description="Send a message in a thread.",
        request=MessageSerializer,
        responses={201: MessageSerializer},
    ),
)
class MessageViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = MessageSerializer
    pagination_class = MessagePagination

    def get_queryset(self):
        """Get messages for a specific thread"""
        thread_id = self.request.query_params.get("thread_id")
        if thread_id:
            return (
                Message.objects.filter(thread_id=thread_id, is_deleted=False)
                .select_related("sender", "thread")
                .order_by("-created_at")
            )
        return (
            Message.objects.filter(is_deleted=False)
            .select_related("sender", "thread")
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        try:
            thread_id = request.query_params.get("thread_id")
            if not thread_id:
                return api_response(
                    error_message="thread_id is required",
                    is_success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Check if user is part of thread
            try:
                thread = Thread.objects.get(id=thread_id)
                if thread.user1 != request.user and thread.user2 != request.user:
                    return api_response(
                        error_message="Not allowed",
                        is_success=False,
                        status_code=status.HTTP_403_FORBIDDEN,
                    )
            except Thread.DoesNotExist:
                return api_response(
                    error_message="Thread not found",
                    is_success=False,
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                result = {
                    "count": self.paginator.page.paginator.count,
                    "next": self.paginator.get_next_link(),
                    "previous": self.paginator.get_previous_link(),
                    "results": serializer.data,
                }
                return api_response(
                    result=result,
                    is_success=True,
                    status_code=status.HTTP_200_OK,
                )

            serializer = self.get_serializer(queryset, many=True)
            return api_response(
                result=serializer.data,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception(
                f"Error listing messages for user {request.user.id}: {str(e)}"
            )
            return api_response(
                error_message=str(e),
                is_success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(
                data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                return api_response(
                    result=None,
                    is_success=False,
                    error_message=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            message = serializer.save()
            result_serializer = self.get_serializer(
                message, context={"request": request}
            )

            return api_response(
                result=result_serializer.data,
                is_success=True,
                status_code=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.exception(
                f"Error creating message for user {request.user.id}: {str(e)}"
            )
            return api_response(
                error_message=str(e),
                is_success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read(self, request):
        message_ids = request.data.get("message_ids", [])

        if not isinstance(message_ids, list) or not message_ids:
            return api_response(
                result=None,
                is_success=False,
                error_message={
                    "message_ids": ["A non-empty list of message IDs is required."]
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        marked_count = (
            Message.objects.filter(
                id__in=message_ids,
                is_read=False,
            )
            .exclude(sender=request.user)
            .update(is_read=True)
        )

        return api_response(
            result={"marked_count": marked_count},
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


@extend_schema(tags=["Communications"])
class OfferViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = OfferSerializer
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        thread_id = self.request.query_params.get("thread_id")
        if thread_id:
            return (
                Offer.objects.filter(thread_id=thread_id)
                .select_related("proposed_by", "thread")
                .order_by("-created_at")
            )
        return Offer.objects.none()

    def _get_thread_or_error(self, thread_id):
        try:
            return Thread.objects.get(id=thread_id), None
        except Thread.DoesNotExist:
            return None, api_response(
                result=None,
                is_success=False,
                error_message=["Thread not found."],
                status_code=status.HTTP_404_NOT_FOUND,
            )

    def _assert_participant(self, thread, user):
        if thread.user1 != user and thread.user2 != user:
            return api_response(
                result=None,
                is_success=False,
                error_message=["You are not a participant of this thread."],
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return None

    def _broadcast_offer(self, offer):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"thread_{offer.thread_id}",
            {
                "type": "offer.event",
                "offer_id": offer.id,
                "amount": str(offer.amount),
                "status": offer.status,
                "proposed_by": str(offer.proposed_by_id),
            },
        )

    def list(self, request, *args, **kwargs):
        thread_id = request.query_params.get("thread_id")
        if not thread_id:
            return api_response(
                result=None,
                is_success=False,
                error_message=["thread_id query param is required."],
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        thread, err = self._get_thread_or_error(thread_id)
        if err:
            return err

        err = self._assert_participant(thread, request.user)
        if err:
            return err

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        thread_id = request.data.get("thread_id")
        amount = request.data.get("amount")

        if not thread_id:
            return api_response(
                result=None,
                is_success=False,
                error_message={"thread_id": ["This field is required."]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if not amount:
            return api_response(
                result=None,
                is_success=False,
                error_message={"amount": ["This field is required."]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        thread, err = self._get_thread_or_error(thread_id)
        if err:
            return err

        err = self._assert_participant(thread, request.user)
        if err:
            return err

        # Expire any existing pending offer on this thread
        Offer.objects.filter(thread=thread, status="pending").update(status="expired")

        offer = Offer.objects.create(
            thread=thread,
            proposed_by=request.user,
            amount=amount,
            status="pending",
        )

        self._broadcast_offer(offer)

        serializer = self.get_serializer(offer)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        try:
            offer = Offer.objects.select_related("thread", "proposed_by").get(
                pk=kwargs["pk"]
            )
        except Offer.DoesNotExist:
            return api_response(
                result=None,
                is_success=False,
                error_message=["Offer not found."],
                status_code=status.HTTP_404_NOT_FOUND,
            )

        err = self._assert_participant(offer.thread, request.user)
        if err:
            return err

        if offer.proposed_by == request.user:
            return api_response(
                result=None,
                is_success=False,
                error_message=["You cannot respond to your own offer."],
                status_code=status.HTTP_403_FORBIDDEN,
            )

        if offer.status != "pending":
            return api_response(
                result=None,
                is_success=False,
                error_message=["Only pending offers can be accepted or rejected."],
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        new_status = request.data.get("status")
        if new_status not in ("accepted", "rejected"):
            return api_response(
                result=None,
                is_success=False,
                error_message={"status": ["Must be 'accepted' or 'rejected'."]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        offer.status = new_status
        offer.save(update_fields=["status"])

        self._broadcast_offer(offer)

        serializer = self.get_serializer(offer)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )
