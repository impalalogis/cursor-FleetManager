"""
Django signals to automatically capture financial data from all relevant models
and create Transaction records for comprehensive financial tracking.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal
import logging
import time

# Import the Transaction model
from .models import Transaction, Payment, OfficeExpense, Invoice

logger = logging.getLogger(__name__)


def debounced_invoice_calculation(invoice_id, delay=1):
    """
    Debounce invoice calculations to prevent excessive recalculations
    """
    cache_key = f"invoice_calc_debounce_{invoice_id}"
    current_time = time.time()
    last_calc = cache.get(cache_key)
    
    if last_calc and (current_time - last_calc) < delay:
        logger.debug(f"Debouncing invoice calculation for invoice {invoice_id}")
        return False
    
    cache.set(cache_key, current_time, 60)  # Cache for 1 minute
    return True


def safe_calculate_invoice_totals(invoice):
    """
    Safely calculate invoice totals with error handling
    """
    try:
        if debounced_invoice_calculation(invoice.id):
            invoice.calculate_totals()
            logger.debug(f"Successfully calculated totals for invoice {invoice.id}")
    except Exception as e:
        logger.error(f"Failed to calculate totals for invoice {invoice.id}: {str(e)}", exc_info=True)


def create_transaction_from_model(sender, instance, transaction_type, category, **kwargs):
    """
    Helper function to create Transaction records from various source models
    """
    try:
        # Determine the amount based on the source model
        amount = (
            getattr(instance, 'amount', None)
            or getattr(instance, 'total_cost', None)
            or getattr(instance, 'cost', None)
            or getattr(instance, 'amount_paid', None)
            or 0
        )
        
        if amount <= 0:
            return  # Skip if no valid amount
        
        # Determine the transaction date
        transaction_date = (
            getattr(instance, 'expense_date', None) or
            getattr(instance, 'service_date', None) or
            getattr(instance, 'date', None) or
            getattr(instance, 'transaction_date', None) or
            getattr(instance, 'payment_date', None) or
            getattr(instance, 'Purchase_Date', None) or
            timezone.now().date()
        )
        
        # Determine the description
        description = (
            getattr(instance, 'description', None) or
            getattr(instance, 'notes', None) or
            str(instance)
        )
        
        # Determine related entities
        driver = getattr(instance, 'driver', None)
        vehicle = getattr(instance, 'vehicle', None)
        shipment = getattr(instance, 'shipment', None)
        
        # Get reference number if available
        reference_number = (
            getattr(instance, 'invoice_number', None) or
            getattr(instance, 'receipt_number', None) or
            getattr(instance, 'reference_number', None) or
            f"{sender.__name__}_{instance.pk}"
        )
        # Determine who created it
        created_by = (
            getattr(instance, 'created_by', None) or
            getattr(instance, 'performed_by', None) or
            getattr(instance, 'Purchase_by', None) or
            'system'
        )
        
        # Prepare the transaction data
        transaction_data = {
            'transaction_type': transaction_type,
            'category': category,
            'description': description,
            'amount': Decimal(str(amount)),
            'transaction_date': transaction_date,
            'reference_number': reference_number,
            'created_by': created_by,
            'driver': driver,
            'vehicle': vehicle,
            'shipment': shipment,
        }
        
        # Add source model reference
        source_field_map = {
            'ShipmentExpense': 'related_shipment_expense',
            'DriverAdvance': 'related_driver_advance',
            'MaintenanceRecord': 'related_maintenance_record',
            'Tyre': 'related_tyre',
            'TyreTransaction': 'related_tyre_transaction',
            'OfficeExpense': 'related_other_expense',
            'Payment': 'related_payment',
        }
        
        source_field = source_field_map.get(sender.__name__)
        if source_field:
            transaction_data[source_field] = instance
        
        # Check if transaction already exists for this source
        if not source_field:
            logger.warning(
                "No source field mapping for sender=%s instance=%s",
                sender.__name__,
                instance.pk,
            )
            return

        existing_transaction = Transaction.objects.filter(**{source_field: instance}).first()
        
        if existing_transaction:
            # Update existing transaction
            for key, value in transaction_data.items():
                setattr(existing_transaction, key, value)
            existing_transaction.save()
        else:
            # Create new transaction
            tx = Transaction.objects.create(**transaction_data)
            # Guarantee transaction_id is present even on updates
            if not tx.transaction_id:
                tx.save()
    except Exception as e:
        # Log the error but don't break the original save
        logger.error(
            "Error creating transaction from %s (id=%s): %s",
            sender.__name__,
            getattr(instance, "pk", None),
            e,
            exc_info=True,
        )


@receiver(post_save, sender='operations.ShipmentExpense')
def create_transaction_from_shipment_expense(sender, instance, created, **kwargs):
    """Create transaction from ShipmentExpense"""
    if not hasattr(instance, 'amount') or not instance.amount:
        logger.debug("Skipping ShipmentExpense %s: amount missing/zero", instance.pk)
        return
        
    create_transaction_from_model(
        sender=sender,
        instance=instance,
        transaction_type='expense',
        category='shipment',
        **kwargs
    )


@receiver(post_save, sender='operations.DriverAdvance')
def create_transaction_from_driver_advance(sender, instance, created, **kwargs):
    """Create transaction from DriverAdvance"""
    if not hasattr(instance, 'amount') or not instance.amount:
        return
        
    create_transaction_from_model(
        sender=sender,
        instance=instance,
        transaction_type='advance',
        category='driver',
        **kwargs
    )


@receiver(post_save, sender='maintenance.MaintenanceRecord')
def create_transaction_from_maintenance(sender, instance, created, **kwargs):
    """Create transaction from MaintenanceRecord"""
    # Ownership for MaintenanceRecord -> Transaction is handled in maintenance.signals.
    # Keep this receiver as a no-op to avoid duplicate update/write paths.
    return


@receiver(post_save, sender='maintenance.Tyre')
def create_transaction_from_tyre_purchase(sender, instance, created, **kwargs):
    """Create transaction from Tyre purchase"""
    # Ownership for Tyre purchase -> Transaction is handled in maintenance.signals.
    # Keep this receiver as a no-op to avoid duplicate update/write paths.
    return


@receiver(post_save, sender='maintenance.TyreTransaction')
def create_transaction_from_tyre_transaction(sender, instance, created, **kwargs):
    """Create transaction from TyreTransaction (tyre service/repair costs)"""
    if not hasattr(instance, 'cost') or not instance.cost:
        return
        
    create_transaction_from_model(
        sender=sender,
        instance=instance,
        transaction_type='expense',
        category='tyre',
        **kwargs
    )


@receiver(post_save, sender=OfficeExpense)
def create_transaction_from_other_expense(sender, instance, created, **kwargs):
    """Create transaction from OfficeExpense"""
    if not hasattr(instance, 'amount') or not instance.amount:
        return
        
    # Determine category based on OfficeExpense category
    category_mapping = {
        'FUEL': 'fuel',
        'OFFICE_RENT': 'office',
        'OFFICE_UTILITIES': 'office',
        'INSURANCE': 'insurance',
        'PERMIT': 'permit',
        'TOLL': 'toll',
        'OfficeExpenses': 'office',
        'rent': 'office'
    }

    expense_category = 'office'  # default
    if hasattr(instance, 'category') and instance.category:
        category_value = (
            getattr(instance.category, 'internal_value', None)
            or getattr(instance.category, 'value', None)
            or str(instance.category)
        )
        expense_category = category_mapping.get(category_value, 'office')

    create_transaction_from_model(
        sender=sender,
        instance=instance,
        transaction_type='expense',
        category=expense_category,
        **kwargs
    )



@receiver(post_save, sender=Payment)
def create_transaction_from_payment(sender, instance, created, **kwargs):
    """Create transaction from Payment (revenue) and update invoice totals"""
    if not hasattr(instance, 'amount_paid') or not instance.amount_paid:
        return
        
    # For payments, we create a revenue transaction
    try:
        # Get related shipment from invoice if available
        shipment = None
        if hasattr(instance, 'invoice') and instance.invoice and hasattr(instance.invoice, 'shipment'):
            shipment = instance.invoice.shipment
        
        transaction_data = {
            'transaction_type': 'revenue',
            'category': 'other',  # Revenue doesn't fit into expense categories
            'description': f"Payment received for Invoice {instance.invoice}" if hasattr(instance, 'invoice') else "Payment received",
            'amount': instance.amount_paid,
            'transaction_date': getattr(instance, 'payment_date', timezone.now().date()),
            'reference_number': getattr(instance, 'reference_number', f"PAY_{instance.pk}"),
            'created_by': getattr(instance, 'created_by', 'system'),
            'shipment': shipment,
            'related_payment': instance,
        }
        
        # Check if transaction already exists
        existing_transaction = Transaction.objects.filter(related_payment=instance).first()
        
        if existing_transaction:
            # Update existing transaction
            for key, value in transaction_data.items():
                setattr(existing_transaction, key, value)
            existing_transaction.save()
        else:
            # Create new transaction
            Transaction.objects.create(**transaction_data)
        
        # CRUCIAL: Update invoice totals when payment is saved
        if hasattr(instance, 'invoice') and instance.invoice:
            safe_calculate_invoice_totals(instance.invoice)
            
    except Exception as e:
        logger.error(
            "Error creating transaction from Payment (id=%s): %s",
            getattr(instance, "pk", None),
            e,
            exc_info=True,
        )


@receiver(post_delete, sender=Payment)
def update_invoice_on_payment_delete(sender, instance, **kwargs):
    """Update invoice totals when Payment is deleted"""
    try:
        if hasattr(instance, 'invoice') and instance.invoice:
            safe_calculate_invoice_totals(instance.invoice)
    except Exception as e:
        logger.error(f"Error updating invoice on payment delete: {str(e)}", exc_info=True)



@receiver(post_delete, sender='operations.ShipmentExpense')
@receiver(post_delete, sender='operations.DriverAdvance')
@receiver(post_delete, sender='maintenance.TyreTransaction')
@receiver(post_delete, sender=OfficeExpense)
def delete_related_transaction(sender, instance, **kwargs):
    """Delete related transaction when source model is deleted"""
    try:
        source_field_map = {
            'ShipmentExpense': 'related_shipment_expense',
            'DriverAdvance': 'related_driver_advance',
            'MaintenanceRecord': 'related_maintenance_record',
            'Tyre': 'related_tyre',
            'TyreTransaction': 'related_tyre_transaction',
            'OfficeExpense': 'related_other_expense',
            'Payment': 'related_payment',
        }
        
        source_field = source_field_map.get(sender.__name__)
        if source_field:
            Transaction.objects.filter(**{source_field: instance}).delete()
            
    except Exception as e:
        logger.error(
            "Error deleting related transaction for %s (id=%s): %s",
            sender.__name__,
            getattr(instance, "pk", None),
            e,
            exc_info=True,
        )


# Helper function to manually sync existing data
def sync_existing_data(verbose=True):
    """
    One-time function to sync existing data from all models to Transaction table.
    Run this after implementing the signals to capture existing data.
    
    Usage:
    from financial.signals import sync_existing_data
    sync_existing_data()
    
    Or via Django shell:
    python manage.py shell -c "from financial.signals import sync_existing_data; sync_existing_data()"
    """
    from django.apps import apps
    
    if verbose:
        print("Starting sync of existing data to Transaction table...")
    
    # Sync ShipmentExpense
    try:
        ShipmentExpense = apps.get_model('operations', 'ShipmentExpense')
        for expense in ShipmentExpense.objects.all():
            create_transaction_from_shipment_expense(ShipmentExpense, expense, created=True)
        if verbose:
            print(f"Synced {ShipmentExpense.objects.count()} ShipmentExpense records")
    except Exception as e:
        if verbose:
            print(f"Error syncing ShipmentExpense: {e}")
    
    # Sync DriverAdvance
    try:
        DriverAdvance = apps.get_model('operations', 'DriverAdvance')
        for advance in DriverAdvance.objects.all():
            create_transaction_from_driver_advance(DriverAdvance, advance, created=True)
        if verbose:
            print(f"Synced {DriverAdvance.objects.count()} DriverAdvance records")
    except Exception as e:
        if verbose:
            print(f"Error syncing DriverAdvance: {e}")
    
    # Sync MaintenanceRecord
    try:
        MaintenanceRecord = apps.get_model('maintenance', 'MaintenanceRecord')
        for maintenance in MaintenanceRecord.objects.all():
            create_transaction_from_maintenance(MaintenanceRecord, maintenance, created=True)
        if verbose:
            print(f"Synced {MaintenanceRecord.objects.count()} MaintenanceRecord records")
    except Exception as e:
        if verbose:
            print(f"Error syncing MaintenanceRecord: {e}")
    
    # Sync Tyre
    try:
        Tyre = apps.get_model('maintenance', 'Tyre')
        for tyre in Tyre.objects.all():
            create_transaction_from_tyre_purchase(Tyre, tyre, created=True)
        if verbose:
            print(f"Synced {Tyre.objects.count()} Tyre records")
    except Exception as e:
        if verbose:
            print(f"Error syncing Tyre: {e}")
    
    # Sync TyreTransaction
    try:
        TyreTransaction = apps.get_model('maintenance', 'TyreTransaction')
        for tyre_transaction in TyreTransaction.objects.all():
            create_transaction_from_tyre_transaction(TyreTransaction, tyre_transaction, created=True)
        if verbose:
            print(f"Synced {TyreTransaction.objects.count()} TyreTransaction records")
    except Exception as e:
        if verbose:
            print(f"Error syncing TyreTransaction: {e}")
    
    # Sync OfficeExpense
    try:
        for expense in OfficeExpense.objects.all():
            create_transaction_from_other_expense(OfficeExpense, expense, created=True)
        if verbose:
            print(f"Synced {OfficeExpense.objects.count()} OfficeExpense records")
    except Exception as e:
        if verbose:
            print(f"Error syncing OfficeExpense: {e}")
    
    # Sync Payment
    try:
        for payment in Payment.objects.all():
            create_transaction_from_payment(Payment, payment, created=True)
        if verbose:
            print(f"Synced {Payment.objects.count()} Payment records")
    except Exception as e:
        if verbose:
            print(f"Error syncing Payment: {e}")
    
    if verbose:
        print("Sync completed!")
    
    return True



