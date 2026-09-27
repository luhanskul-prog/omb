from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.staff_access import role_permission_required

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
# MODEL CONFIGURATION
# =========================================================

MODEL_CONFIG = {

    "vehicle": {
        "model": Vehicle,
        "title": "Vehicles",
        "singular": "Vehicle",
        "permission": "vehicle",
        "list_url": "transport:vehicle_list",
        "add_url": "transport:vehicle_add",
        "edit_url": "transport:vehicle_edit",
        "delete_url": "transport:vehicle_delete",
        "fields": [
            "registration_number",
            "vehicle_name",
            "vehicle_type",
            "make",
            "model",
            "year",
            "capacity",
            "status",
            "insurance_expiry",
            "inspection_expiry",
            "notes",
        ],
        "columns": [
            "registration_number",
            "vehicle_name",
            "vehicle_type",
            "capacity",
            "status",
            "insurance_expiry",
            "inspection_expiry",
        ],
        "search_fields": [
            "registration_number",
            "vehicle_name",
            "make",
            "model",
        ],
    },

        "driver": {
        "model": Driver,
        "title": "Drivers",
        "singular": "Driver",
        "permission": "driver",
        "list_url": "transport:driver_list",
        "add_url": "transport:driver_add",
        "edit_url": "transport:driver_edit",
        "delete_url": "transport:driver_delete",
        "fields": [
            "employee",
            "licence_number",
            "licence_expiry",
            "status",
            "address",
            "notes",
        ],
        "columns": [
            "employee",
            "licence_number",
            "licence_expiry",
            "status",
        ],
        "search_fields": [
            "employee__first_name",
            "employee__last_name",
            "employee__phone",
            "employee__phone_number",
            "employee__national_id",
            "employee__id_number",
            "licence_number",
        ],
    },
"route": {
        "model": Route,
        "title": "Routes",
        "singular": "Route",
        "permission": "route",
        "list_url": "transport:route_list",
        "add_url": "transport:route_add",
        "edit_url": "transport:route_edit",
        "delete_url": "transport:route_delete",
        "fields": [
            "name",
            "code",
            "description",
            "morning_departure",
            "afternoon_departure",
            "status",
        ],
        "columns": [
            "code",
            "name",
            "morning_departure",
            "afternoon_departure",
            "status",
        ],
        "search_fields": [
            "name",
            "code",
            "description",
        ],
    },

    "routestop": {
        "model": RouteStop,
        "title": "Route Stops",
        "singular": "Route Stop",
        "permission": "routestop",
        "list_url": "transport:routestop_list",
        "add_url": "transport:routestop_add",
        "edit_url": "transport:routestop_edit",
        "delete_url": "transport:routestop_delete",
        "fields": [
            "route",
            "name",
            "location",
            "stop_order",
            "pickup_time",
            "dropoff_time",
            "is_active",
        ],
        "columns": [
            "route",
            "stop_order",
            "name",
            "location",
            "pickup_time",
            "dropoff_time",
            "is_active",
        ],
        "search_fields": [
            "name",
            "location",
            "route__name",
            "route__code",
        ],
    },

    "studenttransportassignment": {
        "model": StudentTransportAssignment,
        "title": "Student Transport Assignments",
        "singular": "Student Transport Assignment",
        "permission": "studenttransportassignment",
        "list_url": "transport:student_assignment_list",
        "add_url": "transport:student_assignment_add",
        "edit_url": "transport:student_assignment_edit",
        "delete_url": "transport:student_assignment_delete",
        "fields": [
            "student",
            "route",
            "pickup_stop",
            "dropoff_stop",
            "morning_transport",
            "afternoon_transport",
            "start_date",
            "end_date",
            "status",
            "notes",
        ],
        "columns": [
            "student",
            "route",
            "pickup_stop",
            "dropoff_stop",
            "morning_transport",
            "afternoon_transport",
            "start_date",
            "end_date",
            "status",
        ],
        "search_fields": [
            "student__first_name",
            "student__last_name",
            "student__admission_no",
            "route__name",
            "route__code",
        ],
    },

    "transportassignment": {
        "model": TransportAssignment,
        "title": "Vehicle / Driver Route Assignments",
        "singular": "Transport Assignment",
        "permission": "transportassignment",
        "list_url": "transport:assignment_list",
        "add_url": "transport:assignment_add",
        "edit_url": "transport:assignment_edit",
        "delete_url": "transport:assignment_delete",
        "fields": [
            "route",
            "vehicle",
            "driver",
            "start_date",
            "end_date",
            "status",
            "notes",
        ],
        "columns": [
            "route",
            "vehicle",
            "driver",
            "start_date",
            "end_date",
            "status",
        ],
        "search_fields": [
            "route__name",
            "route__code",
            "vehicle__registration_number",
            "driver__first_name",
            "driver__last_name",
        ],
    },

    "transporttrip": {
        "model": TransportTrip,
        "title": "Transport Trips",
        "singular": "Transport Trip",
        "permission": "transporttrip",
        "list_url": "transport:trip_list",
        "add_url": "transport:trip_add",
        "edit_url": "transport:trip_edit",
        "delete_url": "transport:trip_delete",
        "fields": [
            "date",
            "route",
            "vehicle",
            "driver",
            "trip_type",
            "departure_time",
            "arrival_time",
            "status",
            "notes",
        ],
        "columns": [
            "date",
            "route",
            "vehicle",
            "driver",
            "trip_type",
            "departure_time",
            "arrival_time",
            "status",
        ],
        "search_fields": [
            "route__name",
            "route__code",
            "vehicle__registration_number",
            "driver__first_name",
            "driver__last_name",
        ],
    },

    "vehiclemaintenance": {
        "model": VehicleMaintenance,
        "title": "Vehicle Maintenance",
        "singular": "Vehicle Maintenance Record",
        "permission": "vehiclemaintenance",
        "list_url": "transport:maintenance_list",
        "add_url": "transport:maintenance_add",
        "edit_url": "transport:maintenance_edit",
        "delete_url": "transport:maintenance_delete",
        "fields": [
            "vehicle",
            "maintenance_type",
            "date",
            "description",
            "service_provider",
            "cost",
            "next_service_date",
            "notes",
        ],
        "columns": [
            "vehicle",
            "maintenance_type",
            "date",
            "service_provider",
            "cost",
            "next_service_date",
        ],
        "search_fields": [
            "vehicle__registration_number",
            "service_provider",
            "description",
        ],
    },

    "fuelrecord": {
        "model": FuelRecord,
        "title": "Fuel Records",
        "singular": "Fuel Record",
        "permission": "fuelrecord",
        "list_url": "transport:fuel_list",
        "add_url": "transport:fuel_add",
        "edit_url": "transport:fuel_edit",
        "delete_url": "transport:fuel_delete",
        "fields": [
            "vehicle",
            "date",
            "litres",
            "cost",
            "odometer_reading",
            "fuel_station",
            "notes",
        ],
        "columns": [
            "vehicle",
            "date",
            "litres",
            "cost",
            "odometer_reading",
            "fuel_station",
        ],
        "search_fields": [
            "vehicle__registration_number",
            "fuel_station",
        ],
    },
}


# =========================================================
# FORM FACTORY
# =========================================================

def transport_form(_model, _fields):
    """
    Dynamic ModelForm factory for Transport.

    Driver identity comes from the HR Payroll Employee record.
    Transport only collects driver-specific transport information.
    """

    class TransportModelForm(forms.ModelForm):

        class Meta:
            model = _model
            fields = _fields

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            for name, field in self.fields.items():

                css = "transport-input"

                if isinstance(field.widget, forms.Textarea):
                    css = "transport-input transport-textarea"

                elif isinstance(
                    field.widget,
                    (
                        forms.Select,
                        forms.SelectMultiple,
                    ),
                ):
                    css = "transport-input transport-select"

                field.widget.attrs["class"] = css

                if field.label:
                    field.label = field.label.replace(
                        "_",
                        " ",
                    ).title()

            # -----------------------------------------------------
            # DRIVER EMPLOYEE SELECTOR
            # -----------------------------------------------------
            if "employee" in self.fields:

                self.fields["employee"].label = "HR Employee"

                self.fields["employee"].help_text = (
                    "Select an existing employee from HR Payroll. "
                    "Employee name, phone and identification details "
                    "are taken from the HR record."
                )

                employee_field = self.fields["employee"]

                try:
                    employees = employee_field.queryset

                    choices = [("", "---------")]

                    for employee in employees:

                        first_name = getattr(
                            employee,
                            "first_name",
                            "",
                        ) or ""

                        last_name = getattr(
                            employee,
                            "last_name",
                            "",
                        ) or ""

                        employee_number = (
                            getattr(
                                employee,
                                "employee_number",
                                None,
                            )
                            or getattr(
                                employee,
                                "staff_number",
                                None,
                            )
                            or ""
                        )

                        full_name = (
                            f"{first_name} {last_name}"
                        ).strip()

                        if employee_number:
                            label = (
                                f"{full_name} "
                                f"— {employee_number}"
                            )
                        else:
                            label = full_name

                        choices.append(
                            (
                                employee.pk,
                                label,
                            )
                        )

                    employee_field.choices = choices

                except Exception:
                    pass

    return TransportModelForm

def transport_dashboard(request):

    total_vehicles = Vehicle.objects.count()
    total_drivers = Driver.objects.count()
    total_routes = Route.objects.count()
    total_stops = RouteStop.objects.count()
    total_student_assignments = StudentTransportAssignment.objects.count()
    total_assignments = TransportAssignment.objects.count()
    total_trips = TransportTrip.objects.count()
    total_maintenance = VehicleMaintenance.objects.count()
    total_fuel_records = FuelRecord.objects.count()

    active_vehicles = Vehicle.objects.filter(
        status="ACTIVE"
    ).count()

    inactive_vehicles = Vehicle.objects.filter(
        status="INACTIVE"
    ).count()

    maintenance_vehicles = Vehicle.objects.filter(
        status="MAINTENANCE"
    ).count()

    vehicles = Vehicle.objects.all().order_by("-id")[:8]

    drivers = Driver.objects.all().order_by("-id")[:8]

    routes = Route.objects.all().order_by("-id")[:8]

    trips = (
        TransportTrip.objects
        .select_related("route", "vehicle", "driver")
        .order_by("-date", "-id")[:8]
    )

    fuel_records = (
        FuelRecord.objects
        .select_related("vehicle")
        .order_by("-date", "-id")[:8]
    )

    maintenance_records = (
        VehicleMaintenance.objects
        .select_related("vehicle")
        .order_by("-date", "-id")[:8]
    )

    context = {
        "total_vehicles": total_vehicles,
        "total_drivers": total_drivers,
        "total_routes": total_routes,
        "total_stops": total_stops,
        "total_student_assignments": total_student_assignments,
        "total_assignments": total_assignments,
        "total_trips": total_trips,
        "total_maintenance": total_maintenance,
        "total_fuel_records": total_fuel_records,

        "active_vehicles": active_vehicles,
        "inactive_vehicles": inactive_vehicles,
        "maintenance_vehicles": maintenance_vehicles,

        "vehicles": vehicles,
        "drivers": drivers,
        "routes": routes,
        "trips": trips,
        "fuel_records": fuel_records,
        "maintenance_records": maintenance_records,
    }

    return render(
        request,
        "transport/transport_dashboard.html",
        context,
    )


# =========================================================
# GENERIC LIST
# =========================================================

def _transport_list(request, key):

    config = MODEL_CONFIG[key]
    model = config["model"]

    queryset = model.objects.all()

    search = request.GET.get("q", "").strip()

    if search:
        query = Q()

        for field in config["search_fields"]:
            query |= Q(**{f"{field}__icontains": search})

        queryset = queryset.filter(query)

    queryset = queryset.order_by("-id")

    rows = []

    for obj in queryset:

        values = []

        for field_name in config["columns"]:

            field = model._meta.get_field(field_name)

            if hasattr(obj, f"get_{field_name}_display"):
                value = getattr(
                    obj,
                    f"get_{field_name}_display"
                )()

            else:
                value = getattr(
                    obj,
                    field_name,
                    "",
                )

            if value is None:
                value = ""

            values.append(value)

        rows.append({
            "object": obj,
            "values": values,
        })

    context = {
        "title": config["title"],
        "singular": config["singular"],
        "columns": config["columns"],
        "rows": rows,
        "search": search,
        "config": config,
        "add_permission": f"add_{config['permission']}",
        "change_permission": f"change_{config['permission']}",
        "delete_permission": f"delete_{config['permission']}",
    }

    return render(
        request,
        "transport/model_list.html",
        context,
    )


# =========================================================
# GENERIC ADD
# =========================================================

def _transport_add(request, key):

    config = MODEL_CONFIG[key]

    FormClass = transport_form(
        config["model"],
        config["fields"],
    )

    if request.method == "POST":

        form = FormClass(request.POST)

        if form.is_valid():

            obj = form.save()

            messages.success(
                request,
                f"{config['singular']} created successfully.",
            )

            return redirect(config["list_url"])

    else:
        form = FormClass()

    return render(
        request,
        "transport/model_form.html",
        {
            "form": form,
            "title": f"Add {config['singular']}",
            "singular": config["singular"],
            "config": config,
        },
    )


# =========================================================
# GENERIC EDIT
# =========================================================

def _transport_edit(request, key, pk):

    config = MODEL_CONFIG[key]

    obj = get_object_or_404(
        config["model"],
        pk=pk,
    )

    FormClass = transport_form(
        config["model"],
        config["fields"],
    )

    if request.method == "POST":

        form = FormClass(
            request.POST,
            instance=obj,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                f"{config['singular']} updated successfully.",
            )

            return redirect(config["list_url"])

    else:
        form = FormClass(instance=obj)

    return render(
        request,
        "transport/model_form.html",
        {
            "form": form,
            "title": f"Edit {config['singular']}",
            "singular": config["singular"],
            "config": config,
            "object": obj,
        },
    )


# =========================================================
# GENERIC DELETE
# =========================================================

def _transport_delete(request, key, pk):

    config = MODEL_CONFIG[key]

    obj = get_object_or_404(
        config["model"],
        pk=pk,
    )

    if request.method == "POST":

        obj.delete()

        messages.success(
            request,
            f"{config['singular']} deleted successfully.",
        )

        return redirect(config["list_url"])

    return render(
        request,
        "transport/model_confirm_delete.html",
        {
            "object": obj,
            "title": f"Delete {config['singular']}",
            "singular": config["singular"],
            "config": config,
        },
    )


# =========================================================
# VEHICLES
# =========================================================

@login_required
@role_permission_required("view_vehicle", "transport")
def vehicle_list(request):
    return _transport_list(request, "vehicle")


@login_required
@role_permission_required("add_vehicle", "transport")
def vehicle_add(request):
    return _transport_add(request, "vehicle")


@login_required
@role_permission_required("change_vehicle", "transport")
def vehicle_edit(request, pk):
    return _transport_edit(request, "vehicle", pk)


@login_required
@role_permission_required("delete_vehicle", "transport")
def vehicle_delete(request, pk):
    return _transport_delete(request, "vehicle", pk)


# =========================================================
# DRIVERS
# =========================================================

@login_required
@role_permission_required("view_driver", "transport")
def driver_list(request):
    return _transport_list(request, "driver")


@login_required
@role_permission_required("add_driver", "transport")
def driver_add(request):
    return _transport_add(request, "driver")


@login_required
@role_permission_required("change_driver", "transport")
def driver_edit(request, pk):
    return _transport_edit(request, "driver", pk)


@login_required
@role_permission_required("delete_driver", "transport")
def driver_delete(request, pk):
    return _transport_delete(request, "driver", pk)


# =========================================================
# ROUTES
# =========================================================

@login_required
@role_permission_required("view_route", "transport")
def route_list(request):
    return _transport_list(request, "route")


@login_required
@role_permission_required("add_route", "transport")
def route_add(request):
    return _transport_add(request, "route")


@login_required
@role_permission_required("change_route", "transport")
def route_edit(request, pk):
    return _transport_edit(request, "route", pk)


@login_required
@role_permission_required("delete_route", "transport")
def route_delete(request, pk):
    return _transport_delete(request, "route", pk)


# =========================================================
# ROUTE STOPS
# =========================================================

@login_required
@role_permission_required("view_routestop", "transport")
def routestop_list(request):
    return _transport_list(request, "routestop")


@login_required
@role_permission_required("add_routestop", "transport")
def routestop_add(request):
    return _transport_add(request, "routestop")


@login_required
@role_permission_required("change_routestop", "transport")
def routestop_edit(request, pk):
    return _transport_edit(request, "routestop", pk)


@login_required
@role_permission_required("delete_routestop", "transport")
def routestop_delete(request, pk):
    return _transport_delete(request, "routestop", pk)


# =========================================================
# STUDENT TRANSPORT ASSIGNMENTS
# =========================================================

@login_required
@role_permission_required(
    "view_studenttransportassignment",
    "transport",
)
def student_assignment_list(request):
    return _transport_list(
        request,
        "studenttransportassignment",
    )


@login_required
@role_permission_required(
    "add_studenttransportassignment",
    "transport",
)
def student_assignment_add(request):
    return _transport_add(
        request,
        "studenttransportassignment",
    )


@login_required
@role_permission_required(
    "change_studenttransportassignment",
    "transport",
)
def student_assignment_edit(request, pk):
    return _transport_edit(
        request,
        "studenttransportassignment",
        pk,
    )


@login_required
@role_permission_required(
    "delete_studenttransportassignment",
    "transport",
)
def student_assignment_delete(request, pk):
    return _transport_delete(
        request,
        "studenttransportassignment",
        pk,
    )


# =========================================================
# VEHICLE / DRIVER ROUTE ASSIGNMENTS
# =========================================================

@login_required
@role_permission_required(
    "view_transportassignment",
    "transport",
)
def assignment_list(request):
    return _transport_list(
        request,
        "transportassignment",
    )


@login_required
@role_permission_required(
    "add_transportassignment",
    "transport",
)
def assignment_add(request):
    return _transport_add(
        request,
        "transportassignment",
    )


@login_required
@role_permission_required(
    "change_transportassignment",
    "transport",
)
def assignment_edit(request, pk):
    return _transport_edit(
        request,
        "transportassignment",
        pk,
    )


@login_required
@role_permission_required(
    "delete_transportassignment",
    "transport",
)
def assignment_delete(request, pk):
    return _transport_delete(
        request,
        "transportassignment",
        pk,
    )


# =========================================================
# TRANSPORT TRIPS
# =========================================================

@login_required
@role_permission_required(
    "view_transporttrip",
    "transport",
)
def trip_list(request):
    return _transport_list(
        request,
        "transporttrip",
    )


@login_required
@role_permission_required(
    "add_transporttrip",
    "transport",
)
def trip_add(request):
    return _transport_add(
        request,
        "transporttrip",
    )


@login_required
@role_permission_required(
    "change_transporttrip",
    "transport",
)
def trip_edit(request, pk):
    return _transport_edit(
        request,
        "transporttrip",
        pk,
    )


@login_required
@role_permission_required(
    "delete_transporttrip",
    "transport",
)
def trip_delete(request, pk):
    return _transport_delete(
        request,
        "transporttrip",
        pk,
    )


# =========================================================
# VEHICLE MAINTENANCE
# =========================================================

@login_required
@role_permission_required(
    "view_vehiclemaintenance",
    "transport",
)
def maintenance_list(request):
    return _transport_list(
        request,
        "vehiclemaintenance",
    )


@login_required
@role_permission_required(
    "add_vehiclemaintenance",
    "transport",
)
def maintenance_add(request):
    return _transport_add(
        request,
        "vehiclemaintenance",
    )


@login_required
@role_permission_required(
    "change_vehiclemaintenance",
    "transport",
)
def maintenance_edit(request, pk):
    return _transport_edit(
        request,
        "vehiclemaintenance",
        pk,
    )


@login_required
@role_permission_required(
    "delete_vehiclemaintenance",
    "transport",
)
def maintenance_delete(request, pk):
    return _transport_delete(
        request,
        "vehiclemaintenance",
        pk,
    )


# =========================================================
# FUEL RECORDS
# =========================================================

@login_required
@role_permission_required(
    "view_fuelrecord",
    "transport",
)
def fuel_list(request):
    return _transport_list(
        request,
        "fuelrecord",
    )


@login_required
@role_permission_required(
    "add_fuelrecord",
    "transport",
)
def fuel_add(request):
    return _transport_add(
        request,
        "fuelrecord",
    )


@login_required
@role_permission_required(
    "change_fuelrecord",
    "transport",
)
def fuel_edit(request, pk):
    return _transport_edit(
        request,
        "fuelrecord",
        pk,
    )


@login_required
@role_permission_required(
    "delete_fuelrecord",
    "transport",
)
def fuel_delete(request, pk):
    return _transport_delete(
        request,
        "fuelrecord",
        pk,
    )



