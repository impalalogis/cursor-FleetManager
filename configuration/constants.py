from django.db import models
from django.utils.translation import gettext_lazy as _


class ChoiceCategory(models.TextChoices):
    LOCATION_STATE = "LOCATION_STATE", _("Location State")
    PERSON_GENDER = "PERSON_GENDER", _("Person Gender")
    PERSON_TITLE = "PERSON_TITLE", _("Person Title")

    VEHICLE_BRAND = "VEHICLE_BRAND", _("Vehicle Brand")
    VEHICLE_MODEL = "VEHICLE_MODEL", _("Vehicle Model")
    VEHICLE_WHEEL_CONFIGURATION = "VEHICLE_WHEEL_CONFIGURATION", _("Vehicle Wheel Configuration")
    VEHICLE_FUEL_TYPE = "VEHICLE_FUEL_TYPE", _("Vehicle Fuel Type")
    VEHICLE_TRUCK_TYPE = "VEHICLE_TRUCK_TYPE", _("Vehicle Truck Type")
    VEHICLE_ENGINE_TYPE = "VEHICLE_ENGINE_TYPE", _("Vehicle Engine Type")
    VEHICLE_BODY_TYPE = "VEHICLE_BODY_TYPE", _("Vehicle Body Type")
    VEHICLE_CAPACITY_TONNAGE = "VEHICLE_CAPACITY_TONNAGE", _("Vehicle Capacity (Tonnage)")
    VEHICLE_SPECIFICATION = "VEHICLE_SPECIFICATION", _("Vehicle Specification")
    VEHICLE_DOCUMENT_TYPE = "VEHICLE_DOCUMENT_TYPE", _("Vehicle Document Type")

    DRIVER_DOCUMENT_TYPE = "DRIVER_DOCUMENT_TYPE", _("Driver Document Type")
    ORGANIZATION_DOCUMENT_TYPE = "ORGANIZATION_DOCUMENT_TYPE", _("Organization Document Type")

    ORGANIZATION_TYPE = "ORGANIZATION_TYPE", _("Organization Type")
    BROKER_VEHICLE_TYPE = "BROKER_VEHICLE_TYPE", _("Broker Vehicle Type")

    LOCATION_TYPE = "LOCATION_TYPE", _("Location Type")

    SHIPMENT_FREIGHT_MODE = "SHIPMENT_FREIGHT_MODE", _("Shipment Freight Mode")
    SHIPMENT_PACKAGING_TYPE = "SHIPMENT_PACKAGING_TYPE", _("Shipment Packaging Type")
    SHIPMENT_MATERIAL_TYPE = "SHIPMENT_MATERIAL_TYPE", _("Shipment Material Type")
    SHIPMENT_DOCUMENT_TYPE = "SHIPMENT_DOCUMENT_TYPE", _("Shipment Document Type")

    WEIGHT_UNIT = "WEIGHT_UNIT", _("Weight Unit")

    FINANCE_EXPENSE_TYPE = "FINANCE_EXPENSE_TYPE", _("Finance Expense Type")
    FINANCE_EXPENSE_CATEGORY = "FINANCE_EXPENSE_CATEGORY", _("Finance Expense Category")
    FINANCE_TRANSACTION_TYPE = "FINANCE_TRANSACTION_TYPE", _("Finance Transaction Type")
    FINANCE_PAYMENT_MODE = "FINANCE_PAYMENT_MODE", _("Finance Payment Mode")
    BANK_ACCOUNT_TYPE = "BANK_ACCOUNT_TYPE", _("Bank Account Type")

    GENERAL_STATUS = "GENERAL_STATUS", _("General Status")

    MAINTENANCE_SERVICE_TYPE = "MAINTENANCE_SERVICE_TYPE", _("Maintenance Service Type")
    MAINTENANCE_ITEM = "MAINTENANCE_ITEM", _("Maintenance Item")
    MAINTENANCE_VENDOR = "MAINTENANCE_VENDOR", _("Maintenance Vendor")
    MAINTENANCE_TRANSACTION_TYPE = "MAINTENANCE_TRANSACTION_TYPE", _("Maintenance Transaction Type")

    TYRE_BRAND = "TYRE_BRAND", _("Tyre Brand")
    TYRE_MODEL = "TYRE_MODEL", _("Tyre Model")
    TYRE_SIZE = "TYRE_SIZE", _("Tyre Size")
    TYRE_TYPE = "TYRE_TYPE", _("Tyre Type")
    TYRE_TUBE_TYPE = "TYRE_TUBE_TYPE", _("Tyre Tube Type")
    TYRE_PURCHASE_TYPE = "TYRE_PURCHASE_TYPE", _("Tyre Purchase Type")
    TYRE_POSITION = "TYRE_POSITION", _("Tyre Position")
