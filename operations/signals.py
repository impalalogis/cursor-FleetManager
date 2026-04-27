# operations/signals.py
import logging
from decimal import Decimal

from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from financial.signals import safe_calculate_invoice_totals

from operations.models import (
    ShipmentExpense,
    DriverAdvance,
    Shipment,
    ConsignmentGroup,
    Consignment,
)
from configuration.models import Choice  # used for auto-expense type in owner-paid advances
from configuration.constants import ChoiceCategory

logger = logging.getLogger(__name__)


def _recompute_driver_shipment_advances(driver_id, shipment_id):
    """
    Recompute the carry-forward chain for all DriverAdvance rows for a given
    (driver, shipment), in chronological order.
    """
    qs = DriverAdvance.objects.filter(
        driver_id=driver_id,
        shipment_id=shipment_id
    ).order_by('date', 'id')

    for adv in qs:
        # This calls .save(update_fields=[...]) internally
        adv.settle_and_carry_forward()


# --------------------------------------------------------------------
# SHIPMENT EXPENSES → update invoices; if expense is by a DRIVER, recompute advances
# --------------------------------------------------------------------
@receiver(post_save, sender=ShipmentExpense, dispatch_uid="ops_sync_shipment_expense")
def sync_shipment_expense(sender, instance, created, **kwargs):
    """
    Update invoice totals whenever a ShipmentExpense is saved.
    If the expense is by a DRIVER, recompute that driver's advances for the same shipment.
    """
    # Update invoices
    if instance.shipment_id:
        for invoice in instance.shipment.invoices.all():
            safe_calculate_invoice_totals(invoice)

    # If this expense is attributed to a Driver, recompute advances (no duplicate handler elsewhere)
    ct = instance.content_type
    if ct and instance.shipment_id and instance.object_id:
        if ct.app_label == "entity" and ct.model == "driver":
            _recompute_driver_shipment_advances(instance.object_id, instance.shipment_id)


@receiver(post_delete, sender=ShipmentExpense, dispatch_uid="ops_on_shipment_expense_deleted")
def on_shipment_expense_deleted(sender, instance, **kwargs):
    """
    On delete: refresh invoice; if it was a DRIVER expense, recompute advances.
    """
    try:
        if instance.shipment_id:
            for invoice in instance.shipment.invoices.all():
                safe_calculate_invoice_totals(invoice)
    except Exception as e:
        logger.error(f"Error updating invoice on expense delete: {str(e)}", exc_info=True)

    ct = instance.content_type
    if ct and instance.shipment_id and instance.object_id:
        if ct.app_label == "entity" and ct.model == "driver":
            _recompute_driver_shipment_advances(instance.object_id, instance.shipment_id)


# --------------------------------------------------------------------
# DRIVER ADVANCE → recompute chain; update invoices; avoid recursion
# --------------------------------------------------------------------
@receiver(post_save, sender=DriverAdvance, dispatch_uid="ops_sync_driver_advance")
def sync_driver_advance(sender, instance, created, **kwargs):
    """
    On any DriverAdvance save:
      1) Ignore internal saves that only update settle/carry fields (break recursion).
      2) Recompute the carry-forward chain for this driver+shipment once.
      3) Refresh linked invoice totals.
    NOTE: Do NOT create a Transaction here — financial.signals already does this.
    """
    if kwargs.get("raw"):
        return

    # BREAK THE LOOP: ignore internal update of settle fields
    uf = set(kwargs.get("update_fields") or [])
    settle_fields = {"total_expenses", "carried_forward", "is_settled"}
    if uf and uf.issubset(settle_fields):
        return

    # Recompute chain (once per external change)
    if instance.shipment_id:
        _recompute_driver_shipment_advances(instance.driver_id, instance.shipment_id)

        # Update all invoices for this shipment
        for invoice in instance.shipment.invoices.all():
            safe_calculate_invoice_totals(invoice)


# --------------------------------------------------------------------
# CONSIGNMENT GROUP TOTALS
# --------------------------------------------------------------------
@receiver(m2m_changed, sender=ConsignmentGroup.consignments.through, dispatch_uid="ops_group_membership_change")
def update_group_totals_on_membership_change(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        instance.calculate_totals()


@receiver(post_save, sender=Consignment, dispatch_uid="ops_consignment_change")
def update_group_totals_on_consignment_change(sender, instance, **kwargs):
    for group in instance.consignmentgroup_set.all():
        group.calculate_totals()


# --------------------------------------------------------------------
# SHIPMENT DELETE → mark related advances settled after recompute
# --------------------------------------------------------------------
@receiver(post_delete, sender=Shipment, dispatch_uid="ops_shipment_post_delete")
def shipment_post_delete(sender, instance, **kwargs):
    for adv in DriverAdvance.objects.filter(shipment_id=instance.pk):
        adv.settle_and_carry_forward()
        DriverAdvance.objects.filter(pk=adv.pk).update(is_settled=True)


# --------------------------------------------------------------------
# AUTO-EXPENSE when Owner funds a DriverAdvance (one-time on create)
# --------------------------------------------------------------------
@receiver(post_save, sender=DriverAdvance, dispatch_uid="ops_owner_paid_advance_to_expense")
def create_expense_when_owner_pays_advance(sender, instance, created, **kwargs):
    """
    If a DriverAdvance is paid by an Owner and a shipment is set, create a matching
    ShipmentExpense (once, on create). This expense is attributed to that Owner for that shipment.
    """
    if not created or not instance.shipment_id:
        return

    ct = instance.content_type
    if not (ct and ct.app_label == "entity" and ct.model == "organization"):
        return

    try:
        owner_org = ct.get_object_for_this_type(pk=instance.object_id)
        if getattr(owner_org, 'organization_type_code', None) != 'OWNER':
            return
        # choose an expense type
        expense_type = None
        try:
            expense_type = Choice.objects.get(
                category=ChoiceCategory.FINANCE_EXPENSE_TYPE,
                internal_value="DriverAdvance"
            )
        except Choice.DoesNotExist:
            try:
                expense_type = Choice.objects.get(
                    category=ChoiceCategory.FINANCE_EXPENSE_TYPE,
                    internal_value="Advance"
                )
            except Choice.DoesNotExist:
                expense_type = None

        owner_ct = ContentType.objects.get(app_label="entity", model="organization")

        # Tag with (DA:<id>) so we can clean up on delete
        ShipmentExpense.objects.create(
            shipment_id=instance.shipment_id,
            content_type=owner_ct,
            object_id=instance.object_id,  # Owner organization id
            expense_type=expense_type,
            amount=instance.amount or Decimal("0"),
            expense_date=instance.date,
            description=f"Auto: Driver Advance payout (DA:{instance.pk}) – {instance.description or ''}".strip(),
        )
    except Exception as e:
        logger.error(
            f"Failed to auto-create ShipmentExpense for Owner-paid DriverAdvance #{instance.pk}: {e}",
            exc_info=True
        )


@receiver(post_delete, sender=DriverAdvance, dispatch_uid="ops_remove_auto_expense_on_advance_delete")
def remove_auto_expense_when_advance_deleted(sender, instance, **kwargs):
    """
    If we auto-created a ShipmentExpense for this advance, remove it when the advance is deleted.
    """
    try:
        if not instance.shipment_id:
            return
        ShipmentExpense.objects.filter(
            shipment_id=instance.shipment_id,
            description__icontains=f"(DA:{instance.pk})"
        ).delete()
    except Exception as e:
        logger.error(
            f"Failed to delete auto-created ShipmentExpense for DriverAdvance #{instance.pk}: {e}",
            exc_info=True
        )


from django.db.models.signals import post_save
from django.dispatch import receiver
from operations.models import ShipmentExpense, DriverAdvance
from django.contrib.contenttypes.models import ContentType


@receiver(post_save, sender=ShipmentExpense)
def auto_create_driver_advance_for_expense(sender, instance, created, **kwargs):
    """
    When a ShipmentExpense is added:
    1. Ensure ONE DriverAdvance exists for that shipment.
    2. Recompute the entire DriverAdvance chain for that driver.
    """

    if not created:
        return

    shipment = instance.shipment
    if not shipment:
        return

    driver = shipment.driver
    if not driver:
        return

    # Check if a DriverAdvance already exists for this driver+shipment
    adv = DriverAdvance.objects.filter(
        driver=driver,
        shipment=shipment
    ).first()

    if not adv:
        adv = DriverAdvance.objects.create(
            driver=driver,
            shipment=shipment,
            amount=0,
            description="Auto-created for shipment expenses",
            content_type=ContentType.objects.get_for_model(shipment),
            object_id=shipment.id,
        )

    # ---------------------------------------
    # 🔥 Recompute the entire chain for driver
    # ---------------------------------------
    DriverAdvance.recompute_chain_for_driver(driver.id)



# operations/signals.py
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver

from operations.models import Diesel   # adjust app if different
from operations.models import DriverAdvance
from financial.models import Transaction

@receiver(post_save, sender=Diesel)
def sync_diesel_finance(sender, instance: Diesel, created, **kwargs):

    # ----------------------------------------------------
    # PREVENT DOUBLE EXECUTION
    # ----------------------------------------------------
    if kwargs.get("raw"):
        return

    if getattr(instance, "_diesel_signal_ran", False):
        return
    setattr(instance, "_diesel_signal_ran", True)

    driver = instance.driver

    # ----------------------------------------------------
    # 1) DRIVER CASH TAKEN → DriverAdvance (credit)
    # ----------------------------------------------------
    DriverAdvance.objects.filter(
        description__icontains=f"Diesel#{instance.pk}"
    ).delete()

    if driver and instance.driver_taken_cash and instance.driver_taken_cash > 0:
        DriverAdvance.objects.create(
            driver=driver,
            date=instance.date,
            amount=Decimal(instance.driver_taken_cash),
            shipment=None,
            description=f"Diesel cash taken • Diesel#{instance.pk}",
        )

    # ----------------------------------------------------
    # 2) DIESEL EXPENSE → Transaction
    # ----------------------------------------------------
    amount = instance.total_price or Decimal("0")
    if amount <= 0:
        return

    if instance.payment_mode == "CASH" and driver:
        Transaction.objects.update_or_create(
            reference_number=f"DIESEL_{instance.pk}",
            defaults={
                "transaction_type": "expense",
                "category": "diesel",
                "amount": amount,
                "transaction_date": instance.date,
                "driver": driver,
                "vehicle": instance.vehicle,
                "description": f"Diesel (cash) • {instance.vehicle} • {instance.quantity} L",
            },
        )
    else:
        Transaction.objects.update_or_create(
            reference_number=f"DIESEL_{instance.pk}",
            defaults={
                "transaction_type": "expense",
                "category": "diesel",
                "amount": amount,
                "transaction_date": instance.date,
                "driver": None,
                "vehicle": instance.vehicle,
                "description": f"Diesel (online) • {instance.vehicle} • {instance.quantity} L",
            },
        )



from django.db.models.signals import post_delete
from django.dispatch import receiver
from operations.models import Diesel, DriverAdvance
from financial.models import Transaction

# ---------------------------------------------------------
# DIESEL DELETE → remove Transaction + DriverAdvance
# ---------------------------------------------------------
# ---------------------------------------------------------
# DIESEL DELETE → remove Transaction + DriverAdvance
# ---------------------------------------------------------
@receiver(post_delete, sender=Diesel, dispatch_uid="ops_delete_diesel_finance")
def delete_finance_for_diesel(sender, instance, **kwargs):
    """
    Delete all financial entries created from this diesel entry.
    """

    # 1) Delete Transaction created by diesel signal
    Transaction.objects.filter(
        reference_number=f"DIESEL_{instance.pk}"
    ).delete()

    # 2) Delete DriverAdvance created for diesel cash
    DriverAdvance.objects.filter(
        description__icontains=f"Diesel#{instance.pk}"
    ).delete()

