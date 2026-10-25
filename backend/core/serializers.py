from datetime import datetime, timezone as dt_timezone

from rest_framework import serializers


ALLOWED_CHECKPOINT_INTERVAL_MILES = (10, 25, 50)


class TripInputSerializer(serializers.Serializer):
    """Validation boundary for trip-input requests (Phase 2).

    This validates and normalizes user input only. It generates no routes, no
    weather analysis, and persists nothing. Routing/weather arrive in later
    phases and MUST reuse this serializer as the canonical input boundary.
    """

    origin = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=200,
        error_messages={
            "required": "Origin is required.",
            "blank": "Origin must contain some text — please enter a starting location.",
        },
        help_text="Free-text place or address. Coordinates are never asked of the user.",
    )
    destination = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=200,
        error_messages={
            "required": "Destination is required.",
            "blank": "Destination must contain some text — please enter where the trip ends.",
        },
        help_text="Free-text place or address.",
    )
    departureISO = serializers.CharField(
        required=True,
        trim_whitespace=False,
        error_messages={
            "required": "Departure date and time is required.",
        },
        help_text=(
            "ISO 8601 timestamp WITH timezone offset (e.g. 2026-11-01T08:30:00-05:00). "
            "The client converts the user's local time; this API re-derives and re-checks it."
        ),
    )
    loadWeightLb = serializers.FloatField(
        required=True,
        allow_null=False,
        error_messages={
            "required": "Load weight is required.",
            "null": "Load weight is required.",
            "invalid": "Load weight must be a number (in pounds).",
        },
        help_text="Cargo weight in pounds; 0 is valid (empty cargo). Negative rejected. No invented maximum.",
    )
    # Spec: intervals may be 10/25/50 miles; the default is 25.
    checkpointIntervalMiles = serializers.ChoiceField(
        choices=ALLOWED_CHECKPOINT_INTERVAL_MILES,
        required=False,
        default=25,
        error_messages={
            "invalid_choice": "Sampling interval must be one of: 10, 25, or 50 miles.",
        },
        help_text="How often (in miles) the route is sampled for weather analysis.",
    )

    def validate_departureISO(self, value: str) -> str:
        try:
            departure = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            raise serializers.ValidationError("Departure must be a valid date and time (ISO 8601 format).")
        if departure.tzinfo is None or departure.tzinfo.utcoffset(departure) is None:
            raise serializers.ValidationError("Departure timestamp must include its timezone (checked on the client's local clock).")
        # Compare against the server's timezone-aware now. Tests deliberately use
        # +/- margins so wall-clock races never make expectations brittle.
        from django.utils import timezone as dj_timezone

        now = dj_timezone.now()
        if departure < now:
            raise serializers.ValidationError("Departure time is in the past — choose a future date and time.")
        return departure.astimezone(dt_timezone.utc).isoformat()

    def validate_loadWeightLb(self, value: float) -> float:
        import math

        if not math.isfinite(value):
            raise serializers.ValidationError("Load weight must be a finite number (no Infinity or NaN).")
        if value < 0:
            raise serializers.ValidationError("Load weight must not be negative — enter 0 (empty) or more pounds.")
        return value

    def validate(self, data: dict) -> dict:
        origin = data.get("origin", "")
        destination = data.get("destination", "")
        if origin and destination and origin == destination:
            raise serializers.ValidationError(
                {"destination": "Destination must differ from the origin — pick where the trip actually ends."}
            )
        return data
