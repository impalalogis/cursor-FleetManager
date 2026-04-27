from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.validators import *

from .constants import ChoiceCategory


# Create your models here.
class Location(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'location'


class Route(models.Model):
    source = models.CharField(max_length=100, unique=True, blank=True, null=True)
    via = models.CharField(max_length=100, unique=True, blank=True, null=True)
    destination = models.CharField(max_length=100, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.source} - {self.via} -{self.destination}"

    class Meta:
        db_table = 'route'


class BankingDetail(models.Model):
    """
    Enhanced Banking Details model for comprehensive online banking integration
    """
    ACCOUNT_TYPE_CHOICES = [
        ('SAVINGS', 'Savings Account'),
        ('CURRENT', 'Current Account'),
        ('BUSINESS', 'Business Account'),
        ('OVERDRAFT', 'Overdraft Account'),
        ('JOINT', 'Joint Account'),
    ]

    BANKING_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('SUSPENDED', 'Suspended'),
        ('CLOSED', 'Closed'),
        ('PENDING_VERIFICATION', 'Pending Verification'),
    ]

    VERIFICATION_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('VERIFIED', 'Verified'),
        ('FAILED', 'Failed'),
        ('REJECTED', 'Rejected'),
    ]

    # Basic account information
    account_holder_name = models.CharField(max_length=255, validators=[name_no_digits_validator])
    bank_name = models.CharField(max_length=255, validators=[non_empty_text_validator])
    account_number = models.CharField(max_length=50, validators=[bank_account_validator])
    account_type = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='banking_account_type_set',
        limit_choices_to={'category': ChoiceCategory.BANK_ACCOUNT_TYPE},
        help_text=_("Type of bank account (managed via configuration choices)"),
    )

    # Indian banking specific fields
    ifsc_code = models.CharField(max_length=11, validators=[ifsc_validator], help_text="Indian Financial System Code")
    branch_name = models.CharField(max_length=255, null=True, blank=True)
    branch_address = models.CharField(max_length=255, null=True, blank=True)
    branch_city = models.CharField(max_length=100, null=True, blank=True)
    branch_state = models.CharField(max_length=100, null=True, blank=True)
    branch_pincode = models.CharField(max_length=6, validators=[pincode_validator], null=True, blank=True)

    # Digital payment options
    # upi_id = models.CharField(max_length=100, validators=[upi_validator], null=True, blank=True, help_text="UPI ID for digital payments")
    # mobile_number = models.CharField(max_length=10, validators=[indian_phone_validator], null=True, blank=True, help_text="Registered mobile number")

    # Online banking credentials (for API integration)
    # customer_id = models.CharField(max_length=50, null=True, blank=True, help_text="Bank customer ID")
    # user_id = models.CharField(max_length=50, null=True, blank=True, help_text="Net banking user ID")

    # Status and verification
    # status = models.CharField(max_length=20, choices=BANKING_STATUS_CHOICES, default='PENDING_VERIFICATION')
    # verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='PENDING')
    # verification_date = models.DateTimeField(null=True, blank=True)

    # Additional fields for integration
    # is_primary = models.BooleanField(default=False, help_text="Primary banking account")
    # is_enabled_for_auto_transfer = models.BooleanField(default=False, help_text="Enable automatic transfers")
    # daily_transaction_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # monthly_transaction_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # API integration fields
    # api_key = models.CharField(max_length=255, null=True, blank=True, help_text="Banking API key")
    # api_secret = models.CharField(max_length=255, null=True, blank=True, help_text="Banking API secret")
    # last_sync_datetime = models.DateTimeField(null=True, blank=True, help_text="Last API sync timestamp")

    def __str__(self):
        acct_suffix = self.account_number[-4:] if self.account_number else "----"
        return f"{self.account_holder_name} - {self.bank_name} ({acct_suffix})"

    def get_masked_account_number(self):
        """Return masked account number for security"""
        if not self.account_number:
            return None
        if len(self.account_number) > 4:
            return 'X' * (len(self.account_number) - 4) + self.account_number[-4:]
        return self.account_number

    @property
    def account_type_code(self):
        return self.account_type.internal_value if self.account_type else None

    @property
    def account_type_display(self):
        return self.account_type.display_value if self.account_type else None

    def get_account_type_display(self):
        """Compatibility helper for legacy serializer usage."""
        return self.account_type_display

    # def is_verified(self):
    #     """Check if banking details are verified"""
    #     return self.verification_status == 'VERIFIED'

    # def is_active(self):
    #     """Check if banking account is active"""
    #     return self.status == 'ACTIVE'

    # def can_process_transactions(self):
    #     """Check if account can process transactions"""
    #     return self.is_active() and self.is_verified()

    class Meta:
        db_table = 'banking_detail'
        verbose_name = 'Banking Detail'
        verbose_name_plural = 'Banking Details'

    # def get_linked_entities(self):
    #     """Get all entities linked to this banking detail"""
    #     linked_entities = []
    #
    #     # Check drivers
    #     drivers = self.drivers.all()
    #     for driver in drivers:
    #         linked_entities.append({
    #             'type': 'Driver',
    #             'name': str(driver),
    #             'id': driver.id,
    #             'is_primary': driver.primary_banking_detail == self
    #         })
    #
    #     # Check brokers
    #     brokers = self.brokers.all()
    #     for broker in brokers:
    #         linked_entities.append({
    #             'type': 'Broker',
    #             'name': str(broker),
    #             'id': broker.id,
    #             'is_primary': broker.primary_banking_detail == self
    #         })
    #
    #     # Check transporters
    #     transporters = self.transporters.all()
    #     for transporter in transporters:
    #         linked_entities.append({
    #             'type': 'Transporter',
    #             'name': str(transporter),
    #             'id': transporter.id,
    #             'is_primary': transporter.primary_banking_detail == self
    #         })
    #
    #     # Check owners
    #     owners = self.owners.all()
    #     for owner in owners:
    #         linked_entities.append({
    #             'type': 'Owner',
    #             'name': str(owner),
    #             'id': owner.id,
    #             'is_primary': owner.primary_banking_detail == self
    #         })
    #
    #     # Check organizations
    #     organizations = self.organizations.all()
    #     for org in organizations:
    #         linked_entities.append({
    #             'type': 'Organization',
    #             'name': str(org),
    #             'id': org.id,
    #             'is_primary': org.primary_banking_detail == self
    #         })
    #
    #     return linked_entities

    # def get_linked_entities_display(self):
    #     """Get a formatted display of linked entities"""
    #     entities = self.get_linked_entities()
    #     if not entities:
    #         return "No entities linked"
    #
    #     display_list = []
    #     for entity in entities:
    #         primary_indicator = " (Primary)" if entity['is_primary'] else ""
    #         display_list.append(f"{entity['type']}: {entity['name']}{primary_indicator}")
    #
    #     return " | ".join(display_list)

    # def get_primary_entity(self):
    #     """Get the entity for which this is the primary banking detail"""
    #     entities = self.get_linked_entities()
    #     primary_entities = [e for e in entities if e['is_primary']]
    #
    #     if primary_entities:
    #         return primary_entities[0]
    #     return None

    # def get_primary_entity_display(self):
    #     """Get display string for primary entity"""
    #     primary = self.get_primary_entity()
    #     if primary:
    #         return f"{primary['type']}: {primary['name']}"
    #     return "Not set as primary for any entity"


class Choice(models.Model):
    category = models.CharField(
        max_length=100,
        choices=ChoiceCategory.choices,
        null=True,
        blank=True,
        help_text="Logical grouping for this choice (see configuration.constants.ChoiceCategory)",
    )
    internal_value = models.CharField(max_length=100)  # e.g., 'Mr', '6'
    display_value = models.CharField(max_length=100)  # e.g., 'Mr.', '6'

    class Meta:
        unique_together = ('category', 'internal_value')

    def __str__(self):
        return f"{self.display_value}"


class PostalInfo(models.Model):
    pincode = models.IntegerField(unique=True)
    officename = models.CharField(max_length=255, blank=True, null=True)
    officeType = models.CharField(max_length=50, blank=True, null=True)
    Deliverystatus = models.CharField(max_length=50, blank=True, null=True)
    divisionname = models.CharField(max_length=100, blank=True, null=True)
    regionname = models.CharField(max_length=100, blank=True, null=True)
    circlename = models.CharField(max_length=100, blank=True, null=True)
    Taluk = models.CharField(max_length=100, blank=True, null=True)
    Districtname = models.CharField(max_length=100, blank=True, null=True)
    statename = models.CharField(max_length=100, blank=True, null=True)
    Telephone = models.CharField(max_length=50, blank=True, null=True)
    relatedSuboffice = models.CharField(max_length=100, blank=True, null=True)
    relatedHeadoffice = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.pincode} - {self.statename}, {self.Districtname}"

    @staticmethod
    def get_postal_details(pincode):
        try:
            info = PostalInfo.objects.get(pincode=pincode)
            return {
                "statename": info.statename,
                "Districtname": info.Districtname,
                "Taluk": info.Taluk,
                "officename": info.officename,
            }
        except PostalInfo.DoesNotExist:
            return {}
