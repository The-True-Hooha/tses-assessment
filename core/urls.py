from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def index(request):
    return JsonResponse(
        {
            "status_code": 200,
            "message": "TSES OTP Authentication API",
            "data": {
                "docs": "/api/docs/",
                "health": "/health/",
            },
        }
    )

urlpatterns = [
    path("admin/", admin.site.urls),

    # Apps
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/audit/", include("audit.urls")),

    # OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Index
    path("", index, name="index"),

    # Health
    path("", include("core.health_urls")),
]
