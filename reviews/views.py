from django.db.models import Avg, Count
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated

from ecoLoop.utils import api_response
from .models import Review
from .serializers import ReviewSerializer


class ReviewPagination(PageNumberPagination):
    page_size = 10


class ReviewViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReviewSerializer
    queryset = Review.objects.select_related(
        "reviewer", "reviewer__profile", "reviewee"
    )
    pagination_class = ReviewPagination
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "summary"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return api_response(
                result=None,
                is_success=False,
                error_message={"user_id": ["This query parameter is required."]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.filter_queryset(self.get_queryset().filter(reviewee_id=user_id))
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(reviewer=request.user)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.reviewer_id != request.user.id:
            return api_response(
                result=None,
                is_success=False,
                error_message=["You can only edit your own review."],
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        self.perform_update(serializer)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def summary(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return api_response(
                result=None,
                is_success=False,
                error_message={"user_id": ["This query parameter is required."]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Review.objects.filter(reviewee_id=user_id)
        aggregate = queryset.aggregate(
            average_rating=Avg("rating"), total_count=Count("id")
        )

        breakdown = {str(star): 0 for star in range(1, 6)}
        counts = queryset.values("rating").annotate(total=Count("id"))
        for item in counts:
            breakdown[str(item["rating"])] = item["total"]

        result = {
            "average_rating": aggregate["average_rating"],
            "total_count": aggregate["total_count"],
            "breakdown": breakdown,
        }
        return api_response(
            result=result,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def can_review(self, request):
        reviewee_id = request.query_params.get("reviewee_id")
        if not reviewee_id:
            return api_response(
                result=None,
                is_success=False,
                error_message={"reviewee_id": ["This query parameter is required."]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        existing_review = (
            Review.objects.filter(
                reviewer=request.user,
                reviewee_id=reviewee_id,
            )
            .only("id")
            .first()
        )

        result = {
            "can_review": str(request.user.id) != str(reviewee_id),
            "already_reviewed": existing_review is not None,
            "existing_review_id": str(existing_review.id) if existing_review else None,
        }
        return api_response(
            result=result,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )
