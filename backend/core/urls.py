from django.urls import path

from core.views import HealthView, TripRoutesView, TripValidateView

app_name = "core"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("trips/validate/", TripValidateView.as_view(), name="trip_validate"),
    path("trips/routes/", TripRoutesView.as_view(), name="trip_routes"),
]
