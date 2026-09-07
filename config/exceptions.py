from typing import Any

#from django.db.models.deletion import ProtectedError
#from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response | None:        
    return exception_handler(exc, context)
    