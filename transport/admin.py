from django.contrib import admin

from .models import (
    Vehicle,
    Driver,
    Route,
    RouteStop,
    StudentTransportAssignment,
    TransportAssignment,
    TransportTrip,
    VehicleMaintenance,
    FuelRecord,
)


# =========================================================
# VEHICLES
# =========================================================

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):

    list_display = (
        "registration_number",
        "vehicle_name",
        "vehicle_type",
        "capacity",
        "status",
        "insurance_expiry",
        "inspection_expiry",
    )

    list_filter = (
        "vehicle_type",
        "status",
    )

    search_fields = (
        "registration_number",
        "vehicle_name",
        "make",
        "model",
    )


# =========================================================
# DRIVERS
# =========================================================

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):

    list_display = (
        "full_name",
        "phone",
        "licence_number",
        "licence_expiry",
        "status",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "first_name",
        "last_name",
        "phone",
        "national_id",
        "licence_number",
    )


# =========================================================
# ROUTES
# =========================================================

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "morning_departure",
        "afternoon_departure",
        "status",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "name",
        "code",
    )


# =========================================================
# ROUTE STOPS
# =========================================================

@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):

    list_display = (
        "route",
        "stop_order",
        "name",
        "location",
        "pickup_time",
        "dropoff_time",
        "is_active",
    )

    list_filter = (
        "route",
        "is_active",
    )

    search_fields = (
        "name",
        "location",
        "route__name",
        "route__code",
    )


# =========================================================
# STUDENT TRANSPORT ASSIGNMENTS
# =========================================================

@admin.register(StudentTransportAssignment)
class StudentTransportAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "route",
        "pickup_stop",
        "dropoff_stop",
        "morning_transport",
        "afternoon_transport",
        "status",
        "start_date",
        "end_date",
    )

    list_filter = (
        "status",
        "morning_transport",
        "afternoon_transport",
        "route",
    )

    search_fields = (
        "student__first_name",
        "student__last_name",
        "student__admission_no",
        "route__name",
        "route__code",
    )


# =========================================================
# VEHICLE / DRIVER ROUTE ASSIGNMENTS
# =========================================================

@admin.register(TransportAssignment)
class TransportAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "route",
        "vehicle",
        "driver",
        "start_date",
        "end_date",
        "status",
    )

    list_filter = (
        "status",
        "route",
        "vehicle",
        "driver",
    )

    search_fields = (
        "route__name",
        "route__code",
        "vehicle__registration_number",
        "driver__first_name",
        "driver__last_name",
    )


# =========================================================
# DAILY TRANSPORT TRIPS
# =========================================================

@admin.register(TransportTrip)
class TransportTripAdmin(admin.ModelAdmin):

    list_display = (
        "date",
        "route",
        "vehicle",
        "driver",
        "trip_type",
        "departure_time",
        "arrival_time",
        "status",
    )

    list_filter = (
        "status",
        "trip_type",
        "route",
        "vehicle",
        "driver",
    )

    search_fields = (
        "route__name",
        "route__code",
        "vehicle__registration_number",
        "driver__first_name",
        "driver__last_name",
    )


# =========================================================
# VEHICLE MAINTENANCE
# =========================================================

@admin.register(VehicleMaintenance)
class VehicleMaintenanceAdmin(admin.ModelAdmin):

    list_display = (
        "vehicle",
        "maintenance_type",
        "date",
        "service_provider",
        "cost",
        "next_service_date",
    )

    list_filter = (
        "maintenance_type",
        "vehicle",
    )

    search_fields = (
        "vehicle__registration_number",
        "service_provider",
        "description",
    )


# =========================================================
# FUEL RECORDS
# =========================================================

@admin.register(FuelRecord)
class FuelRecordAdmin(admin.ModelAdmin):

    list_display = (
        "vehicle",
        "date",
        "litres",
        "cost",
        "odometer_reading",
        "fuel_station",
    )

    list_filter = (
        "vehicle",
        "date",
    )

    search_fields = (
        "vehicle__registration_number",
        "fuel_station",
    )