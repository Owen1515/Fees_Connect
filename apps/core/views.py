"""Public website, liveness/readiness and styled error handlers."""

from typing import Any

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def healthz(request: HttpRequest) -> Any:
    """Cheap process liveness endpoint; does not expose configuration."""
    return JsonResponse({"status": "ok"})


@require_GET
def readyz(request: HttpRequest) -> Any:
    """Check database and cache availability before routing traffic."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        cache.set("readiness", "ok", 10)
        if cache.get("readiness") != "ok":
            raise RuntimeError
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})


def error403(request: HttpRequest, exception: Any = None) -> Any:
    """Render a permission error without leaking object details."""
    return render(request, "errors/403.html", status=403)


def error404(request: HttpRequest, exception: Any = None) -> Any:
    """Render an unavailable-resource page."""
    return render(request, "errors/404.html", status=404)


def error500(request: HttpRequest) -> Any:
    """Render a stable server-error page without exception internals."""
    return render(request, "errors/500.html", status=500)
