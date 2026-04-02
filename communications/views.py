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
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from loguru import logger


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
            .prefetch_related("messages", "offers")
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
            thread.messages.filter(is_read=False).exclude(sender=request.user).update(
                is_read=True
            )

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
                Message.objects.filter(thread_id=thread_id)
                .select_related("sender", "thread")
                .order_by("-created_at")
            )
        return Message.objects.select_related("sender", "thread").order_by(
            "-created_at"
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
                error_message={"message_ids": ["A non-empty list of message IDs is required."]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        marked_count = Message.objects.filter(
            id__in=message_ids,
            is_read=False,
        ).exclude(sender=request.user).update(is_read=True)

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
