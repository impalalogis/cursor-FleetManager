import logging
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from configuration.constants import ChoiceCategory
from configuration.models import Choice
from financial.models import Transaction
from financial.signals import safe_calculate_invoice_totals
from operations.models import (
    Consignment,
    ConsignmentGroup,
    Diesel,
    DriverAdvance,
    Shipment,
    ShipmentExpense,
)

logger = logging.getLogger(__name__)

AUTO_LEDGER_PREFIX = "[AUTO_LEDGER]"
LEDGER_KIND_DIESEL_EXPENSE = "DIESEL_EXPENSE"
LEDGER_KIND_DIESEL_CASH = "DIESEL_CASH"
LEDGER_KIND_SHIPMENT_EXPENSE = "SHIPMENT_EXPENSE"


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


def _sync_ledger_entry(
    *,
    kind: str,
    source_id: int,
    driver,
    amount: Decimal,
    entry_date,
    description: str,
    shipment=None,
):
    marker_prefix = _marker(kind, source_id)
    affected_driver_ids = _delete_ledger_entries(marker_prefix)

    if not driver or amount == 0:
        return affected_driver_ids

    entry = DriverAdvance.objects.create(
        driver=driver,
        shipment=shipment,
        amount=amount,
        description=f"{marker_prefix} {description}".strip(),
    )

    # DriverAdvance.date uses auto_now_add; set source date explicitly after create.
    if entry_date:
        DriverAdvance.objects.filter(pk=entry.pk).update(date=entry_date)

    affected_driver_ids.add(driver.id)
    return affected_driver_ids


def _sync_diesel_transaction(instance: Diesel):
    amount = _as_decimal(instance.total_price)
    reference = f"DIESEL_{instance.pk}"

    if amount <= 0:
        Transaction.objects.filter(reference_number=reference).delete()
        return

    Transaction.objects.update_or_create(
        reference_number=reference,
        defaults={
            "transaction_type": "expense",
            "category": "fuel",
            "amount": amount,
            "transaction_date": instance.date,
            "driver": instance.driver,
            "vehicle": instance.vehicle,
            "description": f"Diesel expense for record #{instance.pk}",
        },
    )


def _sync_shipment_expense_driver_ledger(instance: ShipmentExpense):
    ct = instance.content_type
    is_driver_expense = bool(
        ct and ct.app_label == "entity" and ct.model == "driver" and instance.object_id
    )
    amount = _as_decimal(instance.amount)

    return _sync_ledger_entry(
        kind=LEDGER_KIND_SHIPMENT_EXPENSE,
        source_id=instance.pk,
        driver=instance.expense_by if is_driver_expense else None,
        amount=-amount if amount > 0 else Decimal("0"),
        entry_date=instance.expense_date,
        description=f"Shipment expense deduction (SE#{instance.pk})",
        shipment=instance.shipment,
    )


@receiver(post_save, sender=ShipmentExpense, dispatch_uid="ops_sync_shipment_expense")
def sync_shipment_expense(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    if instance.shipment_id:
        for invoice in instance.shipment.invoices.all():
            safe_calculate_invoice_totals(invoice)

    _recompute_driver_chain(_sync_shipment_expense_driver_ledger(instance))


@receiver(post_delete, sender=ShipmentExpense, dispatch_uid="ops_on_shipment_expense_deleted")
def on_shipment_expense_deleted(sender, instance, **kwargs):
    try:
        if instance.shipment_id:
            for invoice in instance.shipment.invoices.all():
                safe_calculate_invoice_totals(invoice)
    except Exception:
        logger.exception("Error updating invoice on shipment expense delete for id=%s", instance.pk)

    marker_prefix = _marker(LEDGER_KIND_SHIPMENT_EXPENSE, instance.pk)
    _recompute_driver_chain(_delete_ledger_entries(marker_prefix))


@receiver(post_save, sender=DriverAdvance, dispatch_uid="ops_sync_driver_advance")
def sync_driver_advance(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    update_fields = set(kwargs.get("update_fields") or [])
    settle_fields = {"total_expenses", "carried_forward", "is_settled"}
    if update_fields and update_fields.issubset(settle_fields):
        return

    _recompute_driver_chain({instance.driver_id})

    if instance.shipment_id:
        for invoice in instance.shipment.invoices.all():
            safe_calculate_invoice_totals(invoice)


@receiver(post_delete, sender=DriverAdvance, dispatch_uid="ops_driver_advance_post_delete")
def driver_advance_post_delete(sender, instance, **kwargs):
    _recompute_driver_chain({instance.driver_id})

    if instance.shipment_id:
        for invoice in instance.shipment.invoices.all():
            safe_calculate_invoice_totals(invoice)


@receiver(m2m_changed, sender=ConsignmentGroup.consignments.through, dispatch_uid="ops_group_membership_change")
def update_group_totals_on_membership_change(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        instance.calculate_totals()


@receiver(post_save, sender=Consignment, dispatch_uid="ops_consignment_change")
def update_group_totals_on_consignment_change(sender, instance, **kwargs):
    for group in instance.consignmentgroup_set.all():
        group.calculate_totals()


@receiver(post_save, sender=DriverAdvance, dispatch_uid="ops_owner_paid_advance_to_expense")
def create_expense_when_owner_pays_advance(sender, instance, created, **kwargs):
    if not created or not instance.shipment_id:
        return

    ct = instance.content_type
    if not (ct and ct.app_label == "entity" and ct.model == "organization"):
        return

    try:
        owner_org = ct.get_object_for_this_type(pk=instance.object_id)
        if getattr(owner_org, "organization_type_code", None) != "OWNER":
            return

        expense_type = None
        try:
            expense_type = Choice.objects.get(
                category=ChoiceCategory.FINANCE_EXPENSE_TYPE,
                internal_value="DriverAdvance",
            )
        except Choice.DoesNotExist:
            try:
                expense_type = Choice.objects.get(
                    category=ChoiceCategory.FINANCE_EXPENSE_TYPE,
                    internal_value="Advance",
                )
            except Choice.DoesNotExist:
                expense_type = None

        owner_ct = ContentType.objects.get(app_label="entity", model="organization")
        ShipmentExpense.objects.create(
            shipment_id=instance.shipment_id,
            content_type=owner_ct,
            object_id=instance.object_id,
            expense_type=expense_type,
            amount=instance.amount or Decimal("0"),
            expense_date=instance.date,
            description=f"Auto: Driver Advance payout (DA:{instance.pk}) - {instance.description or ''}".strip(),
        )
    except Exception:
        logger.exception(
            "Failed to auto-create ShipmentExpense for Owner-paid DriverAdvance #%s",
            instance.pk,
        )


@receiver(post_delete, sender=DriverAdvance, dispatch_uid="ops_remove_auto_expense_on_advance_delete")
def remove_auto_expense_when_advance_deleted(sender, instance, **kwargs):
    try:
        if not instance.shipment_id:
            return
        ShipmentExpense.objects.filter(
            shipment_id=instance.shipment_id,
            description__icontains=f"(DA:{instance.pk})",
        ).delete()
    except Exception:
        logger.exception(
            "Failed to delete auto-created ShipmentExpense for DriverAdvance #%s",
            instance.pk,
        )


@receiver(post_save, sender=Diesel, dispatch_uid="ops_sync_diesel_finance")
def sync_diesel_finance(sender, instance: Diesel, **kwargs):
    if kwargs.get("raw"):
        return

    _sync_diesel_transaction(instance)

    diesel_amount = _as_decimal(instance.total_price)
    cash_amount = _as_decimal(instance.driver_taken_cash)
    driver = instance.driver

    affected_driver_ids = set()
    affected_driver_ids |= _sync_ledger_entry(
        kind=LEDGER_KIND_DIESEL_EXPENSE,
        source_id=instance.pk,
        driver=driver,
        amount=-diesel_amount if diesel_amount > 0 else Decimal("0"),
        entry_date=instance.date,
        description=f"Diesel expense deduction (Diesel#{instance.pk})",
        shipment=None,
    )
    affected_driver_ids |= _sync_ledger_entry(
        kind=LEDGER_KIND_DIESEL_CASH,
        source_id=instance.pk,
        driver=driver,
        amount=cash_amount if cash_amount > 0 else Decimal("0"),
        entry_date=instance.date,
        description=f"Diesel cash taken credit (Diesel#{instance.pk})",
        shipment=None,
    )
    _recompute_driver_chain(affected_driver_ids)


@receiver(post_delete, sender=Diesel, dispatch_uid="ops_delete_diesel_finance")
def delete_finance_for_diesel(sender, instance, **kwargs):
    Transaction.objects.filter(reference_number=f"DIESEL_{instance.pk}").delete()

    affected_driver_ids = set()
    for kind in (LEDGER_KIND_DIESEL_EXPENSE, LEDGER_KIND_DIESEL_CASH):
        affected_driver_ids |= _delete_ledger_entries(_marker(kind, instance.pk))
    _recompute_driver_chain(affected_driver_ids)

