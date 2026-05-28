from django.shortcuts import render
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Prefetch
from recycle.models import ScrapCategory, ScrapRequest, ScrapOffer, SavedScrapRequest
from recycle.serializers import (
    ScrapCategorySerializer,
    ScrapRequestSerializer,
    RecyclerScrapRequestSerializer,
    ScrapOfferSerializer,
    RecyclerAcceptedScrapRequestSerializer,
    SavedScrapRequestSerializer,
)
from recycle.filters import ScrapRequestFilter
from ecoLoop.utils import api_response
from ecoLoop.mail import send_scrap_status_update
from accounts.permissions import IsRecycler

# Create your views here.


class ScrapCategoryViewSet(viewsets.ModelViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]
    queryset = ScrapCategory.objects.all()
    serializer_class = ScrapCategorySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


class ScrapRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ScrapRequestSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filterset_class = ScrapRequestFilter

    def get_queryset(self):
        # Users can only see their own scrap requests
        return (
            ScrapRequest.objects.filter(user=self.request.user)
            .prefetch_related("images")
            .select_related("category")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            result = {
                "count": getattr(self.paginator.page.paginator, "count", len(data)),
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "results": data,
            }
            return api_response(
                result=result,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        data = self.get_serializer(queryset, many=True).data
        return api_response(
            result=data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Set the user to the authenticated user
        serializer.save(user=request.user)

        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )


class RecyclerScrapRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Recycler users to view all pending scrap requests.
    Recyclers can list and retrieve pending scrap requests but cannot modify them.
    Supports filtering by category, condition, and weight range.
    """

    permission_classes = [IsAuthenticated, IsRecycler]
    serializer_class = RecyclerScrapRequestSerializer
    filterset_class = ScrapRequestFilter

    def get_queryset(self):
        # Recycler can see all pending scrap requests that are not yet accepted
        saved_prefetch = Prefetch(
            "saved_by",
            queryset=SavedScrapRequest.objects.filter(user=self.request.user),
            to_attr="user_saved",
        )
        return (
            ScrapRequest.objects.filter(status="pending", accepted_by__isnull=True)
            .prefetch_related("images", saved_prefetch)
            .select_related("category", "user", "accepted_by")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            result = {
                "count": getattr(self.paginator.page.paginator, "count", len(data)),
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "results": data,
            }
            return api_response(
                result=result,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        data = self.get_serializer(queryset, many=True).data
        return api_response(
            result=data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="accept")
    def accept_request(self, request, pk=None):
        """
        Recycler accepts a scrap request and creates an offer.
        This changes the request status to 'accepted' and creates a scrap offer.

        """

        # Get the scrap request without status filter to check if it exists
        try:
            scrap_request = ScrapRequest.objects.get(id=pk)
        except ScrapRequest.DoesNotExist:
            return api_response(
                result=None,
                is_success=False,
                error_message="Scrap request not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Check if request is still pending
        if scrap_request.status != "pending":
            return api_response(
                result=None,
                is_success=False,
                error_message=f"Cannot accept request with status: {scrap_request.status}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Create the offer
        offer_serializer = ScrapOfferSerializer(data=request.data)
        if not offer_serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=offer_serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Update request status
        scrap_request.status = "accepted"
        scrap_request.accepted_by = request.user
        scrap_request.save()

        send_scrap_status_update(
            scrap_request.user.email,
            scrap_request.user.full_name,
            "accepted",
        )

        # Save the offer
        offer = offer_serializer.save(
            recycler=request.user, scrap_request=scrap_request
        )

        return api_response(
            result={
                "message": "Scrap request accepted successfully",
                "offer": ScrapOfferSerializer(offer).data,
                "request": RecyclerScrapRequestSerializer(scrap_request).data,
            },
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post", "delete"], url_path="save")
    def save_request(self, request, pk=None):
        scrap_request = self.get_object()

        if request.method == "POST":
            SavedScrapRequest.objects.get_or_create(
                user=request.user, scrap_request=scrap_request
            )
            return api_response(
                result={"is_saved": True},
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        SavedScrapRequest.objects.filter(
            user=request.user, scrap_request=scrap_request
        ).delete()
        return api_response(
            result={"is_saved": False},
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


class SavedRecyclerScrapRequestViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsRecycler]
    serializer_class = SavedScrapRequestSerializer

    def get_queryset(self):
        return (
            SavedScrapRequest.objects.filter(user=self.request.user)
            .select_related(
                "scrap_request",
                "scrap_request__user",
                "scrap_request__category",
            )
            .prefetch_related("scrap_request__images")
            .order_by("-created_at")
        )


class RecyclerAcceptedScrapRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Recycler users to view accepted scrap requests.
    Recyclers can list and retrieve accepted scrap requests with offer details.
    Supports filtering by category, condition, and weight range.
    """

    permission_classes = [IsAuthenticated, IsRecycler]
    serializer_class = RecyclerAcceptedScrapRequestSerializer
    filterset_class = ScrapRequestFilter

    def get_queryset(self):
        # Recycler can only see scrap requests accepted by themselves
        return (
            ScrapRequest.objects.filter(
                status="accepted",
                accepted_by=self.request.user,
            )
            .prefetch_related("images", "recycler_offers")
            .select_related("category", "user", "accepted_by")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            result = {
                "count": getattr(self.paginator.page.paginator, "count", len(data)),
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "results": data,
            }
            return api_response(
                result=result,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        data = self.get_serializer(queryset, many=True).data
        return api_response(
            result=data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_request(self, request, pk=None):
        """
        Recycler marks an accepted scrap request as completed.
        Also marks recycler's related offers for that request as completed.
        """
        scrap_request = self.get_object()

        if scrap_request.status != "accepted":
            return api_response(
                result=None,
                is_success=False,
                error_message=f"Cannot complete request with status: {scrap_request.status}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        scrap_request.status = "completed"
        scrap_request.save(update_fields=["status"])

        send_scrap_status_update(
            scrap_request.user.email,
            scrap_request.user.full_name,
            "completed",
        )

        ScrapOffer.objects.filter(
            scrap_request=scrap_request,
            recycler=request.user,
        ).exclude(status="completed").update(status="completed")

        return api_response(
            result={
                "message": "Scrap request marked as completed",
                "request": RecyclerAcceptedScrapRequestSerializer(scrap_request).data,
            },
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


class RecyclerCompletedScrapRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Recycler users to view completed scrap requests.
    Recyclers can list and retrieve completed scrap requests with offer details.
    Supports filtering by category, condition, and weight range.
    """

    permission_classes = [IsAuthenticated, IsRecycler]
    serializer_class = RecyclerAcceptedScrapRequestSerializer
    filterset_class = ScrapRequestFilter

    def get_queryset(self):
        # Recycler can only see completed scrap requests accepted by themselves
        return (
            ScrapRequest.objects.filter(
                status="completed", accepted_by=self.request.user
            )
            .prefetch_related("images", "recycler_offers")
            .select_related("category", "user", "accepted_by")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            result = {
                "count": getattr(self.paginator.page.paginator, "count", len(data)),
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "results": data,
            }
            return api_response(
                result=result,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        data = self.get_serializer(queryset, many=True).data
        return api_response(
            result=data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )
