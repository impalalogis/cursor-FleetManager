# maintenance/signals.py
import logging
from decimal import Decimal

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from financial.models import Transaction
from maintenance.models import MaintenanceRecord, Tyre
from operations.models import DriverAdvance

logger = logging.getLogger(__name__)

AUTO_LEDGER_PREFIX = "[AUTO_LEDGER]"
LEDGER_KIND_MAINTENANCE_EXPENSE = "MAINTENANCE_EXPENSE"


def _choice_label(ch):
    if not ch:
        return ""
    return getattr(ch, "name", None) or getattr(ch, "value", None) or getattr(ch, "key", None) or str(ch)


def _as_decimal(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _marker(kind: str, source_id: int) -> str:
    return f"{AUTO_LEDGER_PREFIX}[{kind}:{source_id}]"


def _recompute_driver_chain(driver_ids):
    for driver_id in {driver_id for driver_id in driver_ids if driver_id}:
        try:
            DriverAdvance.recompute_chain_for_driver(driver_id)
        except Exception:
            logger.exception("Failed to recompute DriverAdvance chain for driver=%s", driver_id)


def _delete_ledger_entries(marker_prefix: str):
    entries = list(
        DriverAdvance.objects.filter(description__startswith=marker_prefix).values("id", "driver_id")
    )
    if entries:
        DriverAdvance.objects.filter(id__in=[entry["id"] for entry in entries]).delete()
    return {entry["driver_id"] for entry in entries if entry["driver_id"]}


def _sync_maintenance_ledger(instance: MaintenanceRecord):
    marker_prefix = _marker(LEDGER_KIND_MAINTENANCE_EXPENSE, instance.pk)
    affected_driver_ids = _delete_ledger_entries(marker_prefix)

    amount = _as_decimal(instance.total_cost)
    ct = instance.content_type
    is_driver_performed = bool(
        ct and ct.app_label == "entity" and ct.model == "driver" and instance.object_id
    )
    driver = instance.performed_by if is_driver_performed else None
    if not driver or amount <= 0:
        return affected_driver_ids

    entry = DriverAdvance.objects.create(
        driver=driver,
        shipment=None,
        amount=-amount,
        description=f"{marker_prefix} Maintenance expense deduction (MR:{instance.pk})",
    )

    # DriverAdvance.date uses auto_now_add; align with maintenance date.
    DriverAdvance.objects.filter(pk=entry.pk).update(date=instance.service_date)
    affected_driver_ids.add(driver.id)
    return affected_driver_ids


@receiver(post_save, sender=MaintenanceRecord, dispatch_uid="maint_sync_finance")
def sync_maintenance_expense(sender, instance, **kwargs):
    amount = _as_decimal(instance.total_cost)
    ct = instance.content_type
    is_driver_performed = bool(
        ct and ct.app_label == "entity" and ct.model == "driver" and instance.object_id
    )

    if amount <= 0:
        Transaction.objects.filter(related_maintenance_record=instance).delete()
    else:
        Transaction.objects.update_or_create(
            related_maintenance_record=instance,
            defaults={
                "transaction_type": "expense",
                "category": "maintenance",
                "amount": amount,
                "transaction_date": instance.service_date,
                "driver": instance.performed_by if is_driver_performed else None,
                "vehicle": instance.vehicle,
                "description": f"Maintenance - {_choice_label(instance.service_type)}",
            },
        )

    _recompute_driver_chain(_sync_maintenance_ledger(instance))


@receiver(post_save, sender=Tyre, dispatch_uid="maint_sync_tyre_expense")
def sync_tyre_expense(sender, instance: Tyre, created, **kwargs):
    if not created:
        return

    amount = _as_decimal(instance.amount)
    if amount <= 0:
        return

    Transaction.objects.update_or_create(
        related_tyre=instance,
        defaults={
            "transaction_type": "expense",
            "category": "tyre",
            "amount": amount,
            "transaction_date": getattr(instance, "purchase_date", None),
            "description": f"Tyre - {getattr(instance, 'tyreNo', '')}",
        },
    )


@receiver(post_delete, sender=MaintenanceRecord, dispatch_uid="maint_delete_finance")
def delete_finance_for_maintenance(sender, instance, **kwargs):
    Transaction.objects.filter(related_maintenance_record=instance).delete()
    marker_prefix = _marker(LEDGER_KIND_MAINTENANCE_EXPENSE, instance.pk)
    _recompute_driver_chain(_delete_ledger_entries(marker_prefix))


