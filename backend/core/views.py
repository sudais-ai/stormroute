from django.http import JsonResponse
from rest_framework.exceptions import ParseError
from rest_framework.views import APIView
from rest_framework.response import Response

from core.serializers import TripInputSerializer
from core.services.routing import ProviderError, generate_routes
from core.services.risk import analyze_route_risk
from stormroute.settings import APP_VERSION

TRIP_VALIDATED_MESSAGE = (
    "Trip inputs are valid and normalized. Route generation will be connected in a later phase — "
    "no routing, weather, or safety analysis has been performed yet."
)


class HealthView(APIView):
    """GET /api/health/ — foundation health endpoint.

    Returns service identity and version so the frontend status panel and
    deployment checks can distinguish "backend reachable" from "backend wrong".
    """

    def get(self, request):
        return JsonResponse(
            {
                "status": "ok",
                "service": "stormroute-backend",
                "version": APP_VERSION,
            }
        )


class _TripRequestMixin:
    """Shared malformed-JSON guard for POST trip endpoints.

    error_response_factory(parsing result) lets each endpoint keep its own
    public 400 shape (Phase 2 endpoint stays byte-for-byte compatible).
    """

    def parse_or_error(self, request, error_response_factory):
        try:
            return request.data, None
        except ParseError:
            return None, error_response_factory()


class TripValidateView(APIView, _TripRequestMixin):
    """POST /api/trips/validate/ — validates trip inputs only.

    Returns the normalized, timezone-aware departure timestamp and all
    validated/trimmed client values on success. Field-specific errors with
    HTTP 400 otherwise. Never persists anything and never touches routing or
    weather providers. Internal exceptions are not leaked to clients.
    """

    def post(self, request):
        data, error = self.parse_or_error(
            request,
            lambda: Response(
                {"valid": False, "errors": {"detail": ["Malformed JSON body — expected a valid trip object."]}},
                status=400,
            ),
        )
        if error:
            return error

        serializer = TripInputSerializer(data=data)
        if serializer.is_valid():
            return Response(
                {
                    "valid": True,
                    "trip": serializer.validated_data,
                    "message": TRIP_VALIDATED_MESSAGE,
                },
                status=200,
            )
        return Response({"valid": False, "errors": serializer.errors}, status=400)


class TripRoutesView(APIView, _TripRequestMixin):
    """POST /api/trips/routes/ — Phase 3 live route generation.

    Reuses TripInputSerializer so the Phase 2 input contract (validation
    messages, UTC normalization) is identical for both endpoints. On success
    returns the actual routes sent by Mapbox (1..3), geocoded endpoint
    details, per-route ETA and honest warning when fewer than three routes
    were received. Provider failures map to the safe codes defined in
    core.services.routing — the Mapbox token never appears in responses,
    messages, or logs.
    """

    def post(self, request):
        data, error = self.parse_or_error(
            request,
            lambda: Response(
                {
                    "routesAvailable": False,
                    "error": {"code": "malformed_request", "message": "Malformed JSON body — expected a valid trip object."},
                },
                status=400,
            ),
        )
        if error:
            return error

        serializer = TripInputSerializer(data=data)
        if not serializer.is_valid():
            return Response(
                {"routesAvailable": False, "inputErrors": serializer.errors},
                status=400,
            )

        try:
            result = generate_routes(serializer.validated_data)
        except ProviderError as provider_error:
            return Response(
                {"routesAvailable": False, "error": provider_error.as_payload()},
                status=provider_error.http_status,
            )

        return Response({"routesAvailable": True, **result}, status=200)
