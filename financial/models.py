from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from utils.validators import user_document_upload_path, document_file_validator
from configuration.constants import ChoiceCategory


# Approval workflow and tenant logic removed for simplicity


class Invoice(models.Model):
    """
    Enhanced Invoice model with consignment support and comprehensive financial tracking.
    Each invoice belongs to a single tenant through its shipment and can be linked to consignments.
    """
    INVOICE_STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]

    BILL_TO_CHOICES = [
        ('CONSIGNOR', 'Consignor'),
        ('CONSIGNEE', 'Consignee'),
        ('TRANSPORTER', 'Transporter'),
        ('BROKER', 'Broker'),
    ]

    bill_to = models.CharField(
        max_length=20,
        choices=BILL_TO_CHOICES,
        default='CONSIGNOR',
        help_text="Select who this invoice is billed to"
    )

    invoice_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    invoice_ref = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # Enhanced relationships to support consignments
    shipment = models.ForeignKey('operations.Shipment', on_delete=models.SET_NULL, related_name='invoices', null=True,
                                 blank=True)
    consignmentGroup = models.ForeignKey('operations.ConsignmentGroup', on_delete=models.SET_NULL,
                                         related_name='invoices', null=True, blank=True)

    detention_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Detention charges applicable for this invoice"
    )

    # Enhanced date fields
    issue_date = models.DateField(auto_now=True)
    due_date = models.DateField(null=True, blank=True)

    # Enhanced financial fields with proper calculations
    total_freight = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        help_text="Consignment total freight amount")
    total_expense = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        help_text="Total driver/owner expenses")
    total_advance = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        help_text="Total advances (shipment + driver advances)")
    balance_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                         help_text="Balance after total freight and expenses")
    payment_received = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                           help_text="Total payments received")
    total_dues = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                     help_text="Remaining dues after all deductions")
    # final_bill_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Final bill amount after expenses")

    # Enhanced status and additional fields
    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='DRAFT')
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True, help_text="Invoice notes and remarks")

    # Audit fields
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.invoice_id}"

    class Meta:
        db_table = 'invoice'
        indexes = [
            models.Index(fields=['shipment']),  # For tenant filtering
            models.Index(fields=['issue_date']),
            models.Index(fields=['is_paid']),
            # Composite indexes for common query patterns
            models.Index(fields=['shipment', 'status']),  # For invoice filtering by shipment and status
            models.Index(fields=['status', 'issue_date']),  # For status-based date filtering
            models.Index(fields=['consignmentGroup', 'status']),  # For consignment-based filtering
        ]

    def calculate_totals(self):
        """
        Enhanced calculation implementing the exact formulas specified:

        For Consignments:
        Total Dues = consignment.totalFreight
                   - (shipment.advanceReceived + driverAdvances.amount)
                   - payments

        For Shipments:
        Final Bill = consignment.totalFreight - driverOrOwnerExpenses
        """
        from django.apps import apps
        from django.db.models import Sum
        import logging

        logger = logging.getLogger(__name__)

        try:
            DriverAdvance = apps.get_model('operations', 'DriverAdvance')
            ShipmentExpense = apps.get_model('operations', 'ShipmentExpense')

            # Get total freight from multiple sources with priority order
            self.total_freight = 0

            # Priority 1: ConsignmentGroup total_amount
            if self.consignmentGroup and self.consignmentGroup.total_amount:
                self.total_freight = self.consignmentGroup.total_amount
            # Priority 2: Shipment total_freight_amount
            elif self.shipment and self.shipment.total_freight_amount:
                self.total_freight = self.shipment.total_freight_amount
            # Priority 3: Auto-link consignment group from shipment if not set
            elif self.shipment and hasattr(self.shipment, 'consignment_group') and self.shipment.consignment_group:
                self.consignmentGroup = self.shipment.consignment_group
                if self.consignmentGroup.total_amount:
                    self.total_freight = self.consignmentGroup.total_amount
            # Priority 4: Calculate from individual consignments if available
            elif self.consignmentGroup:
                # Calculate total from all consignments in the group
                consignments = self.consignmentGroup.consignments.all()
                total_freight = sum(
                    c.total_freight for c in consignments if hasattr(c, 'total_freight') and c.total_freight)
                if total_freight > 0:
                    self.total_freight = total_freight
                    # Update the ConsignmentGroup total_amount for future use
                    self.consignmentGroup.total_amount = total_freight
                    self.consignmentGroup.save()

            # Calculate total expenses using aggregation (more efficient)
            if self.shipment:
                expense_total = ShipmentExpense.objects.filter(
                    shipment=self.shipment
                ).aggregate(total=Sum('amount'))['total'] or 0
                self.total_expense = expense_total

                # Calculate total advances using aggregation
                shipment_advance = self.shipment.freight_advance or 0
                shipment_ct = ContentType.objects.get(app_label='operations', model='shipment')
                driver_advance_total = DriverAdvance.objects.filter(
                    shipment=self.shipment,
                    content_type=shipment_ct
                ).aggregate(total=Sum('amount'))['total'] or 0
                self.total_advance = shipment_advance + driver_advance_total
            else:
                # No shipment, set defaults
                self.total_expense = 0
                self.total_advance = 0

            # Calculate payments received using aggregation
            payment_total = Payment.objects.filter(
                invoice=self
            ).aggregate(total=Sum('amount_paid'))['total'] or 0
            self.payment_received = payment_total

            # MAIN FORMULAS IMPLEMENTATION:

            # 1. For Consignments - Total Dues Formula:
            # Total Dues = consignment.totalFreight - (shipment.advanceReceived + driverAdvances.amount) - payments
            # total_deductions = self.total_advance + self.payment_received
            # self.total_dues = self.total_freight - total_deductions

            # inside Invoice.calculate_totals()

            # Add detention to freight
            total_freight_with_detention = float(self.total_freight or 0) + float(self.detention_amount or 0)

            # Total deductions
            total_deductions = float(self.total_advance or 0) + float(self.payment_received or 0)

            # Final dues
            self.total_dues = total_freight_with_detention - total_deductions

            # 2. For Shipments - Final Bill Formula:
            # Final Bill = consignment.totalFreight - driverOrOwnerExpenses
            # self.final_bill_amount = self.total_freight - self.total_expense

            # Calculate balance amount (for compatibility with existing logic)
            self.balance_amount = self.total_freight - self.total_expense

            # Update payment status
            self.is_paid = self.total_dues <= 0
            if self.is_paid and self.status != 'CANCELLED':
                self.status = 'PAID'
            elif self.total_dues > 0:
                self.status = 'PENDING'

            self.save(skip_calculation=True)

        except Exception as e:
            logger.error(f"Error calculating totals for invoice {self.id}: {str(e)}", exc_info=True)
            # Don't raise the exception to prevent cascade failures
            pass

    def expense_breakdown(self):
        from django.apps import apps
        ShipmentExpense = apps.get_model('operations', 'ShipmentExpense')
        return [{
            "date": e.expense_date,
            "type": e.expense_type.display_value if hasattr(e.expense_type, 'display_value') else str(e.expense_type),
            "description": e.description,
            "amount": e.amount
        } for e in ShipmentExpense.objects.filter(shipment=self.shipment)]

    def advance_breakdown(self):
        advances = self.get_driver_advances()
        return [{
            "date": a.date,
            "driver": a.driver.first_name + " " + a.driver.last_name,
            "description": a.description,
            "amount": a.amount,
            "is_settled": a.is_settled,
            "carried_forward": a.carried_forward
        } for a in advances]

    def financial_summary(self):
        """Complete financial breakdown including advances and expenses"""
        return {
            "total_freight": self.total_freight,
            "total_advance": self.total_advance,
            "total_expense": self.total_expense,
            "balance_amount": self.balance_amount,
            "payment_received": self.payment_received,
            "total_dues": self.total_dues,
            # "final_bill_amount": self.final_bill_amount,
            "advance_details": self.advance_breakdown(),
            # "expense_details": self.expense_breakdown(),
            "payment_details": self.payment_breakdown(),
            "payment_status": "Paid" if self.is_paid else "Pending"
        }

    def get_itemized_breakdown(self):
        """Get detailed itemized breakdown of the invoice implementing the exact requirements"""
        return {
            "invoice_details": {
                "invoice_id": self.invoice_id,
                "consignment_group_id": self.consignmentGroup.group_id if self.consignmentGroup else None,
                "shipment_id": self.shipment.shipment_id,
                "issue_date": self.issue_date,
                "due_date": self.due_date,
                "status": self.get_status_display() if hasattr(self, 'get_status_display') else self.status,
            },
            "financial_breakdown": {
                "total_freight": self.total_freight,
                "freight_advance": self.shipment.freight_advance or 0,
                "driver_advances": sum(a.amount for a in self.get_driver_advances() if a.amount),
                "payments_received": self.payment_received,
                "driver_owner_expenses": self.total_expense,
                "remaining_balance": self.total_dues,
                # "final_bill_amount": self.final_bill_amount,
            },
            "itemized_details": {
                "advance_breakdown": self.advance_breakdown(),
                # "expense_breakdown": self.expense_breakdown(),
                "payment_breakdown": self.payment_breakdown(),
            },
            "calculation_summary": {
                "consignment_formula": f"Total Dues = {self.total_freight} - ({self.shipment.freight_advance or 0} + {sum(a.amount for a in self.get_driver_advances() if a.amount)}) - {self.payment_received} = {self.total_dues}",
                "shipment_formula": f"Final Bill = {self.total_freight} - {self.total_expense} = {self.balance_amount}",
            }
        }

    def get_driver_advances(self):
        from django.apps import apps
        DriverAdvance = apps.get_model('operations', 'DriverAdvance')
        from django.contrib.contenttypes.models import ContentType
        shipment_ct = ContentType.objects.get(app_label='operations', model='shipment')
        return DriverAdvance.objects.filter(shipment=self.shipment, content_type=shipment_ct)

    def payment_breakdown(self):
        """Get breakdown of all payments for this invoice"""
        payments = Payment.objects.filter(invoice=self)

        breakdown = []
        for payment in payments:
            breakdown.append({
                "date": payment.payment_date,
                "amount": payment.amount_paid,
                "method": payment.get_payment_method_display() if hasattr(payment,
                                                                          'get_payment_method_display') else payment.method,
                "reference": getattr(payment, 'reference_number', None),
                "status": payment.get_status_display() if hasattr(payment, 'get_status_display') else payment.status,
                "notes": getattr(payment, 'notes', None),
            })

        return breakdown

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        skip_calc = kwargs.pop('skip_calculation', False)
        super().save(*args, **kwargs)  # First save to get the PK if new

        # Generate invoice_id for new invoices
        # if is_new:
        #     today_str = timezone.now().strftime("%Y%m%d")
        #     self.invoice_id = f"ASN/{self.pk}"
        #     # Use update to avoid recursion or infinite loop
        #     Invoice.objects.filter(pk=self.pk).update(invoice_id=self.invoice_id)

        if is_new:
            from django.db.models import Max
            from django.utils import timezone

            today = timezone.now()
            year = today.year
            month = today.month

            # Determine FY start and end
            if month >= 4:
                fy_start = year
                fy_end = year + 1
            else:
                fy_start = year - 1
                fy_end = year

            fy_code = f"FY{str(fy_start)[-2:]}{str(fy_end)[-2:]}"

            # Find last invoice number for this FY
            last_invoice = Invoice.objects.filter(
                invoice_id__icontains=f"/{fy_code}"
            ).aggregate(
                max_no=Max("invoice_id")
            )["max_no"]

            if last_invoice:
                # Extract the 4‑digit number between ASN/ and /FYxxxx
                try:
                    last_no = int(last_invoice.split("/")[1])
                except:
                    last_no = 0
            else:
                last_no = 0

            new_no = last_no + 1
            padded = str(new_no).zfill(4)

            # Final invoice ID
            invoice_id = f"ASN/{padded}/{fy_code}"

            # Save without recursion
            Invoice.objects.filter(pk=self.pk).update(invoice_id=invoice_id)
            self.invoice_id = invoice_id

        # Calculate totals after the initial save
        # Skip if this is part of calculate_totals to avoid infinite recursion

        if not skip_calc:
            self.calculate_totals()


class Transaction(models.Model):
    """
    Simplified Transaction model to capture all financial data from maintenance, shipment expenses,
    driver advances, tyre costs, payments, and other business expenses.
    This serves as a central repository for all financial transactions across the system.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('expense', 'Expense'),
        ('advance', 'Advance'),
        ('revenue', 'Revenue'),
        ('refund', 'Refund'),
    ]

    CATEGORY_CHOICES = [
        ('maintenance', 'Maintenance'),
        ('tyre', 'Tyre'),
        ('fuel', 'Fuel'),
        ('driver', 'Driver'),
        ('shipment', 'Shipment'),
        ('office', 'Office'),
        ('insurance', 'Insurance'),
        ('permit', 'Permit & License'),
        ('toll', 'Toll & Charges'),
        ('other', 'Other'),
    ]

    # Core transaction details (matching your requirements)
    transaction_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default='expense')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateField(default=timezone.now)

    # Entity references (optional but useful for linking)
    shipment = models.ForeignKey('operations.Shipment', on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='transactions')
    driver = models.ForeignKey('entity.Driver', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='transactions')
    vehicle = models.ForeignKey('entity.Vehicle', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='transactions')

    # Related source models for traceability
    related_shipment_expense = models.ForeignKey('operations.ShipmentExpense', on_delete=models.SET_NULL, null=True,
                                                 blank=True, related_name='transactions')
    related_driver_advance = models.ForeignKey('operations.DriverAdvance', on_delete=models.SET_NULL, null=True,
                                               blank=True, related_name='transactions')
    related_maintenance_record = models.ForeignKey('maintenance.MaintenanceRecord', on_delete=models.SET_NULL,
                                                   null=True, blank=True, related_name='transactions')
    related_tyre = models.ForeignKey('maintenance.Tyre', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='financial_transactions')
    related_tyre_transaction = models.ForeignKey('maintenance.TyreTransaction', on_delete=models.SET_NULL, null=True,
                                                 blank=True, related_name='financial_transactions')
    related_other_expense = models.ForeignKey('OfficeExpense', on_delete=models.SET_NULL, null=True, blank=True,
                                              related_name='transactions')
    related_payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='transactions')

    # For audit and traceability
    reference_number = models.CharField(max_length=100, null=True, blank=True, help_text="Invoice no, receipt no, etc.")
    created_by = models.CharField(max_length=50, null=True, blank=True, help_text="Username or staff ID")

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transaction'
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['transaction_date']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['category']),
            models.Index(fields=['shipment']),
            models.Index(fields=['driver']),
            models.Index(fields=['vehicle']),
            models.Index(fields=['reference_number']),
            models.Index(fields=['created_by']),
            # Composite indexes for common queries
            models.Index(fields=['transaction_type', 'category']),
            models.Index(fields=['transaction_date', 'category']),
            models.Index(fields=['driver', 'transaction_date']),
            models.Index(fields=['vehicle', 'transaction_date']),
        ]

    def clean(self):
        """Validate that amount is positive"""
        if self.amount < 0:
            raise ValidationError("Amount must be greater than or equal to 0")

    def __str__(self):
        return f"{self.transaction_type.title()} - {self.category.title()} - ₹{self.amount} on {self.transaction_date}"

    def save(self, *args, **kwargs):
        # Validate amount is positive
        # if self.amount < 0:
        #    raise ValidationError("Amount must be greater than or equal to 0")
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Generate id for new invoices
        if is_new:
            today_str = timezone.now().strftime("%Y%m%d")
            self.transaction_id = f"TRN{today_str}{self.pk}"
            # Use update to avoid recursion or infinite loop
            Transaction.objects.filter(pk=self.pk).update(transaction_id=self.transaction_id)

    def get_transaction_summary(self):
        """Get comprehensive transaction summary"""
        return {
            "id": self.id,
            "transaction_type": self.get_transaction_type_display(),
            "category": self.get_category_display(),
            "amount": self.amount,
            "date": self.transaction_date,
            "description": self.description,
            "reference_number": self.reference_number,
            "created_by": self.created_by,
            "related_entities": {
                "shipment": str(self.shipment) if self.shipment else None,
                "driver": str(self.driver) if self.driver else None,
                "vehicle": str(self.vehicle) if self.vehicle else None,
            },
            "source_model": self.get_source_model(),
        }

    def get_source_model(self):
        """Get the source model that created this transaction"""
        if self.related_shipment_expense:
            return f"ShipmentExpense: {self.related_shipment_expense}"
        elif self.related_driver_advance:
            return f"DriverAdvance: {self.related_driver_advance}"
        elif self.related_maintenance_record:
            return f"MaintenanceRecord: {self.related_maintenance_record}"
        elif self.related_tyre:
            return f"Tyre: {self.related_tyre}"
        elif self.related_tyre_transaction:
            return f"TyreTransaction: {self.related_tyre_transaction}"
        elif self.related_other_expense:
            return f"OfficeExpense: {self.related_other_expense}"
        elif self.related_payment:
            return f"Payment: {self.related_payment}"
        return "Manual Entry"

    @classmethod
    def get_expenses_by_category(cls, start_date=None, end_date=None):
        """Get expenses grouped by category"""
        from django.db.models import Sum
        queryset = cls.objects.filter(transaction_type='expense')

        if start_date:
            queryset = queryset.filter(transaction_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(transaction_date__lte=end_date)

        return queryset.values('category').annotate(total_amount=Sum('amount')).order_by('-total_amount')

    @classmethod
    def get_monthly_summary(cls, year, month):
        """Get monthly financial summary"""
        from django.db.models import Sum
        from datetime import date

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        queryset = cls.objects.filter(
            transaction_date__gte=start_date,
            transaction_date__lt=end_date
        )

        return {
            'expenses': queryset.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0,
            'advances': queryset.filter(transaction_type='advance').aggregate(Sum('amount'))['amount__sum'] or 0,
            'revenue': queryset.filter(transaction_type='revenue').aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_transactions': queryset.count(),
        }


class Payment(models.Model):
    """
    Enhanced Payment model with comprehensive banking integration and strict tenant isolation.
    Each payment belongs to a single tenant.
    """
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('PARTIAL', 'Partial'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('UPI', 'UPI'),
        ('IMPS', 'IMPS'),
        ('NEFT', 'NEFT'),
        ('RTGS', 'RTGS'),
        ('MOBILE_BANKING', 'Mobile Banking'),
        ('NET_BANKING', 'Net Banking'),
        ('WALLET', 'Digital Wallet'),
        ('DEBIT_CARD', 'Debit Card'),
        ('CREDIT_CARD', 'Credit Card'),
    ]

    # Core payment details
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField()
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True,
        related_name='payment_mode_set',
        blank=True,
        limit_choices_to={'category': ChoiceCategory.FINANCE_PAYMENT_MODE},
    )
    reference_number = models.CharField(max_length=100, blank=True, null=True)

    # Enhanced banking fields
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')

    # Banking transaction details
    transaction_reference = models.CharField(max_length=100, null=True, blank=True,
                                             help_text="Bank transaction reference")
    utr_number = models.CharField(max_length=22, null=True, blank=True, help_text="Unique Transaction Reference")
    transaction_id = models.CharField(max_length=100, null=True, blank=True, help_text="Bank transaction ID")

    # Banking account details
    from_banking_detail = models.ForeignKey('configuration.BankingDetail', on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='payments_from', help_text="Source banking account")
    to_banking_detail = models.ForeignKey('configuration.BankingDetail', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='payments_to', help_text="Destination banking account")

    # Processing details
    processed_datetime = models.DateTimeField(null=True, blank=True)
    bank_charges = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Bank charges for payment")
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0000)

    # Cheque specific details
    cheque_number = models.CharField(max_length=20, null=True, blank=True)
    cheque_date = models.DateField(null=True, blank=True)
    cheque_bank = models.CharField(max_length=255, null=True, blank=True)
    cheque_status = models.CharField(max_length=20, choices=[
        ('ISSUED', 'Issued'),
        ('DEPOSITED', 'Deposited'),
        ('CLEARED', 'Cleared'),
        ('BOUNCED', 'Bounced'),
        ('CANCELLED', 'Cancelled'),
    ], null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    # Additional notes
    notes = models.TextField(null=True, blank=True, help_text="Payment notes and remarks")

    def __str__(self):
        return f"Payment of ₹{self.amount_paid} for Invoice #{self.invoice.id} ({self.status})"

    def get_net_amount(self):
        """Get net amount after deducting bank charges"""
        try:
            amount_paid = self.amount_paid or 0
            bank_charges = self.bank_charges or 0
            return amount_paid - bank_charges
        except (AttributeError, TypeError):
            return 0

    def is_successful(self):
        """Check if payment was successful"""
        return self.status in ['COMPLETED', 'PARTIAL']

    def is_banking_payment(self):
        """Check if this is a banking payment (not cash)"""
        return self.payment_method != 'CASH'

    def is_cheque_payment(self):
        """Check if this is a cheque payment"""
        return self.payment_method == 'CHEQUE'

    class Meta:
        db_table = 'payment'
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['payment_date']),
            models.Index(fields=['status']),
            models.Index(fields=['invoice']),
            # Composite indexes for common query patterns
            models.Index(fields=['invoice', 'status']),  # For invoice payments by status
            models.Index(fields=['payment_date', 'status']),  # For date and status filtering
            models.Index(fields=['payment_method', 'status']),  # For method and status filtering
        ]


class OfficeExpense(models.Model):
    category = models.ForeignKey(
        'configuration.Choice',
        on_delete=models.SET_NULL,
        null=True,
        related_name='other_expense_set',
        blank=True,
        limit_choices_to={'category': ChoiceCategory.FINANCE_EXPENSE_CATEGORY},
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    expense_date = models.DateField()
    description = models.CharField(max_length=1000, null=True, blank=True)
    paid_by = models.CharField(max_length=100, blank=True, null=True)  # e.g. accountant or department
    driver = models.ForeignKey('entity.Driver', on_delete=models.CASCADE, related_name='other_expense_driver',
                               null=True, blank=True)
    invoice_document = models.FileField(upload_to=user_document_upload_path, validators=[document_file_validator],
                                        null=True, blank=True, help_text="Purchase invoice document")
    def __str__(self):
        return f"{self.category} - ₹{self.amount} on {self.expense_date}"

    class Meta:
        db_table = 'office_expense'


class BankTransfer(models.Model):
    """
    Dedicated model for tracking bank transfers and online banking transactions
    """
    TRANSFER_TYPE_CHOICES = [
        ('ADVANCE_PAYMENT', 'Advance Payment'),
        ('SALARY_PAYMENT', 'Salary Payment'),
        ('EXPENSE_REIMBURSEMENT', 'Expense Reimbursement'),
        ('VENDOR_PAYMENT', 'Vendor Payment'),
        ('REFUND', 'Refund'),
        ('INTERNAL_TRANSFER', 'Internal Transfer'),
        ('LOAN_DISBURSEMENT', 'Loan Disbursement'),
        ('LOAN_REPAYMENT', 'Loan Repayment'),
        ('OTHER', 'Other'),
    ]

    TRANSFER_STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
        ('RETURNED', 'Returned'),
    ]

    TRANSFER_MODE_CHOICES = [
        ('IMPS', 'IMPS - Immediate Payment Service'),
        ('NEFT', 'NEFT - National Electronic Funds Transfer'),
        ('RTGS', 'RTGS - Real Time Gross Settlement'),
        ('UPI', 'UPI - Unified Payments Interface'),
        ('NET_BANKING', 'Net Banking'),
        ('MOBILE_BANKING', 'Mobile Banking'),
        ('API_TRANSFER', 'API Transfer'),
    ]

    # Core transfer details
    transfer_type = models.CharField(max_length=30, choices=TRANSFER_TYPE_CHOICES)
    from_banking_detail = models.ForeignKey('configuration.BankingDetail', on_delete=models.PROTECT,
                                            related_name='transfers_sent', help_text="Source banking account")
    to_banking_detail = models.ForeignKey('configuration.BankingDetail', on_delete=models.PROTECT,
                                          related_name='transfers_received', help_text="Destination banking account")

    # Amount and transaction details
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Transfer amount")
    bank_charges = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Bank charges for transfer")
    net_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Net amount after charges")

    # Transfer processing details
    transfer_mode = models.CharField(max_length=20, choices=TRANSFER_MODE_CHOICES)
    status = models.CharField(max_length=20, choices=TRANSFER_STATUS_CHOICES, default='INITIATED')

    # Banking transaction references
    transaction_id = models.CharField(max_length=100, unique=True, help_text="Unique transaction identifier")
    utr_number = models.CharField(max_length=22, null=True, blank=True, help_text="UTR number from bank")
    reference_number = models.CharField(max_length=100, null=True, blank=True, help_text="Bank reference number")

    # Timestamps
    initiated_datetime = models.DateTimeField(auto_now_add=True)
    processed_datetime = models.DateTimeField(null=True, blank=True)
    completed_datetime = models.DateTimeField(null=True, blank=True)

    # Beneficiary details (for validation)
    beneficiary_name = models.CharField(max_length=255, help_text="Beneficiary account holder name")
    beneficiary_account_number = models.CharField(max_length=50, help_text="Beneficiary account number")
    beneficiary_ifsc = models.CharField(max_length=11, help_text="Beneficiary IFSC code")

    # Purpose and description
    purpose_code = models.CharField(max_length=10, null=True, blank=True, help_text="Banking purpose code")
    description = models.TextField(help_text="Transfer description and purpose")
    notes = models.TextField(null=True, blank=True, help_text="Internal notes")

    # Related entities
    related_shipment = models.ForeignKey('operations.Shipment', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='bank_transfers')
    related_driver = models.ForeignKey('entity.Driver', on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='bank_transfers')
    related_invoice = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='bank_transfers')
    related_payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='bank_transfers')

    # API integration details
    api_request_id = models.CharField(max_length=100, null=True, blank=True, help_text="API request identifier")
    api_response_data = models.JSONField(null=True, blank=True, help_text="API response data")

    # Audit fields
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bank_transfer'
        ordering = ['-initiated_datetime']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['utr_number']),
            models.Index(fields=['status']),
            models.Index(fields=['initiated_datetime']),
        ]

    def __str__(self):
        return f"Transfer #{self.transaction_id} - ₹{self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        # Calculate net amount if not set
        if not self.net_amount:
            self.net_amount = self.amount - self.bank_charges

        # Generate transaction_id if not set
        if not self.transaction_id:
            import uuid
            self.transaction_id = f"TXN{uuid.uuid4().hex[:10].upper()}"

        super().save(*args, **kwargs)

    def is_successful(self):
        """Check if transfer was successful"""
        return self.status == 'COMPLETED'

    def is_pending(self):
        """Check if transfer is pending"""
        return self.status in ['INITIATED', 'PENDING', 'PROCESSING']

    def get_transfer_duration(self):
        """Get transfer processing duration"""
        if self.completed_datetime and self.initiated_datetime:
            return self.completed_datetime - self.initiated_datetime
        return None

    def get_status_display_with_icon(self):
        """Get status with appropriate icon"""
        status_icons = {
            'COMPLETED': '✅',
            'FAILED': '❌',
            'PENDING': '⏳',
            'PROCESSING': '🔄',
            'CANCELLED': '🚫',
            'REJECTED': '⛔',
        }
        icon = status_icons.get(self.status, '❓')
        return f"{icon} {self.get_status_display()}"

    def transfer_summary(self):
        """Get comprehensive transfer summary"""
        return {
            "transaction_id": self.transaction_id,
            "transfer_type": self.get_transfer_type_display(),
            "amount": self.amount,
            "bank_charges": self.bank_charges,
            "net_amount": self.net_amount,
            "status": self.get_status_display(),
            "transfer_mode": self.get_transfer_mode_display(),
            "from_account": str(self.from_banking_detail),
            "to_account": str(self.to_banking_detail),
            "initiated_datetime": self.initiated_datetime,
            "completed_datetime": self.completed_datetime,
            "utr_number": self.utr_number,
            "reference_number": self.reference_number,
            "description": self.description,
        }


