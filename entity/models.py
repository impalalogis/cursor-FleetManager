from django.db import models
from django.apps import apps
import uuid
from utils.validators import *
from django.utils.translation import gettext_lazy as _
import os
from django.core.exceptions import ValidationError
from datetime import date
import re

from configuration.constants import ChoiceCategory


class AddressMixin(models.Model):
    """
    Mixin class that provides address fields with pincode-based auto-population
    """
    address_line_1 = models.CharField(max_length=255, validators=[non_empty_text_validator], null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    locality = models.CharField(max_length=100, null=True, blank=True,
                                help_text="E.g. Near Metro Station or Market Name")
    city = models.CharField(max_length=100, validators=[non_empty_text_validator], null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=6, validators=[pincode_validator], null=True, blank=True)
    landmark = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        abstract = True

    def auto_populate_from_pincode(self, pincode_field='pincode', prefix=''):
        """
        Auto-populate address fields based on pincode

        Args:
            pincode_field: Name of the pincode field to use
            prefix: Prefix for field names (e.g., 'family_' for family address)
        """
        pincode_value = getattr(self, pincode_field, None)
        if pincode_value:
            try:
                pincode_int = int(pincode_value)
                PostalInfo = apps.get_model('configuration', 'PostalInfo')
                details = PostalInfo.get_postal_details(pincode_int)

                if details:
                    # Only update fields that are currently empty
                    state_field = f"{prefix}state" if prefix else "state"
                    district_field = f"{prefix}district" if prefix else "district"
                    city_field = f"{prefix}city" if prefix else "city"
                    locality_field = f"{prefix}locality" if prefix else "locality"

                    if hasattr(self, state_field) and not getattr(self, state_field):
                        setattr(self, state_field, details.get("statename"))

                    if hasattr(self, district_field) and not getattr(self, district_field):
                        setattr(self, district_field, details.get("Districtname"))

                    if hasattr(self, city_field) and not getattr(self, city_field):
                        setattr(self, city_field, details.get("Taluk"))

                    if hasattr(self, locality_field) and not getattr(self, locality_field):
                        setattr(self, locality_field, details.get("officename"))
            except (ValueError, TypeError):
                # Invalid pincode format, skip auto-population
                pass

    def get_formatted_address(self):
        """Return formatted address string"""
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            self.locality,
            self.city,
            self.district,
            self.state,
            self.country,
            self.pincode
        ]
        return ', '.join(filter(None, address_parts))

    def is_address_complete(self):
        """Check if minimum required address fields are filled"""
        return bool(self.address_line_1 and self.city and self.state and self.pincode)


class ContactMixin(models.Model):
    """
    Abstract base class for contact information.
    Provides standardized contact fields across all models.
    """
    contact_person = models.CharField(max_length=100, null=True, blank=True, help_text="Primary contact person name")
    contact_phone = models.CharField(max_length=10, validators=[indian_phone_validator], null=True, blank=True,
                                     help_text="Contact phone number")
    contact_email = models.EmailField(null=True, blank=True, help_text="Contact email address")
    phone_number = models.CharField(max_length=10, validators=[indian_phone_validator], unique=True, null=True,
                                    blank=True, help_text="Legacy phone field - use contact_phone instead")
    email = models.EmailField(null=True, blank=True, help_text="Legacy email field - use contact_email instead")

    class Meta:
        abstract = True

    def get_contact_summary(self):
        """Return formatted contact information"""
        return {
            'person': self.contact_person,
            'phone': self.contact_phone,
            'email': self.contact_email
        }

    def has_contact_info(self):
        """Check if any contact information is provided"""
        return bool(self.contact_person or self.contact_phone or self.contact_email)


class PersonMixin(models.Model):
    """
    Abstract base class for personal details.
    Eliminates duplication across Broker, Transporter, Driver, and Owner models.
    """
    # Personal Details
    title = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_title_set',
        limit_choices_to={'category': ChoiceCategory.PERSON_TITLE},
    )
    first_name = models.CharField(max_length=50, validators=[name_no_digits_validator], null=False, blank=True)
    middle_name = models.CharField(max_length=50, validators=[name_no_digits_validator], blank=True)
    last_name = models.CharField(max_length=50, validators=[name_no_digits_validator], null=True, blank=True)
    date_of_birth = models.DateField(validators=[birthdate_validator, age_validator], default="1947-01-01")
    gender = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_gender_set',
        limit_choices_to={'category': ChoiceCategory.PERSON_GENDER},
    )

    class Meta:
        abstract = True

    def calculate_age(self):
        """Calculate age from date of birth"""
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    @property
    def age(self):
        return self.calculate_age()

    @property
    def full_name(self):
        """Get formatted full name"""
        parts = [
            str(self.title) if self.title else "",
            self.first_name or "",
            self.middle_name or "",
            self.last_name or ""
        ]
        return " ".join(filter(None, parts)).strip()

    def __str__(self):
        return self.full_name or f"{self.__class__.__name__} {self.pk}"


class BusinessEntityMixin(models.Model):
    """
    Abstract base class for business-related fields.
    Used by entities that conduct business (Broker, Transporter, Owner).
    """
    # Business Documentation
    GST_NO = models.CharField(max_length=15, validators=[gst_validator], null=True, blank=True)
    GST_document = models.FileField(upload_to=user_document_upload_path, validators=[document_file_validator],
                                    null=True, blank=True)

    class Meta:
        abstract = True


class Comman(models.Model):
    """
    Common base class that provides address, contact, and banking fields.
    Optimized to use consolidated mixins and eliminate redundancy.
    """
    # # Common Documents
    aadhaar = models.CharField(max_length=12, validators=[aadhaar_validator], null=True, blank=True)
    aadhaar_document = models.FileField(upload_to=user_document_upload_path, validators=[document_file_validator],
                                        null=True, blank=True)
    pan_number = models.CharField(max_length=10, validators=[pan_validator], null=True, blank=True)
    pan_document = models.FileField(upload_to=user_document_upload_path, validators=[document_file_validator],
                                    null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    notes = models.CharField(max_length=1000, null=True, blank=True)
    # Audit
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    created_by = models.ForeignKey(
        'users.CustomUser',
        related_name='created_%(class)s_set',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_by = models.ForeignKey(
        'users.CustomUser',
        related_name='updated_%(class)s_set',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        abstract = True


class Organization(AddressMixin, BusinessEntityMixin, ContactMixin):
    """
    Enhanced Organization model serving as the primary tenant model.
    Each organization represents a separate tenant in the multi-tenant architecture.
    """

    objects = None
    organization_number = models.CharField(
        max_length=10,
        unique=True,
        editable=False,
        help_text="Auto-generated organization number in format ORG-00001"
    )

    # parent_organization_name = models.CharField(max_length=50, validators=[name_no_digits_validator], null=False, blank=True)
    organization_name = models.CharField(max_length=50, validators=[name_no_digits_validator], null=False, blank=True)
    organization_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organization_type_members',
        limit_choices_to={'category': ChoiceCategory.ORGANIZATION_TYPE},
        help_text="Type of organization",
    )
    location = models.ForeignKey(
        'configuration.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organizations',
        help_text="Select location from dropdown"
    )

    pan_number = models.CharField(max_length=10, validators=[pan_validator], null=True, blank=True)
    pan_document = models.FileField(upload_to=user_document_upload_path, validators=[document_file_validator],
                                    null=True, blank=True)
    tds_declaration = models.FileField(upload_to=user_document_upload_path, validators=[document_file_validator],
                                       null=True, blank=True)
    route = models.ForeignKey('configuration.Route', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='%(class)s_routes', help_text="Primary route of operation")
    notes = models.CharField(max_length=1000, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.auto_populate_from_pincode()
        if not self.organization_number:
            existing_numbers = Organization.objects.values_list('organization_number', flat=True)
            max_number = 0
            pattern = re.compile(r'ORG(\d{5})')

            for number in existing_numbers:
                match = pattern.match(number)
                if match:
                    num = int(match.group(1))
                    if num > max_number:
                        max_number = num

            self.organization_number = f"ORG{max_number + 1:05d}"

        self.auto_populate_from_pincode()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'organization'
        ordering = ['organization_name']
        indexes = [
            models.Index(fields=['organization_type'], name='organization_type_idx'),
        ]

    def __str__(self):
        # location_name = str(self.location) if self.location else "No Location"
        return f"{self.organization_name}"

    @property
    def organization_type_code(self):
        return self.organization_type.internal_value if self.organization_type else None

    @property
    def organization_type_label(self):
        return self.organization_type.display_value if self.organization_type else None

    def is_broker(self):
        """Check if this organization is classified as a broker"""
        return self.organization_type_code == 'BROKER'

    def is_transporter(self):
        """Check if this organization is classified as a transporter"""
        return self.organization_type_code == 'TRANSPORTER'

    def is_company(self):
        """Check if this organization is classified as a company"""
        return self.organization_type_code == 'CONSIGNOR-AND-CONSIGNEE'

    def is_owner(self):
        """Check if this organization is classified as an owner"""
        return self.organization_type_code == 'OWNER'

    @classmethod
    def get_brokers(cls):
        """Get all organizations classified as brokers"""
        return cls.objects.filter(organization_type__internal_value='BROKER')

    @classmethod
    def get_transporters(cls):
        """Get all organizations classified as transporters"""
        return cls.objects.filter(organization_type__internal_value='TRANSPORTER')

    @classmethod
    def get_companies(cls):
        """Get all organizations classified as companies"""
        return cls.objects.filter(organization_type__internal_value='CONSIGNOR-AND-CONSIGNEE')

    @classmethod
    def get_owners(cls):
        """Get all organizations classified as owners"""
        return cls.objects.filter(organization_type__internal_value='OWNER')

    def latest_document(self, doc_type):
        queryset = self.documents.all()
        if isinstance(doc_type, str):
            return queryset.filter(doc_type__internal_value=doc_type).order_by('-uploaded_at').first()
        return queryset.filter(doc_type=doc_type).order_by('-uploaded_at').first()

    def documents_by_type(self):
        Choice = apps.get_model('configuration', 'Choice')
        doc_types = Choice.objects.filter(category='ORGANIZATION_DOCUMENT_TYPE').order_by('display_value')
        out = {}
        for choice in doc_types:
            out[choice.internal_value] = list(
                self.documents.filter(doc_type=choice).order_by('-uploaded_at')
            )
        return out


# Create your models here.
# --- add near vehicle_document_path ---


def _sanitize_for_filename(value, default="NA"):
    value = str(value or default)
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    sanitized = value.strip("_")
    return sanitized or default


def driver_document_path(instance, filename):
    doc_code = _sanitize_for_filename(getattr(instance.doc_type, "internal_value", instance.doc_type_id) or "document",
                                      "document")
    doc_no = _sanitize_for_filename(instance.doc_no)
    """
    Store files under: drivers/<DRIVER_PK or NAME>/documents/<filename>
    """
    first_name = _sanitize_for_filename(getattr(instance.driver, 'first_name', None), "unknown")
    last_name = _sanitize_for_filename(getattr(instance.driver, 'last_name', None), "")
    driver_pk = instance.driver.pk if instance.driver_id else "driver"
    base = _sanitize_for_filename(f"{driver_pk}_{last_name}_{first_name}", f"driver_{driver_pk}")
    local_filename = f"{doc_code}_{doc_no}_{base}_{filename}"
    return os.path.join("drivers", base, "documents", local_filename)


def organization_document_path(instance, filename):
    doc_code = _sanitize_for_filename(getattr(instance.doc_type, "internal_value", instance.doc_type_id) or "document",
                                      "document")
    doc_no = _sanitize_for_filename(instance.doc_no)
    org_number = _sanitize_for_filename(instance.organization.organization_number or f"org_{instance.organization.pk}",
                                        "org")
    org_name = _sanitize_for_filename(getattr(instance.organization, 'organization_name', None), "organization")
    org_segment = _sanitize_for_filename(f"{org_number}_{org_name}", org_number)
    local_filename = f"{doc_code}_{doc_no}_{org_segment}_{filename}"
    return os.path.join("organizations", org_segment, "documents", local_filename)


class DriverDocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    driver = models.ForeignKey(
        'entity.Driver',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    doc_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.PROTECT,
        related_name='driver_documents',
        limit_choices_to={'category': ChoiceCategory.DRIVER_DOCUMENT_TYPE}
    )
    file = models.FileField(upload_to=driver_document_path)  # add validators if you wish
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    doc_no = models.CharField(max_length=60, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "driver_document"
        indexes = [
            models.Index(fields=["driver", "doc_type"]),
            models.Index(fields=["uploaded_at"]),
        ]
        ordering = ["-uploaded_at"]

    def __str__(self):
        label = self.doc_type.display_value if self.doc_type else "Unknown"
        return f"{self.driver.full_name} - {label}"

    @property
    def doc_type_code(self):
        return self.doc_type.internal_value if self.doc_type else None

    @property
    def doc_type_label(self):
        return self.doc_type.display_value if self.doc_type else None

    def clean(self):
        # Example rule: LICENSE usually has expiry
        if self.doc_type and self.doc_type.internal_value == 'LICENSE' and not self.expiry_date:
            # Make strict if needed:
            # raise ValidationError({"expiry_date": "Expiry date is required for Driving License."})
            pass


class OrganizationDocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        'entity.Organization',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    doc_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.PROTECT,
        related_name='organization_documents',
        limit_choices_to={'category': ChoiceCategory.ORGANIZATION_DOCUMENT_TYPE}
    )
    file = models.FileField(upload_to=organization_document_path)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    doc_no = models.CharField(max_length=60, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organization_document'
        indexes = [
            models.Index(fields=['organization', 'doc_type']),
            models.Index(fields=['uploaded_at']),
        ]
        ordering = ['-uploaded_at']

    def __str__(self):
        label = self.doc_type.display_value if self.doc_type else 'Unknown'
        return f"{self.organization.organization_name} - {label}"

    @property
    def doc_type_code(self):
        return self.doc_type.internal_value if self.doc_type else None

    @property
    def doc_type_label(self):
        return self.doc_type.display_value if self.doc_type else None


class Driver(PersonMixin, ContactMixin, AddressMixin):
    """
    Driver model - Industry Standard Implementation.
    IMPORTANT: Every driver MUST belong to an owner organization (industry standard).
    Drivers work for vehicle owners and operate their vehicles.
    """
    # Industry Standard: Driver always belongs to an Owner organization
    owner = models.ForeignKey(
        'Organization',
        on_delete=models.PROTECT,
        related_name='drivers',
        help_text="Owner organization this driver works for (REQUIRED - industry standard)",
        limit_choices_to={'organization_type__internal_value': 'OWNER'}
    )

    # Driver-specific documents and credentials
    license_number = models.CharField(max_length=30, unique=True, validators=[indian_license_validator],
                                      null=True, blank=True, help_text="Driving license number")
    license_document = models.FileField(upload_to=user_document_upload_path, validators=[document_file_validator],
                                        null=True, blank=True, help_text="Driving license document")
    license_expiry = models.DateField(null=True, blank=True, help_text="License expiry date")

    # Family_Address
    family_name = models.CharField(max_length=255, validators=[non_empty_text_validator], null=True, blank=True)
    family_address_line_1 = models.CharField(max_length=255, validators=[non_empty_text_validator], null=True,
                                             blank=True)
    family_address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    family_locality = models.CharField(max_length=100, null=True, blank=True,
                                       help_text="E.g. Near Metro Station or Market Name")
    family_city = models.CharField(max_length=100, validators=[non_empty_text_validator], null=True, blank=True)
    family_district = models.CharField(max_length=100, null=True, blank=True)
    family_state = models.CharField(max_length=100, null=True, blank=True)
    family_country = models.CharField(max_length=100, default='India')
    family_pincode = models.CharField(max_length=6, validators=[pincode_validator], null=True, blank=True)
    family_landmark = models.CharField(max_length=255, null=True, blank=True)
    family_phone_number = models.CharField(max_length=10, validators=[indian_phone_validator], unique=True, null=True,
                                           blank=True)
    is_active = models.BooleanField(default=False, help_text="Whether Driver is active or not")

    # contact_person = models.CharField(max_length=100, default="Unknown",null=True, blank=True)
    def save(self, *args, **kwargs):

        self.auto_populate_from_pincode()
        self.auto_populate_from_pincode(pincode_field='family_pincode', prefix='family_')
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'driver'
        ordering = ['first_name', 'middle_name', 'last_name']
        indexes = [
            models.Index(fields=['owner']),  # Primary relationship index
            models.Index(fields=['license_number']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['license_number'], condition=models.Q(license_number__isnull=False),
                                    name='unique_driver_license'),
        ]

    def __str__(self):
        # return f"{self.id} - {self.full_name} (owner: {self.owner})"
        return f"{self.id} - {self.full_name}"

    @property
    def current_vehicle(self):
        """Get the vehicle currently assigned to this driver"""
        # This would be determined by recent shipments or assignments
        from operations.models import Shipment
        recent_shipment = Shipment.objects.filter(driver=self).order_by('-actual_departure').first()
        return recent_shipment.vehicle if recent_shipment else None

    @property
    def license_status(self):
        """Check if license is valid"""
        if not self.license_expiry:
            return "Unknown"
        today = date.today()
        if today > self.license_expiry:
            return "Expired"
        elif (self.license_expiry - today).days <= 30:
            return "Expiring Soon"
        return "Valid"

    def driver_advance_summary(self):
        from django.contrib.contenttypes.models import ContentType

        DriverAdvance = apps.get_model('operations', 'DriverAdvance')
        ShipmentExpense = apps.get_model('operations', 'ShipmentExpense')
        advances = DriverAdvance.objects.filter(driver=self)

        # Get ContentType for Driver model
        driver_content_type = ContentType.objects.get_for_model(self)
        expenses = ShipmentExpense.objects.filter(
            content_type=driver_content_type,
            object_id=self.id
        )

        total_advance = sum(a.amount + a.carried_forward for a in advances)
        total_expense = sum(e.amount for e in expenses if e.amount)
        balance = total_advance - total_expense

        return {
            "total_advance": total_advance,
            "total_expense": total_expense,
            "balance": balance,
            "unsettled_balance": sum(a.remaining_balance() for a in advances if not a.is_settled)
        }

    def driver_advance_breakdown(self):
        """Detailed breakdown of all advances for this driver"""
        DriverAdvance = apps.get_model('operations', 'DriverAdvance')
        advances = DriverAdvance.objects.filter(driver=self).order_by('-date')

        return {
            "driver": f"{self.first_name} {self.last_name}",
            "driver_id": self.id,
            "summary": self.driver_advance_summary(),
            "advances": [advance.advance_breakdown() for advance in advances],
            "unsettled_advances": [
                advance.advance_breakdown()
                for advance in advances
                if not advance.is_settled and advance.remaining_balance() > 0
            ]
        }

    def get_current_balance(self):
        """Get current unsettled balance for this driver"""
        DriverAdvance = apps.get_model('operations', 'DriverAdvance')
        unsettled_advances = DriverAdvance.objects.filter(driver=self, is_settled=False)
        return sum(a.remaining_balance() for a in unsettled_advances)

    def latest_document(self, doc_type: str):
        queryset = self.documents.all()
        if isinstance(doc_type, str):
            return queryset.filter(doc_type__internal_value=doc_type).order_by('-uploaded_at').first()
        return queryset.filter(doc_type=doc_type).order_by('-uploaded_at').first()

    def documents_by_type(self):
        """Return dict of documents grouped by driver document type internal value."""
        Choice = apps.get_model('configuration', 'Choice')
        doc_types = Choice.objects.filter(category='DRIVER_DOCUMENT_TYPE').order_by('display_value')
        out = {}
        for choice in doc_types:
            out[choice.internal_value] = list(
                self.documents.filter(doc_type=choice).order_by('-uploaded_at')
            )
        return out


def vehicle_document_path(instance, filename):
    """
    Store files under: vehicles/<REG_NO>/documents/<filename>
    """
    reg = _sanitize_for_filename(instance.vehicle.registration_number, "unknown")
    doc_code = _sanitize_for_filename(getattr(instance.doc_type, "internal_value", instance.doc_type_id) or "document",
                                      "document")
    local_filename = f"{doc_code}_{reg}_{filename}"
    return os.path.join("vehicles", reg, "documents", local_filename)


class VehicleDocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    vehicle = models.ForeignKey(
        'entity.Vehicle',  # if Vehicle is in app "entity"
        on_delete=models.CASCADE,
        related_name='documents'
    )
    doc_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.PROTECT,
        related_name='vehicle_documents',
        limit_choices_to={'category': ChoiceCategory.VEHICLE_DOCUMENT_TYPE}
    )
    file = models.FileField(
        upload_to=vehicle_document_path,  # or your user_document_upload_path
        # validators=[document_file_validator],  # uncomment if you use it
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vehicle_document"
        indexes = [
            models.Index(fields=["vehicle", "doc_type"]),
            models.Index(fields=["uploaded_at"]),
        ]
        ordering = ["-uploaded_at"]

    def __str__(self):
        label = self.doc_type.display_value if self.doc_type else "Unknown"
        return f"{self.vehicle.registration_number} - {label}"

    @property
    def doc_type_code(self):
        return self.doc_type.internal_value if self.doc_type else None

    @property
    def doc_type_label(self):
        return self.doc_type.display_value if self.doc_type else None

    def clean(self):
        # Example soft validation: some doc types typically have expiry
        if (
                self.doc_type
                and self.doc_type.internal_value in {"INSURANCE", "POLLUTION"}
                and not self.expiry_date
        ):
            # Make this a hard rule if you want:
            # raise ValidationError({"expiry_date": "Expiry date is required for this document type."})
            pass


class Vehicle(models.Model):
    """
    Enhanced Vehicle model with UUID primary key and comprehensive vehicle specifications.
    Vehicles are associated with tenants through their owner's organization.
    """
    # UUID Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Registration and Identification
    registration_number = models.CharField(max_length=20, unique=True,
                                           help_text="Vehicle registration number (e.g., MH12AB123)")
    chassis_number = models.CharField(max_length=50, unique=True, help_text="Chassis number for vehicle identification")
    # vehicle_number = models.CharField(max_length=50, unique=True, help_text="Vehicles number for identification")

    # Choice-based fields for consistency
    brand_name = models.ForeignKey('configuration.Choice', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='vehicle_brand_choice_set',
                                   limit_choices_to={'category': ChoiceCategory.VEHICLE_BRAND},
                                   help_text="Brand from predefined choices")
    model_name = models.ForeignKey('configuration.Choice', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='vehicle_model_choice_set',
                                   limit_choices_to={'category': ChoiceCategory.VEHICLE_MODEL},
                                   help_text="Model from predefined choices")
    truck_type = models.ForeignKey('configuration.Choice', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='vehicle_truck_type_set',
                                   limit_choices_to={'category': ChoiceCategory.VEHICLE_TRUCK_TYPE},
                                   help_text="Truck type from predefined choices")
    engine_type = models.ForeignKey('configuration.Choice', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='vehicle_engine_type_set',
                                    limit_choices_to={'category': ChoiceCategory.VEHICLE_ENGINE_TYPE},
                                    help_text="Engine type from predefined choices")
    fuel_type = models.ForeignKey('configuration.Choice', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='vehicle_fuel_choice_set',
                                  limit_choices_to={'category': ChoiceCategory.VEHICLE_FUEL_TYPE},
                                  help_text="Fuel type from predefined choices")
    body_type = models.ForeignKey('configuration.Choice', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='vehicle_body_type_set',
                                  limit_choices_to={'category': ChoiceCategory.VEHICLE_BODY_TYPE},
                                  help_text="Body type from predefined choices")
    truck_specification = models.ForeignKey('configuration.Choice', on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='vehicle_specification_set',
                                            limit_choices_to={'category': ChoiceCategory.VEHICLE_SPECIFICATION},
                                            help_text="Truck specification from predefined choices")

    wheel_count = models.ForeignKey('configuration.Choice', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='vehicle_wheels_type_set',
                                    limit_choices_to={'category': ChoiceCategory.VEHICLE_WHEEL_CONFIGURATION},
                                    help_text="Number of wheels (e.g., 6, 10, 12)")

    load_capacity_tons = models.ForeignKey('configuration.Choice', on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='vehicle_capacity_type_set',
                                           limit_choices_to={'category': ChoiceCategory.VEHICLE_CAPACITY_TONNAGE},
                                           help_text="Gross Vehicle Weight (e.g., 28T, 16.2T)")

    # Maintenance and Compliance
    maintenance_due_date = models.DateField(null=True, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    fitness_certificate_expiry = models.DateField(null=True, blank=True)
    pollution_certificate_expiry = models.DateField(null=True, blank=True)

    # Ownership and Location
    owner = models.ForeignKey(
        'Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicles',
        limit_choices_to={'organization_type__internal_value': 'OWNER'},
        help_text="Owner organization responsible for this vehicle"
    )
    # state_registered = models.CharField(max_length=50, null=True, blank=True, help_text="State where vehicle is registered")
    state_registered = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vechile_state_set',
        limit_choices_to={'category': ChoiceCategory.LOCATION_STATE},
        help_text="State where vehicle is registered"
    )
    # Status
    is_active = models.BooleanField(default=True, help_text="Whether vehicle is active in fleet")

    class Meta:
        db_table = 'vehicle'
        indexes = [
            models.Index(fields=['owner']),  # For tenant filtering through owner
            models.Index(fields=['registration_number']),
            models.Index(fields=['chassis_number']),
            models.Index(fields=['is_active']),
            models.Index(fields=['brand_name', 'model_name']),
            models.Index(fields=['truck_type']),
            # models.Index(fields=['created_at']),
        ]

    def clean(self):
        """Custom validation for vehicle data"""
        super().clean()

        # Validate GVW format
        if self.load_capacity_tons and not self.load_capacity_tons:
            raise ValidationError({'load_capacity_tons': 'load_capacity_tons must end with "T" (e.g., "28T")'})

        # Validate wheel count
        # if self.wheel_count:
        #     raise ValidationError({'wheel_count': 'Wheel count must be at least 4'})

    def save(self, *args, **kwargs):
        """Enhanced save method with auto-population from choices"""

        super().save(*args, **kwargs)

    def __str__(self):
        # return f"{self.registration_number} - {self.brand_name} {self.model_name}"
        return f"{self.registration_number}"

    def get_vehicle_summary(self):
        """Return comprehensive vehicle information"""
        return {
            'id': str(self.id),
            'registration_number': self.registration_number,
            'chassis_number': self.chassis_number,
            'brand_model': f"{self.brand_name} {self.model_name}",
            'specifications': {
                'truck_type': self.truck_type,
                'engine_type': self.engine_type,
                'fuel_type': self.fuel_type,
                'body_type': self.body_type,
                'wheel_count': self.wheel_count,
                'load_capacity_tons': self.load_capacity_tons

            },
            'owner': str(self.owner) if self.owner else None,
            'is_active': self.is_active,
        }

    @property
    def is_maintenance_due(self):
        """Check if maintenance is due"""
        if not self.maintenance_due_date:
            return False
        return date.today() >= self.maintenance_due_date

    @property
    def compliance_status(self):
        """Check compliance status for various certificates"""
        today = date.today()
        status = {}

        if self.insurance_expiry:
            status['insurance'] = 'valid' if today < self.insurance_expiry else 'expired'
        if self.fitness_certificate_expiry:
            status['fitness'] = 'valid' if today < self.fitness_certificate_expiry else 'expired'
        if self.pollution_certificate_expiry:
            status['pollution'] = 'valid' if today < self.pollution_certificate_expiry else 'expired'

        return status

    def latest_document(self, doc_type: str):
        """Return most recent document for a given document type."""
        queryset = self.documents.all()
        if isinstance(doc_type, str):
            return queryset.filter(doc_type__internal_value=doc_type).order_by('-uploaded_at').first()
        return queryset.filter(doc_type=doc_type).order_by('-uploaded_at').first()

    def documents_by_type(self):
        """Return dict: {doc_type: [VehicleDocument, ...]}"""
        Choice = apps.get_model('configuration', 'Choice')
        doc_types = Choice.objects.filter(category='VEHICLE_DOCUMENT_TYPE').order_by('display_value')
        out = {}
        for choice in doc_types:
            out[choice.internal_value] = list(
                self.documents.filter(doc_type=choice).order_by('-uploaded_at')
            )
        return out

