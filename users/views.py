from django.db.models import QuerySet
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import serializers, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import UserSerializer
from .utils.filters import apply_filters


@extend_schema_view(
    get=extend_schema(
        responses={
            200: UserSerializer(many=True),
        },
        parameters=[
            OpenApiParameter(
                name="name",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter users by name. Partial match.",
            ),
            OpenApiParameter(
                name="email",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter users by email. Partial match.",
            ),
            OpenApiParameter(
                name="code",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter users by code.",
            ),
            OpenApiParameter(
                name="is_active",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter users by active status.",
            ),
            OpenApiParameter(
                name="min_age",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Minimum user age.",
            ),
            OpenApiParameter(
                name="max_age ",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Maximum user age.",
            ),
        ],
    ),
    post=extend_schema(
        request=UserSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Invalid user data"),
        },
    ),
)
class UserListView(ListCreateAPIView[User]):
    serializer_class = UserSerializer

    def get_queryset(self) -> QuerySet[User]:
        filter_config = {
            "name": {
                "lookup": "icontains",
            },
            "email": {
                "lookup": "icontains",
            },
            "code": {
                "lookup": "icontains",
            },
            "min_age": {
                "field": "age",
                "lookup": "gte",
            },
            "max_age": {
                "field": "age",
                "lookup": "lte",
            },
        }

        return apply_filters(
            model=User,
            filters=self.request.query_params,
            config=filter_config,
        )
        


@extend_schema_view(
    get=extend_schema(
        responses={
            200: UserSerializer,
            404: OpenApiResponse(description="User code not found"),
        }
    ),
    patch=extend_schema(
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Invalid user data"),
            404: OpenApiResponse(description="User not found"),
        },
    ),
    delete=extend_schema(
        responses={
            204: OpenApiResponse(description="User deleted successfully"),
            404: OpenApiResponse(description="User not found"),
        },
    ),
)
class UserDetailView(RetrieveUpdateDestroyAPIView[User]):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    lookup_field = "code"
    lookup_url_kwarg = "code_param"

    http_method_names = (
        "get",
        "patch",
        "delete",
        "head",
        "options",
    )


class UserBulkView(APIView):
    @extend_schema(
        request=UserSerializer(many=True),
        responses=UserSerializer(many=True),
    )
    def post(self, request: Request) -> Response:
        serializer = UserSerializer(
            data=request.data,
            many=True,
        )

        serializer.is_valid(raise_exception=True)

        users = [User(**user_data) for user_data in serializer.validated_data]

        created_users = User.objects.bulk_create(users)

        response_serializer = UserSerializer(
            instance=created_users,
            many=True,
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=UserSerializer(many=True),
        responses={
            200: UserSerializer(many=True),
            400: OpenApiResponse(description="Invalid user data"),
            404: OpenApiResponse(description="User not found"),
        },
    )
    def patch(self, request: Request) -> Response:
        request_data: list[dict] = request.data

        codes: list[str] = []
        users_without_codes: list[dict] = []

        for index, user_data in enumerate(request_data):
            if "code" not in user_data:
                raise serializers.ValidationError(
                    {index: {"code": "This field is required."}}
                )

            codes.append(user_data["code"])

            user_without_code = user_data.copy()
            user_without_code.pop("code")

            users_without_codes.append(user_without_code)

        serialized = UserSerializer(
            data=users_without_codes,
            many=True,
            partial=True,
        )

        serialized.is_valid(raise_exception=True)

        query_data = User.objects.filter(code__in=codes)

        users_by_code: dict[str, User] = {}

        for user in query_data:
            users_by_code[user.code] = user

        for index, user_data in enumerate(request_data):
            code = user_data["code"]

            if code not in users_by_code:
                raise serializers.ValidationError(
                    {index: {"code": f"User with code '{code}' does not exist."}}
                )

        users_to_update: list[User] = []

        for code, update_data in zip(
            codes,
            serialized.validated_data,
        ):
            user = users_by_code[code]

            for field, value in update_data.items():
                setattr(user, field, value)

            users_to_update.append(user)

        User.objects.bulk_update(
            users_to_update,
            fields=[
                "name",
                "last_name",
                "age",
                "email",
                "is_active",
            ],
        )

        response_serializer = UserSerializer(
            instance=users_to_update,
            many=True,
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="codes",
                type={"type": "array", "items": {"type": "string"}},
                location=OpenApiParameter.QUERY,
                required=True,
                description="User codes to delete.",
            ),
        ],
        responses=None,
    )
    def delete(self, request: Request) -> Response:
        codes = request.query_params.getlist("codes")

        query_data = User.objects.filter(
            code__in=codes,
        )

        existing_codes = set(query_data.values_list("code", flat=True))

        requested_codes = set(codes)

        missing_codes = requested_codes - existing_codes

        if missing_codes:
            raise serializers.ValidationError(
                {"codes": f"Users not found: {', '.join(sorted(missing_codes))}"}
            )

        query_data.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )