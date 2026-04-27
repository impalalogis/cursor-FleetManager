# maintenance/signals.py
import logging
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver

from financial.models import Transaction
from maintenance.models import MaintenanceRecord, Tyre
from django.contrib.contenttypes.models import ContentType

# NEW import:
from operations.models import DriverAdvance  # <-- use your existing model

logger = logging.getLogger(__name__)


def _choice_label(ch):
    if not ch:
        return ""
    return getattr(ch, "name", None) or getattr(ch, "value", None) or getattr(ch, "key", None) or str(ch)


@receiver(post_save, sender=MaintenanceRecord)
def sync_maintenance_expense(sender, instance, created, **kwargs):
    print(">>> SIGNAL FIRED for MaintenanceRecord:", instance.pk)

    amt = instance.total_cost or Decimal("0.00")

    # Determine if performer is a driver
    is_driver = (
        instance.content_type
        and instance.content_type.app_label == "entity"
        and instance.content_type.model == "driver"
    )

    print(">>> is_driver:", is_driver)

    # Create or update Transaction only
    Transaction.objects.update_or_create(
        related_maintenance_record=instance,
        defaults={
            "transaction_type": "expense",
            "category": "maintenance",
            "amount": amt,
            "transaction_date": instance.service_date,
            "driver": instance.performed_by if is_driver else None,
            "vehicle": instance.vehicle,
            "description": f"Maintenance - {_choice_label(instance.service_type)}",
        }
    )

    print(">>> Transaction created/updated")




@receiver(post_save, sender=Tyre)
def sync_tyre_expense(sender, instance: Tyre, created, **kwargs):
    if created:
        amt = instance.amount if instance.amount is not None else Decimal("0.00")
        Transaction.objects.create(
            transaction_type="Expense",
            amount=amt,
            transaction_date=getattr(instance, "purchase_date", None),
            description=f"Tyre - {getattr(instance, 'tyreNo', '')}",
        )



from django.db.models.signals import post_delete
from django.dispatch import receiver
from operations.models import DriverAdvance
from maintenance.models import MaintenanceRecord


@receiver(post_delete, sender=MaintenanceRecord)
def delete_driveradvance_for_maintenance(sender, instance, **kwargs):
    """
    Delete any DriverAdvance rows created earlier for this maintenance record.
    (Old data cleanup + safety)
    """
    DriverAdvance.objects.filter(
        description__icontains=f"MR:{instance.pk}"
    ).delete()

from django.db.models.signals import post_delete
from django.dispatch import receiver
from maintenance.models import MaintenanceRecord
from operations.models import DriverAdvance
from financial.models import Transaction


# ---------------------------------------------------------
# MAINTENANCE DELETE → remove Transaction + old DriverAdvance
# ---------------------------------------------------------

@receiver(post_delete, sender=MaintenanceRecord, dispatch_uid="maint_delete_finance")
def delete_finance_for_maintenance(sender, instance, **kwargs):
    """
    Delete all financial entries created from this maintenance record.
    """

    # 1) Delete Transaction created by maintenance signal
    Transaction.objects.filter(
        related_maintenance_record=instance
    ).delete()

    # 2) Delete old DriverAdvance rows (cleanup from old logic)
    DriverAdvance.objects.filter(
        description__icontains=f"MR:{instance.pk}"
    ).delete()


