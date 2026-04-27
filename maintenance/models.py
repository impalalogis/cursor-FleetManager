from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from datetime import date

from entity.models import Vehicle
from utils.validators import (document_file_validator, name_no_digits_validator, user_document_upload_path)

from configuration.constants import ChoiceCategory

# Create your models here.
SERVICE_TYPE = [
    ('Oil_Change', 'Oil_Change.'),
    ('Brake_Inspection', 'Brake_Inspection.'),
    ('Engine', 'Engine'),
    ('Tyre', 'Tyre'),
]
TYRE_CHOICES = [
    ('Radial', 'Radial.'),
    ('Nylon', 'Nylon.'),
    ('Mx', 'Mx.'),
]
PURCHASE_TYPE = [
    ('Original', 'Original'),
    ('Used', 'Used'),
    ('Retread', 'Retread'),
]
POSITION_CHOICES = [
    ('FL', 'Front Left'),
    ('FR', 'Front Right'),
    ('RL', 'Rear Left'),
    ('RR', 'Rear Right'),
    ('SP', 'Spare'),
    # Add more for trucks with multiple axles
]


class MaintenanceRecord(models.Model):
    vehicle = models.ForeignKey('entity.Vehicle', on_delete=models.CASCADE, related_name='maintenance_records')

    # FK to configuration.Choice
    service_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='maintenance_service_type',
        limit_choices_to={'category': ChoiceCategory.MAINTENANCE_SERVICE_TYPE}
    )
    items = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='maintenance_item',
        limit_choices_to={'category': ChoiceCategory.MAINTENANCE_ITEM}
    )

    service_date = models.DateField(null=False, blank=False)
    next_due_date = models.DateField(null=True, blank=True)
    mileage_at_service = models.PositiveIntegerField(null=True, blank=True)

    # REMOVE the old CharField named performed_by entirely

    notes = models.TextField(blank=True, null=True)

    # Tyre-specific fields
    tyre = models.ForeignKey('Tyre', on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="Select tyre only when service type category is 'Tyre'")
    next_mileage_due_date = models.PositiveIntegerField(null=True, blank=True)

    invoice_no = models.CharField(max_length=20, unique=True, blank=True, null=True)

    vendors = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='maintenance_vendor',
        limit_choices_to={'category': ChoiceCategory.MAINTENANCE_VENDOR}
    )

    quantity = models.PositiveIntegerField(null=True, blank=True)

    # Make these nullable or give defaults to avoid migration prompts
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # % or absolute? adjust later
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Generic relation: who performed (Driver/Owner organization)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        limit_choices_to={"app_label": "entity", "model__in": ["driver", "organization"]},
        null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    performed_by = GenericForeignKey("content_type", "object_id")

    maintenance_document = models.FileField(
        upload_to=user_document_upload_path,
        validators=[document_file_validator],
        null=True, blank=True
    )

    def clean(self):
        from django.core.exceptions import ValidationError

        # service_type is a Choice FK; compare by category/value fields
        # Adjust field names based on your Choice model (e.g., .key/.value/.name)
        st = self.service_type
        is_tyre = bool(st and (getattr(st, "key", None) == "Tyre" or getattr(st, "value", None) == "Tyre" or getattr(st, "name", None) == "Tyre"))

        if is_tyre and not self.tyre:
            raise ValidationError({'tyre': 'Tyre must be selected when service type is "Tyre".'})
        if (not is_tyre) and self.tyre:
            raise ValidationError({'tyre': 'Tyre should only be selected when service type is "Tyre".'})

        if self.content_type:
            if not (
                self.content_type.app_label == 'entity' and
                self.content_type.model in ('driver', 'organization')
            ):
                raise ValidationError("performed_by must point to a Driver or an Owner organization.")

            if self.content_type.model == 'organization' and self.object_id:
                org = self.content_type.get_object_for_this_type(pk=self.object_id)
                if getattr(org, 'organization_type_code', None) != 'OWNER':
                    raise ValidationError({'performed_by': 'Only organizations of type OWNER can be selected here.'})

    def save(self, *args, **kwargs):
        st = self.service_type
        is_tyre = bool(st and (getattr(st, "key", None) == "Tyre" or getattr(st, "value", None) == "Tyre" or getattr(st, "name", None) == "Tyre"))
        if not is_tyre:
            self.tyre = None

        # Optional: auto-calc total_cost if not provided
        if self.quantity and self.rate is not None:
            base = Decimal(self.quantity) * self.rate
            if self.gst is not None:
                # treat gst as percent; change if it’s absolute
                self.total_cost = (base * (Decimal('1') + (self.gst / Decimal('100')))).quantize(Decimal('0.01'))
            else:
                self.total_cost = base.quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

    def __str__(self):
        st_label = None
        if self.service_type:
            st_label = getattr(self.service_type, "name", None) or getattr(self.service_type, "value", None) or str(self.service_type)
        if st_label == 'Tyre' and self.tyre:
            return f"{st_label} - {self.tyre} on {self.vehicle.registration_number}"
        return f"{st_label or 'Service'} on {self.vehicle.registration_number}"


class Tyre(models.Model):
    """
    Enhanced Tyre model with comprehensive specifications for Indian truck fleet management.
    Manages detailed tyre information, specifications, and maintenance tracking.
    """
    # Basic Identification
    tyreNo = models.CharField(max_length=50, null=False, blank=True, help_text="Unique tyre identification number")
    tyre_document = models.FileField(upload_to=user_document_upload_path, validators=[document_file_validator],
                                     null=True, blank=True, help_text="Tyre warranty/documentation")

    # Tyre Specifications (Enhanced)
    brand = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tyre_brand',
        limit_choices_to={'category': ChoiceCategory.TYRE_BRAND}
    )

    model = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tyre_model',
        limit_choices_to={'category': ChoiceCategory.TYRE_MODEL}
    )

    size = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tyre_size',
        limit_choices_to={'category': ChoiceCategory.TYRE_SIZE}
    )
    type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tyre_type',
        limit_choices_to={'category': ChoiceCategory.TYRE_TYPE}
    )

    # Enhanced Specifications
    tube_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tyre_tube_type',
        limit_choices_to={'category': ChoiceCategory.TYRE_TUBE_TYPE}
    )
    ply_rating = models.CharField(max_length=10, blank=True, null=True, help_text="Ply rating (e.g., 16PR, 18PR)")


    # Purchase Information
    purchase_date = models.DateField(null=True, blank=True, help_text="Date of tyre purchase")
    purchase_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tyre_purchase_type',
        limit_choices_to={'category': ChoiceCategory.TYRE_PURCHASE_TYPE}
    )
    purchase_by = models.CharField(max_length=50, null=True, blank=True,
                                   help_text="Purchased by (person/organization)")
    amount = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True, help_text="Purchase amount")
    invoice_document = models.FileField(upload_to=user_document_upload_path, validators=[document_file_validator],
                                        null=True, blank=True, help_text="Purchase invoice document")

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tyre'
        ordering = ['brand', 'model', 'size']
        indexes = [
            models.Index(fields=['brand', 'model']),
            models.Index(fields=['size']),
            models.Index(fields=['purchase_date']),
        ]

    def __str__(self):
        return f"{self.brand} {self.model} ({self.size}) - {self.tyreNo}"


    def calculate_age(self):
        if not self.purchase_date:
            return None
        today = date.today()
        return today.year - self.purchase_date.year - (
                (today.month, today.day) < (self.purchase_date.month, self.purchase_date.day))

    @property
    def age(self):
        return self.calculate_age()

    @property
    def tyre_specification_summary(self):
        """Get comprehensive tyre specification summary"""
        return {
            'tyre_number': self.tyreNo,
            'specification': f"{self.brand} {self.model}",
            'size': self.size,
            'type': self.type,
            'tube_type': self.tube_type,
            'ply_rating': self.ply_rating,
            'purchase_info': {
                'date': self.purchase_date,
                'type': self.purchase_type,
                'amount': self.amount,
                'purchased_by': self.purchase_by
            }
        }

    @property
    def is_tubeless(self):
        """Check if tyre is tubeless"""
        return self.tube_type and 'tubeless' in self.tube_type.lower()

    def get_current_vehicle(self):
        """Get the vehicle where this tyre is currently installed"""
        latest_transaction = self.transactions.filter(
            transaction_type__internal_value__in=['Install', 'Replace']
        ).order_by('-transaction_date').first()

        if latest_transaction:
            # Check if tyre was removed after this installation
            removed = self.transactions.filter(
                transaction_type__internal_value='Remove',
                transaction_date__gt=latest_transaction.transaction_date
            ).exists()

            if not removed:
                return latest_transaction.vehicle
        return None


class TyreTransaction(models.Model):
    tyre = models.ForeignKey(Tyre, on_delete=models.CASCADE, related_name='transactions')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='tyre_transactions')
    position = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tyre_position',
        limit_choices_to={'category': ChoiceCategory.TYRE_POSITION}
    )
    transaction_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.PROTECT,
        related_name='tyre_transactions',
        limit_choices_to={'category': ChoiceCategory.MAINTENANCE_TRANSACTION_TYPE},
        null=True,
        blank=True,
    )
    transaction_date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                               help_text="Cost of tyre service/repair")
    performed_by = models.CharField(max_length=100)  # Mechanic or technician name
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        label = self.transaction_type.display_value if self.transaction_type else self.transaction_type_code or "Unknown"
        return f"{label} - {self.tyre} on {self.vehicle}"

    @property
    def transaction_type_code(self):
        return self.transaction_type.internal_value if self.transaction_type else None

    @property
    def transaction_type_label(self):
        return self.transaction_type.display_value if self.transaction_type else None
