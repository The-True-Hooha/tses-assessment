import os

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
                "docs": "/api/v1/docs/",
                "health": "/health/",
            },
        }
    )

urlpatterns = [
    path(os.environ.get("DJANGO_ADMIN_URL", "admin/"), admin.site.urls),

    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/audit/", include("audit.urls")),

    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    path("", index, name="index"),
    
    path("", include("core.health_urls")),
]
