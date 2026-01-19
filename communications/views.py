from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import PageNumberPagination

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)

from communications.serializers import (
    ThreadSerializer,
    MessageSerializer,
    ThreadDetailSerializer,
)
from communications.models import Thread, Message
from ecoLoop.utils import api_response
from django.db.models import Q

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
    """
    API endpoint for managing chat threads.
    - GET /api/communications/threads/ - List all threads for authenticated user
    - POST /api/communications/threads/ - Create new thread
    - GET /api/communications/threads/{id}/ - Get thread with all messages
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = ThreadSerializer
    lookup_field = "id"

    def get_queryset(self):
        """Get threads where the user is either user1 or user2"""
        user = self.request.user
        return (
            Thread.objects.filter(Q(user1=user) | Q(user2=user))
            .select_related("user1", "user2")
            .prefetch_related("messages")
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
    """
    API endpoint for managing messages.
    - GET /api/communications/messages/?thread_id=1 - List messages in thread (paginated)
    - POST /api/communications/messages/ - Send message
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = MessageSerializer
    pagination_class = PageNumberPagination

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
