from django.db import models
from django.core.exceptions import ValidationError
from django.apps import apps
from django.conf import settings
from django.utils import timezone

from utils.validators import (birthdate_validator, future_date_validator,
                               pincode_validator, user_document_upload_path, document_file_validator)

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from entity.models import AddressMixin, ContactMixin
from decimal import Decimal

from django.db.models import Sum, Q

from configuration.constants import ChoiceCategory

class ConsignmentGroup(models.Model):
    """
    ConsignmentGroup model for batching multiple consignments together.
    Used for operational and billing purposes in logistics operations.
    """
    group_id = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # group_name = models.CharField(
    #     max_length=200,
    #     null=True, blank=True,
    #     help_text="Optional name/description for this consignment group"
    # )

    consignments = models.ManyToManyField('Consignment', blank=True)

    # Scheduling
    planned_dispatch_date = models.DateField(
        null=True, blank=True,
        help_text="Planned dispatch date for this group"
    )
    actual_dispatch_date = models.DateField(
        null=True, blank=True,
        help_text="Actual dispatch date"
    )

    # Financial summary (calculated fields)
    total_weight = models.DecimalField(
        max_digits=12, decimal_places=3,
        null=True, blank=True,
        help_text="Total weight of all consignments in this group"
    )
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        help_text="Total amount for all consignments in this group"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_consignment_groups'
    )

    class Meta:
        db_table = 'consignment_group'
        indexes = [

            models.Index(fields=['planned_dispatch_date']),
            models.Index(fields=['created_at']),

        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_weight__gte=0) | models.Q(total_weight__isnull=True),
                name='non_negative_total_weight'
            ),
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0) | models.Q(total_amount__isnull=True),
                name='non_negative_total_amount'
            ),
        ]
        ordering = ['group_id']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            today_str = timezone.now().strftime("%Y%m%d")
            self.group_id = f"CG{today_str}{self.pk}"
            ConsignmentGroup.objects.filter(pk=self.pk).update(group_id=self.group_id)

    def calculate_totals(self):
        totals = self.consignments.aggregate(
            total_weight=Sum('weight'),
            total_amount=Sum('total_freight')
        )
        self.total_weight = totals['total_weight'] or Decimal('0')
        self.total_amount = totals['total_amount'] or Decimal('0')
        self.save(update_fields=['total_weight', 'total_amount'])

    def get_consignment_count(self):
        """Get the number of consignments in this group"""
        return self.consignments.count()

    # def get_route_summary(self):
    #     """Get a summary of the route covered by this group"""
    #     consignments = self.consignments.select_related(
    #         'consignor', 'consignee'
    #     ).all()
    #
    #     origins = set()
    #     destinations = set()
    #     #
    #     # for consignment in consignments:
    #     #     if consignment.consignor.city:
    #     #         origins.add(f"{consignment.consignor.city}, {consignment.consignor.state}")
    #     #     if consignment.consignee.city:
    #     #         destinations.add(f"{consignment.consignee.city}, {consignment.consignee.state}")
    #     #
    #     # return {
    #     #     'origins': list(origins),
    #     #     'destinations': list(destinations),
    #     #     'consignment_count': len(consignments)
    #     # }
    #
    #     route_list = []
    #
    #     for consignment in consignments:
    #         origin = (
    #             f"{consignment.consignor.city}, {consignment.consignor.state}"
    #             if consignment.consignor else "Unknown Origin"
    #         )
    #         destination = (
    #             f"{consignment.consignee.city}, {consignment.consignee.state}"
    #             if consignment.consignee else "Unknown Destination"
    #         )
    #         route_list.append(
    #             f"Consignment {consignment.id}: {origin} → {destination}"
    #         )
    #
    #     return route_list

    def get_route_summary(self):
        """Get a per-consignment origin → destination list for this group"""
        consignments = self.consignments.select_related(
            'consignor', 'consignee'
        ).all()

        route_list = []

        for consignment in consignments:
            origin = (
                f"{consignment.consignor.city}, {consignment.consignor.state}"
                if consignment.consignor else "Unknown Origin"
            )
            destination = (
                f"{consignment.consignee.city}, {consignment.consignee.state}"
                if consignment.consignee else "Unknown Destination"
            )
            route_list.append(
                f"Consignment {consignment.id}: {origin} → {destination}"
            )

        return route_list

    # @property
    # def origins(self):
    #     try:
    #         return ', '.join(self.get_route_summary()['origins'])
    #     except Exception:
    #         return 'N/A'
    #
    # @property
    # def destinations(self):
    #     try:
    #         return ', '.join(self.get_route_summary()['destinations'])
    #     except Exception:
    #         return 'N/A'

    def __str__(self):
        count = getattr(self, 'consignment_count', 'N/A')
        return f"{self.group_id}"

    # @property
    # def consignment_count(self):
    #     try:
    #         return self.consignments.count()
    #     except Exception:
    #         return 'N/A'

    # def __str__(self):
    #     count = self.get_consignment_count()
    #     return f"{self.group_id} - {self.group_name or 'Consignment Group'} ({count} consignments)"

    #
    # def calculate_totals(self):
    #     """Calculate and update total weight and amount from associated consignments"""
    #     consignments = self.consignments.all()
    #
    #     self.total_weight = sum(
    #         consignment.weight or Decimal('0')
    #         for consignment in consignments
    #     )
    #     self.total_amount = sum(
    #         consignment.total_freight or Decimal('0')
    #         for consignment in consignments
    #     )
    #
    #
    #     self.save(update_fields=['total_weight', 'total_amount',])

    from django.db.models import Sum


class Consignment(models.Model):
    """
    Consignment model for managing individual shipment units.
    Captures complete consignor and consignee information along with goods details.
    Each consignment belongs to a ConsignmentGroup for operational efficiency.
    """
    consignment_id = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # Consignor Information (Sender)
    consignor = models.ForeignKey(
        'entity.Organization',
        on_delete=models.PROTECT,
        related_name='consignor_consignments',
        null=True, blank=True,
        help_text="Organization sending the goods"
    )

    # Consignee Information (Receiver)
    consignee = models.ForeignKey(
        'entity.Organization',
        on_delete=models.PROTECT,
        related_name='consignee_consignments',
        null=True, blank=True,
        help_text="Organization receiving the goods"
    )

    from_location = models.ForeignKey(
        'configuration.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consignment_from_location',
        help_text="Select location from dropdown"
    )

    to_location = models.ForeignKey(
        'configuration.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consignment_location_to',
        help_text="Select location from dropdown"
    )

    material_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='consignment_material_type_set',
        limit_choices_to={'category': ChoiceCategory.SHIPMENT_MATERIAL_TYPE},
        help_text="Specific material type (e.g., Steel, Electronics, Food Items)",
        default=1  # Assuming 1 is for 'tonnes'

    )

    # Weight and dimensions
    weight = models.DecimalField(
        max_digits=10, decimal_places=3,
        help_text="Weight in tonnes/kg"
    )
    weight_unit = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='consignment_weight_unit_set',
        limit_choices_to={'category': ChoiceCategory.WEIGHT_UNIT},
        help_text="Unit of weight measurement",
        default=1  # Assuming 1 is for 'tonnes'
    )
    volume = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True,
        help_text="Volume in cubic meters"
    )

    # Packaging information
    number_of_packages = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Number of packages/pieces"
    )
    packaging_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='consignment_packaging_set',
        limit_choices_to={'category': ChoiceCategory.SHIPMENT_PACKAGING_TYPE},
        help_text="Type of packaging (boxes, pallets, loose, etc.)"

    )

    vehicle_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='Consignment_VEHICLE_TYPE',
        limit_choices_to={'category': ChoiceCategory.BROKER_VEHICLE_TYPE},
        help_text="Preferred vehicle types for Consignment"
    )

    # Freight and pricing
    freight_mode = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='consignment_freight_mode_set',
        limit_choices_to={'category': ChoiceCategory.SHIPMENT_FREIGHT_MODE},
        help_text="Freight calculation mode (Rate, Fixed, etc.)"
    )

    rate = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Rate per kg/tonne based on freight mode"
    )
    total_freight = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text="Total freight amount for this consignment"

    )

    # Scheduling
    schedule_date = models.DateField(
        null=True, blank=True,
        help_text="Scheduled pickup date"
    )
    scheduled_pickup_time = models.TimeField(
        null=True, blank=True,
        help_text="Scheduled pickup time"
    )
    expected_delivery_date = models.DateField(
        null=True, blank=True,
        help_text="Expected delivery date"
    )
    expected_delivery_time = models.TimeField(
        null=True, blank=True,
        help_text="Expected delivery time"

    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_consignments'
    )

    class Meta:
        db_table = 'consignment'
        indexes = [

            # models.Index(fields=['consignment_group']),
            models.Index(fields=['consignor']),
            models.Index(fields=['consignee']),
            models.Index(fields=['schedule_date']),
            # models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            # models.Index(fields=['consignor_city', 'consignor_state']),
            # models.Index(fields=['consignee_city', 'consignee_state']),
            # models.Index(fields=['goods_type']),
            # models.Index(fields=['requires_special_handling']),

        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(weight__gt=0),
                name='positive_weight'

            ),
            # models.CheckConstraint(
            #     check=models.Q(rate__gt=0),
            #     name='non_negative_amount'
            # ),

            models.CheckConstraint(

                check=models.Q(number_of_packages__gt=0) | models.Q(number_of_packages__isnull=True),
                name='positive_package_count'
            ),
        ]

    def clean(self):
        """Validate consignment data"""
        super().clean()

        # Ensure consignor and consignee are different

        if self.consignor == self.consignee:
            raise ValidationError("Consignor and consignee organizations cannot be the same.")

        # Validate freight calculation
        if self.freight_mode and self.freight_mode.internal_value == 'Rate':
            if not self.rate:
                raise ValidationError("Rate per unit is required when freight mode is 'Rate'.")

        # Update group totals when consignment changes
        # if self.consignment_group:
        #     self.consignment_group.calculate_totals()

    def calculate_total_freight(self):
        """Calculate total freight based on freight mode"""
        if self.freight_mode and self.freight_mode.internal_value == 'Rate':
            return (self.weight or Decimal('0')) * (self.rate or Decimal('0'))
        elif self.freight_mode and self.freight_mode.internal_value == 'Fixed':
            return self.rate or Decimal('0')
        else:
            return self.rate or Decimal('0')

    def __str__(self):
        return f"{self.consignment_id} - {self.consignor} → {self.consignee}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.total_freight = self.calculate_total_freight()
        super().save(*args, **kwargs)

        if is_new:
            today_str = timezone.now().strftime("%Y%m%d")
            self.consignment_id = f"CONS{today_str}{self.pk}"
            Consignment.objects.filter(pk=self.pk).update(consignment_id=self.consignment_id)


class Shipment(models.Model):
    """
    Shipment model for tracking delivery execution.
    Each shipment is assigned to one ConsignmentGroup containing multiple consignments.
    """
    shipment_id = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # Link to ConsignmentGroup instead of individual Consignment
    consignment_group = models.OneToOneField(
        ConsignmentGroup,

        on_delete=models.SET_NULL,
        related_name='shipment',
        null=True, blank=True,

        help_text="Consignment group assigned to this shipment"
    )

    e_way_bill = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        verbose_name="E-Way Bill"
    )

    invoice_no = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        verbose_name="Invoice No"
    )

    # Vehicle and crew assignment
    vehicle = models.ForeignKey(
        'entity.Vehicle',
        on_delete=models.SET_NULL,
        related_name='shipments',
        null=True, blank=True,
        help_text="Vehicle assigned for this shipment"
    )
    driver = models.ForeignKey(
        'entity.Driver',
        on_delete=models.SET_NULL,
        related_name='assigned_shipments',
        null=True, blank=True,
        help_text="Primary driver assigned"
    )
    co_driver = models.ForeignKey(
        'entity.Driver',
        on_delete=models.SET_NULL,
        related_name='co_driver_shipments',
        null=True, blank=True,
        help_text="Co-driver if applicable"

    )
    transporter = models.ForeignKey(
        'entity.Organization',
        on_delete=models.SET_NULL,
        related_name='transporter_shipments',
        null=True, blank=True,
        limit_choices_to={'organization_type__internal_value': 'TRANSPORTER'},
        help_text="Transporter organization handling the shipment"
    )

    broker = models.ForeignKey(
        'entity.Organization',
        on_delete=models.SET_NULL,
        related_name='broker_shipments',
        null=True, blank=True,
        limit_choices_to={'organization_type__internal_value': 'BROKER'},
        help_text="Broker organization facilitating the shipment"
    )

    # Scheduling and timing
    planned_departure = models.DateTimeField(
        null=True, blank=True,
        help_text="Planned departure time"
    )
    actual_departure = models.DateTimeField(
        null=True, blank=True,
        help_text="Actual departure time"
    )
    planned_arrival = models.DateTimeField(
        null=True, blank=True,
        help_text="Planned arrival time"
    )
    actual_arrival = models.DateTimeField(
        null=True, blank=True,
        help_text="Actual arrival time"
    )

    # Vehicle tracking
    odometer_start = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Starting odometer reading"
    )
    odometer_end = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Ending odometer reading"
    )
    total_distance = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Total distance covered in km"
    )

    # Financial tracking
    freight_advance = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        help_text="Total advance received for this shipment"
    )
    total_freight_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        help_text="Total freight amount for all consignments in this shipment"
    )

    # # Status and notes
    # status = models.ForeignKey(
    #     'configuration.Choice',
    #     on_delete=models.SET_NULL,
    #     null=True, blank=True,
    #     related_name='shipment_status_set',
    #     limit_choices_to={'category': 'SHIPMENT_STATUS'},
    #     help_text="Current status of the shipment"
    # )
    notes = models.CharField(

        null=True, blank=True,
        help_text="General notes about the shipment"
    )

    # Route and logistics

    planned_route = models.ForeignKey(
        'configuration.Route',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shipment_route_planned_set',
        # limit_choices_to={'category': 'SHIPMENT_STATUS'},
        help_text="Planned route taken"
    )
    actual_route = models.ForeignKey(
        'configuration.Route',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shipment_route_actual_set',
        # limit_choices_to={'category': 'SHIPMENT_STATUS'},

        help_text="Actual route taken"
    )

    lr_no = models.CharField(
        max_length=8,
        blank=True,
        null=True,
        unique=True,
        verbose_name="LR No"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_shipments'
    )

    class Meta:
        db_table = 'shipment'
        indexes = [
            models.Index(fields=['consignment_group']),
            models.Index(fields=['vehicle']),
            models.Index(fields=['driver']),
            models.Index(fields=['transporter']),

            # models.Index(fields=['status']),

            models.Index(fields=['actual_departure']),
            models.Index(fields=['planned_departure']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(freight_advance__gte=0),
                name='non_negative_advance'
            ),
            models.CheckConstraint(
                check=models.Q(total_distance__gte=0) | models.Q(total_distance__isnull=True),
                name='non_negative_distance'
            ),
            models.CheckConstraint(
                check=models.Q(odometer_end__gte=models.F('odometer_start')) |
                      models.Q(odometer_end__isnull=True) |
                      models.Q(odometer_start__isnull=True),
                name='valid_odometer_reading'
            ),
        ]

    @classmethod
    def get_next_invoice_no(cls, year=None, exclude_pk=None):
        if year is None:
            year = timezone.now().year

        year_str = str(year)
        prefix = f"INV-{year_str}-"

        qs = cls.objects.filter(
            invoice_no__startswith=prefix
        ).exclude(
            invoice_no__isnull=True
        ).exclude(
            invoice_no__exact=""
        )

        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)

        max_seq = 0

        for value in qs.values_list("invoice_no", flat=True):
            if not value:
                continue

            parts = value.split("-")
            if len(parts) != 3:
                continue

            inv_prefix, inv_year, seq_part = parts
            if inv_prefix == "INV" and inv_year == year_str and seq_part.isdigit():
                seq = int(seq_part)
                if seq > max_seq:
                    max_seq = seq

        next_seq = max_seq + 1
        return f"INV-{year_str}-{next_seq:04d}"

    def ensure_unique_invoice_no(self):
        if not self.invoice_no:
            return

        value = self.invoice_no.strip()
        parts = value.split("-")

        if len(parts) != 3:
            return

        inv_prefix, inv_year, seq_part = parts
        if inv_prefix != "INV" or not inv_year.isdigit() or not seq_part.isdigit():
            return

        duplicate_qs = Shipment.objects.filter(invoice_no=value)
        if self.pk:
            duplicate_qs = duplicate_qs.exclude(pk=self.pk)

        if duplicate_qs.exists():
            self.invoice_no = Shipment.get_next_invoice_no(year=int(inv_year), exclude_pk=self.pk)
    @classmethod
    def get_next_lr_no(cls, year=None, exclude_pk=None):
        if year is None:
            year = timezone.now().year

        year_str = str(year)

        qs = cls.objects.filter(lr_no__startswith=year_str).exclude(lr_no__isnull=True).exclude(lr_no__exact="")
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)

        max_seq = 0

        for value in qs.values_list("lr_no", flat=True):
            if value and len(value) == 8 and value[:4].isdigit() and value[4:].isdigit():
                if value[:4] == year_str:
                    seq = int(value[4:])
                    if seq > max_seq:
                        max_seq = seq

        next_seq = max_seq + 1
        return f"{year_str}{next_seq:04d}"

    def ensure_unique_lr_no(self):
        """
        If lr_no already exists on another shipment, regenerate the next one for that year.
        Useful when two users generate the same preview LR before saving.
        """
        if not self.lr_no:
            return

        lr_value = self.lr_no.strip()
        if len(lr_value) != 8 or not lr_value.isdigit():
            return

        year = int(lr_value[:4])

        duplicate_qs = Shipment.objects.filter(lr_no=lr_value)
        if self.pk:
            duplicate_qs = duplicate_qs.exclude(pk=self.pk)

        if duplicate_qs.exists():
            self.lr_no = Shipment.get_next_lr_no(year=year, exclude_pk=self.pk)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        skip_calc = kwargs.pop('skip_calculation', False)

        self.total_distance = self.calculate_distance()

        # Prevent duplicate LR/invoice if same preview number was generated by another user
        self.ensure_unique_lr_no()
        self.ensure_unique_invoice_no()

        super().save(*args, **kwargs)

        if is_new:
            today_str = timezone.now().strftime("%Y%m%d")
            self.shipment_id = f"SHIP{today_str}{self.pk}"
            Shipment.objects.filter(pk=self.pk).update(shipment_id=self.shipment_id)

        if not skip_calc:
            self.calculate_totals()

    def calculate_totals(self):
        """Calculate total freight amount from all consignments in the group"""
        if self.consignment_group:
            total_freight = sum(

                consignment.total_freight or Decimal('0')

                for consignment in self.consignment_group.consignments.all()
            )
            if self.total_freight_amount != total_freight:
                self.total_freight_amount = total_freight
                Shipment.objects.filter(pk=self.pk).update(total_freight_amount=total_freight)

    def calculate_distance(self):
        """Calculate total distance from odometer readings"""
        if self.odometer_start and self.odometer_end:
            self.total_distance = self.odometer_end - self.odometer_start
            return self.total_distance
        return None


    def get_consignment_count(self):
        """Get number of consignments in this shipment"""
        return self.consignment_group.consignments.count() if self.consignment_group else 0

    def get_route_summary(self):
        """Get route summary for this shipment"""
        if self.consignment_group:
            return self.consignment_group.get_route_summary()
        return {}

    def __str__(self):
        if self.consignment_group:
            count = self.get_consignment_count()
            return f"{self.shipment_id}"
        return f"{self.shipment_id}"


# Keep existing models with minimal changes
ALLOWED_MODELS = ('entity.driver', "entity.organization")


class ShipmentExpense(models.Model):
    """
    ShipmentExpense model for tracking delivery-related expenses.
    """
    shipment = models.ForeignKey(
        Shipment,

        on_delete=models.CASCADE,

        related_name='expenses',
        null=True, blank=True
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        limit_choices_to={"app_label": "entity", "model__in": ["driver", "organization"]},
        null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    expense_by = GenericForeignKey("content_type", "object_id")
    expense_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shipment_expense_set',
        limit_choices_to={'category': ChoiceCategory.FINANCE_EXPENSE_TYPE}
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    expense_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=1000, null=True, blank=True)
    shipment_expense_document = models.FileField(upload_to=user_document_upload_path,
                                                 validators=[document_file_validator],
                                                 null=True, blank=True)

    def clean(self):
        if self.content_type:
            if not (
                self.content_type.app_label == 'entity' and
                self.content_type.model in ('driver', 'organization')
            ):
                raise ValidationError("expense_by must point to a Driver or an Owner organization.")

            if self.content_type.model == 'organization' and self.object_id:
                org = self.content_type.get_object_for_this_type(pk=self.object_id)
                if getattr(org, 'organization_type_code', None) != 'OWNER':
                    raise ValidationError("Only organizations of type OWNER can be attached as expense_by.")

    def __str__(self):
        return f"{self.expense_type} - ₹{self.amount} on {self.expense_date}"

    class Meta:
        db_table = 'shipmentexpense'
        indexes = [
            models.Index(fields=['shipment']),
            models.Index(fields=['expense_date']),
            models.Index(fields=['shipment', 'expense_date']),
            models.Index(fields=['expense_type', 'expense_date']),
        ]


class ShipmentStatus(models.Model):
    """
    ShipmentStatus model for tracking shipment status changes.
    """
    shipment = models.ForeignKey(
        Shipment,

        on_delete=models.CASCADE,

        related_name='status_logs'
    )
    status = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shipment_status_log_set',
        limit_choices_to={'category': ChoiceCategory.GENERAL_STATUS}
    )

    shipment_doc_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shipment_doc_type',
        limit_choices_to={'category': ChoiceCategory.SHIPMENT_DOCUMENT_TYPE}
    )
    shipment_document = models.FileField(upload_to=user_document_upload_path, validators=[document_file_validator],
                                         null=True, blank=True)

    #timestamp = models.DateTimeField(auto_now_add=True)
    effective_date = models.DateTimeField(
        null=True, blank=True,
        help_text="effective_date"
    )
    updated_by = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="User who updated the status"
    )
    notes = models.TextField(
        null=True, blank=True,
        help_text="Additional notes about this status change"
    )

    def __str__(self):
        return f"{self.shipment} → {self.status} at {self.effective_date}"

    class Meta:
        db_table = 'shipmentstatus'
        indexes = [
            models.Index(fields=['shipment']),
            models.Index(fields=['effective_date']),
            models.Index(fields=['status']),
        ]


class DriverAdvance(models.Model):
    """
    DriverAdvance model for tracking advances given to drivers.
    """
    driver = models.ForeignKey('entity.Driver', on_delete=models.PROTECT)

    # ✅ allow Owner organization OR Shipment (operations) as the payer
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        limit_choices_to=(
            Q(app_label="entity",     model="organization") |
            Q(app_label="operations", model="shipment")  # <-- fix app label: operations
        ),
        null=True, blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    advance_by = GenericForeignKey("content_type", "object_id")

    # This is the shipment the advance is FOR (reporting/expense linking), independent of payer
    shipment = models.ForeignKey(
        Shipment,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="Shipment this advance is for (optional)"
    )

    description = models.CharField(
        max_length=1000,
        blank=True,
        help_text="Purpose of advance (e.g. fuel, lodging)"
    )
    date = models.DateField(auto_now_add=True, editable=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_settled = models.BooleanField(default=False)
    carried_forward = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'driver_advance'
        indexes = [
            models.Index(fields=['driver']),
            models.Index(fields=['date']),
            models.Index(fields=['shipment', 'driver']),
        ]

    # ---------- VALIDATION / SYNC RULES ----------
    def clean(self):
        """
        Keep shipment FK and payer (advance_by) consistent:
          - If payer is a Shipment, default 'shipment' FK to that same shipment when not provided.
          - Ensure payer ContentType is either entity.owner or operations.shipment.
        """
        super().clean()

        if self.content_type_id and self.object_id:
            app_label = self.content_type.app_label
            model     = self.content_type.model

            if (app_label, model) not in {("entity", "organization"), ("operations", "shipment")}:
                raise ValidationError("advance_by must be either an OWNER organization or a Shipment.")

            if app_label == "entity" and model == "organization":
                org = self.content_type.get_object_for_this_type(pk=self.object_id)
                if getattr(org, 'organization_type_code', None) != 'OWNER':
                    raise ValidationError({"content_type": "Only organizations of type OWNER can fund driver advances."})

            # If payer is a Shipment and 'shipment' is empty, auto-sync it.
            if app_label == "operations" and model == "shipment":
                if self.shipment_id is None:
                    self.shipment_id = self.object_id  # make the 'for' shipment match the payer shipment

                # Optional hard-guard: if shipment is provided but doesn't match payer shipment, raise
                elif self.shipment_id != self.object_id:
                    raise ValidationError(
                        "When payer is a Shipment, the 'shipment' field must match the same Shipment."
                    )

    def save(self, *args, **kwargs):
        # Re-run clean to enforce sync even when saving programmatically
        self.full_clean()
        return super().save(*args, **kwargs)

    # ---------- CARRY-FORWARD / EXPENSE LOGIC (unchanged) ----------
    def _previous_cf_for_driver(self):
        qs = (
            DriverAdvance.objects
            .filter(driver_id=self.driver_id)
            .exclude(pk=self.pk)
            .order_by('date', 'id')
        )
        prev = qs.last()
        return prev.carried_forward if prev is not None else Decimal('0')

    def _total_expenses_for_this_shipment_and_driver(self) -> Decimal:
        if not self.shipment_id:
            return Decimal('0')

        driver_ct = ContentType.objects.get_for_model(self.driver.__class__)
        expenses = ShipmentExpense.objects.filter(
            shipment_id=self.shipment_id,
            content_type=driver_ct,
            object_id=self.driver_id
        ).only('amount')

        total = Decimal('0')
        for e in expenses:
            total += (e.amount or Decimal('0'))
        return total

    def settle_and_carry_forward(self):
        """
        carried_forward = prev_cf + amount - incremental_expenses_for_this_shipment
        where incremental_expenses = cumulative_expenses_now - cumulative_expenses_at_previous_advance_on_same_shipment
        """
        amt = self.amount or Decimal('0')
        prev_cf = self._previous_cf_for_driver()

        # cumulative expenses for THIS shipment & driver (unchanged)
        exp_cumulative = self._total_expenses_for_this_shipment_and_driver()
        print("exp_cumulative ", exp_cumulative)
        # how much of these expenses were already applied by *earlier* advances on the same shipment?
        # prev_same = self._previous_advance_same_shipment()


        # prev_exp_cumulative = prev_same.total_expenses if prev_same else Decimal('0')
        # print("prev_exp_cumulative ", prev_exp_cumulative)
        # only subtract the *new* (unapplied) portion
        # exp_increment = exp_cumulative + prev_cf
        # if exp_increment < 0:
        #     exp_increment = Decimal('0')  # safety

        # set fields:
        self.total_expenses = exp_cumulative
        self.carried_forward = (prev_cf + amt) - self.total_expenses
        self.is_settled = (self.carried_forward == 0)

        # ⚠️ IMPORTANT: use queryset update to avoid triggering post_save again
        DriverAdvance.objects.filter(pk=self.pk).update(
            total_expenses=self.total_expenses,
            carried_forward=self.carried_forward,
            is_settled=self.is_settled,
        )
        return self.carried_forward

    def __str__(self):
        shipment_info = self.shipment or 'General'
        return f"{self.driver.first_name} | Advance ₹{self.amount} | {shipment_info}"

    def remaining_balance(self):
        if self.shipment:
            driver_ct = ContentType.objects.get_for_model(self.driver.__class__)
            expenses = ShipmentExpense.objects.filter(
                shipment=self.shipment,
                content_type=driver_ct,
                object_id=self.driver.id
            )
            total_expenses = sum(e.amount or Decimal('0') for e in expenses)
            return (self.amount or Decimal('0')) + self.carried_forward - total_expenses
        return self.amount or Decimal('0')

    def get_expense_breakdown(self):
        if not self.shipment:
            return []

        driver_ct = ContentType.objects.get_for_model(self.driver.__class__)
        expenses = ShipmentExpense.objects.filter(
            shipment=self.shipment,
            content_type=driver_ct,
            object_id=self.driver.id
        ).select_related('expense_type')

        return [
            {
                "id": e.id,
                "date": e.expense_date,
                "expense_type": str(e.expense_type) if e.expense_type else "Other",
                "amount": e.amount or Decimal('0'),
                "description": e.description or ""
            } for e in expenses
        ]

    def advance_breakdown(self):
        expenses = self.get_expense_breakdown()
        total_expenses = sum(e['amount'] for e in expenses)
        remaining = (self.amount or Decimal('0')) + self.carried_forward - total_expenses

        return {
            "advance_id": self.id,
            "driver": {
                "id": self.driver.id,
                "name": f"{self.driver.first_name} {self.driver.last_name}",
                "phone": getattr(self.driver, 'phone_number', '')
            },
            "shipment": {
                "id": self.shipment.id if self.shipment else None,
                "name": str(self.shipment) if self.shipment else "General Advance"
            },
            "date_issued": self.date,
            "advance_amount": self.amount or Decimal('0'),
            "description": self.description or "",
            "carried_forward": self.carried_forward or Decimal('0'),
            "total_available": (self.amount or Decimal('0')) + (self.carried_forward or Decimal('0')),
            "expenses": expenses,
            "total_expenses": total_expenses,
            "remaining_balance": remaining,
            "settlement_status": "settled" if remaining <= 0 else "unsettled",
            "is_settled": self.is_settled
        }

    def get_unsettled_balance(self):
        unsettled_advances = DriverAdvance.objects.filter(driver=self.driver, is_settled=False)
        return sum(a.remaining_balance() for a in unsettled_advances)

    @staticmethod
    def create_driver_advance(driver, shipment, amount, description=""):
        previous_advances = DriverAdvance.objects.filter(driver=driver, is_settled=False)
        carry_balance = sum(a.remaining_balance() for a in previous_advances)

        new_advance = DriverAdvance.objects.create(
            driver=driver,
            shipment=shipment,
            amount=amount,
            description=description,
            carried_forward=carry_balance
        )

        # Mark previous advances as settled since balance is carried forward
        previous_advances.update(is_settled=True)
        return new_advance

    @staticmethod
    def get_driver_summary(driver, shipment=None):
        query = DriverAdvance.objects.filter(driver=driver)
        if shipment:
            query = query.filter(shipment=shipment)

        advances = query.select_related('shipment', 'driver')

        summary = {
            "driver": {
                "id": driver.id,
                "name": f"{driver.first_name} {driver.last_name}",
                "phone": getattr(driver, 'phone_number', '')
            },
            "total_advances": len(advances),
            "total_advance_amount": sum(a.amount or Decimal('0') for a in advances),
            "total_expenses": sum(a.total_expenses or Decimal('0') for a in advances),
            "total_carried_forward": sum(a.carried_forward or Decimal('0') for a in advances),
            "settled_advances": len([a for a in advances if a.is_settled]),
            "unsettled_advances": len([a for a in advances if not a.is_settled]),
            "advances": [a.advance_breakdown() for a in advances]
        }
        return summary

    @classmethod
    def recompute_chain_for_driver(cls, driver_id):
        """
        Recompute the entire DriverAdvance chain for a driver.
        Ensures correct carried_forward and settlement across all rows.
        """
        advances = cls.objects.filter(driver_id=driver_id).order_by("date", "id")

        carried = 0
        for adv in advances:
            # Apply your existing logic
            adv.carried_forward = carried + adv.amount
            adv.is_settled = (adv.carried_forward == 0)
            adv.save(update_fields=["carried_forward", "is_settled"])

            carried = adv.carried_forward

    # def _previous_advance_same_shipment(self):
    #     if not self.shipment_id:
    #         return None
    #     return (
    #         DriverAdvance.objects
    #         .filter(driver_id=self.driver_id, shipment_id=self.shipment_id)
    #         .exclude(pk=self.pk)
    #         .order_by('id', 'date',)
    #         .last()
    #     )

class Diesel(models.Model):
    PAYMENT_MODE_CHOICES = (
        ('ONLINE', 'Online'),
        ('CASH', 'Cash'),
    )

    # Relations
    vehicle = models.ForeignKey(
        'entity.Vehicle',
        on_delete=models.CASCADE,
        related_name='diesel_entries'
    )



    driver = models.ForeignKey(
        'entity.Driver',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Basic Info
    date = models.DateField()

    description = models.TextField(
        help_text="Transfer description and purpose",
        blank=True,
        null=True
    )

    # Diesel Details
    price_per_ltr = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Odometer & Calculated Fields
    full_km = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Odometer reading",
        null=True,
        blank=True
    )

    mileage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    rs_per_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Payment Info
    payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    payment_mode = models.CharField(
        max_length=10,
        choices=PAYMENT_MODE_CHOICES
    )

    location = models.ForeignKey(
        'configuration.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='diesel_location',
        help_text="Select location from dropdown"
    )

    driver_taken_cash = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Documents
    upload_doc = models.FileField(
        upload_to='diesel_slips/',
        null=True,
        blank=True
    )

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle} | {self.date} | {self.quantity} L"

    def save(self, *args, **kwargs):

        # 1️⃣ Auto-calc total price
        if self.price_per_ltr and self.quantity:
            self.total_price = self.price_per_ltr * self.quantity
        else:
            self.total_price = 0

        # 2️⃣ Auto-calc payment based on driver_taken_cash
        if self.driver_taken_cash and self.driver_taken_cash > 0:
            self.payment = self.total_price + self.driver_taken_cash
        else:
            self.payment = self.total_price

        # 3️⃣ Auto-calc mileage (optional)
        if self.full_km and self.quantity:
            try:
                self.mileage = self.full_km / self.quantity
            except:
                self.mileage = None

        # 4️⃣ Auto-calc Rs per km (optional)
        if self.total_price and self.full_km:
            try:
                self.rs_per_km = self.total_price / self.full_km
            except:
                self.rs_per_km = None

        super().save(*args, **kwargs)


