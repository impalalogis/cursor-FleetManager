from django.contrib import admin
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.contrib import messages
from django.http import HttpResponseRedirect
from .models import Invoice, Payment, Transaction, OfficeExpense, BankTransfer
from .admin_mixins import NavigationButtonMixin
from django.http import HttpResponse
from django.template.loader import render_to_string
from io import BytesIO
from xhtml2pdf import pisa
from django.urls import path, reverse
from pathlib import Path
import base64
from django.conf import settings





import logging

logger = logging.getLogger(__name__)


@admin.register(Payment)
class PaymentAdmin(NavigationButtonMixin,admin.ModelAdmin):
    change_form_template = "admin/payment/change_form.html"

    class Media:
        css = {
            "all": ("financial/css/navigation_buttons.css",)
        }

    def get_queryset(self, request):
        """Optimize queryset with select_related to reduce database queries"""
        return super().get_queryset(request).select_related(
            'invoice',
            'invoice__shipment',
            'invoice__consignmentGroup',
            'method',
            'from_banking_detail',
            'to_banking_detail'
        )

    list_display = (
        'invoice',
        'payment_date',
        'amount_paid',
        'method',
        'status',
        'transaction_reference'
    )
    # list_filter = (
    #     'method',
    #     'status',
    #     'payment_date',
    #     'cheque_status'
    # )
    search_fields = (
        'reference_number',
        'transaction_reference',
        'utr_number',
        'transaction_id',
        'cheque_number'
    )
    readonly_fields = ('created_at', 'updated_at', 'net_amount_display')
    autocomplete_fields = ('invoice', )

    def net_amount_display(self, obj):
        """Display net amount safely"""
        if obj and obj.pk:
            try:
                return f"₹{obj.get_net_amount():.2f}"
            except Exception as e:
                logger.error(f"Error calculating net amount for payment {obj.pk}: {str(e)}", exc_info=True)
                return "₹0.00 (Error)"
        return "₹0.00"

    net_amount_display.short_description = "Net Amount"

    def save_model(self, request, obj, form, change):
        """Override save_model to add error handling and logging"""
        try:
            if not change:  # Creating new payment
                logger.info(
                    f"Creating new payment for invoice {obj.invoice.id if obj.invoice else 'None'} by user {request.user.username}")
            else:  # Updating existing payment
                logger.info(
                    f"Updating payment {obj.id} for invoice {obj.invoice.id if obj.invoice else 'None'} by user {request.user.username}")

            # Set audit fields
            if not change:
                obj.created_by = request.user.username
            obj.updated_by = request.user.username

            super().save_model(request, obj, form, change)

            # Add success message
            action = "created" if not change else "updated"
            messages.success(request, f"Payment {action} successfully.")

        except Exception as e:
            logger.error(f"Error saving payment: {str(e)}", exc_info=True)
            messages.error(request, f"Error saving payment: {str(e)}")

    def delete_model(self, request, obj):
        """Override delete_model to add logging"""
        try:
            logger.info(
                f"Deleting payment {obj.id} for invoice {obj.invoice.id if obj.invoice else 'None'} by user {request.user.username}")
            super().delete_model(request, obj)
            messages.success(request, "Payment deleted successfully.")
        except Exception as e:
            logger.error(f"Error deleting payment {obj.id}: {str(e)}", exc_info=True)
            messages.error(request, f"Error deleting payment: {str(e)}")

    fieldsets = (
        ('Payment Details', {
            'fields': (
                'invoice',
                'payment_date',
                'amount_paid',
                'method',
                'reference_number'
            ),
            'description': 'Basic payment information and reference.'
        }),
        # ('Enhanced Banking Information', {
        #     'fields': (
        #         # 'method',
        #         'status',
        #         'transaction_reference',
        #         'utr_number',
        #         'transaction_id',
        #         'processed_datetime'
        #     ),
        #     'description': 'Banking and payment processing details.'
        # }),
        # ('Banking Accounts', {
        #     'fields': (
        #         'from_banking_detail',
        #         'to_banking_detail'
        #     ),
        #     'description': 'Source and destination banking accounts.'
        # }),
        # ('Processing Details', {
        #     'fields': (
        #         'bank_charges',
        #         'exchange_rate',
        #         'net_amount_display'
        #     ),
        #     'classes': ('collapse',),
        #     'description': 'Processing charges and net amount calculations.'
        # }),
        # ('Cheque Details', {
        #     'fields': (
        #         'cheque_number',
        #         'cheque_date',
        #         'cheque_bank',
        #         'cheque_status'
        #     ),
        #     'classes': ('collapse',),
        #     'description': 'Cheque-specific information (applicable for cheque payments).'
        # }),
        # ('Additional Information', {
        #     'fields': (
        #         'notes',
        #         'created_at',
        #         'updated_at',
        #         'created_by',
        #         'updated_by'
        #     ),
        #     'classes': ('collapse',),
        #     'description': 'Additional notes and audit information.'
        # })
    )

    actions = ['mark_as_completed', 'mark_cheque_cleared']

    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            status='COMPLETED',
            processed_datetime=timezone.now()
        )
        self.message_user(request, f"{updated} payments marked as completed.")

    mark_as_completed.short_description = "Mark payments as completed"

    def mark_cheque_cleared(self, request, queryset):
        updated = queryset.filter(payment_method='CHEQUE').update(
            cheque_status='CLEARED',
            status='COMPLETED'
        )
        self.message_user(request, f"{updated} cheque payments marked as cleared.")

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)

        # No NEXT step for Payment
        next_step_url = None
        next_step_label = None

        # BACK → Invoice (same pattern as Shipment Status / Expenses)
        if obj and obj.invoice:
            back_step_url = reverse("admin:financial_invoice_change", args=[obj.invoice.pk])
            back_step_label = "Back to Invoice"
        else:
            back_step_url = reverse("admin:index")
            back_step_label = "Back to Dashboard"

        extra_context = extra_context or {}
        extra_context.update({
            "next_step_url": next_step_url,
            "next_step_label": next_step_label,
            "back_step_url": back_step_url,
            "back_step_label": back_step_label,
        })

        return super().change_view(request, object_id, form_url, extra_context)

    mark_cheque_cleared.short_description = "Mark cheque payments as cleared"


# @admin.register(BankTransfer)
# class BankTransferAdmin(admin.ModelAdmin):
#     list_display = (
#         'transaction_id',
#         'transfer_type',
#         'amount',
#         'transfer_mode',
#         'status',
#         'beneficiary_name',
#         'initiated_datetime'
#     )
#     # list_filter = (
#     #     'transfer_type',
#     #     'transfer_mode',
#     #     'status',
#     #     'initiated_datetime'
#     # )
#     search_fields = (
#         'transaction_id',
#         'utr_number',
#         'reference_number',
#         'beneficiary_name',
#         'beneficiary_account_number',
#         'description'
#     )
#     readonly_fields = (
#         'transaction_id',
#         'net_amount',
#         'initiated_datetime',
#         'created_at',
#         'updated_at',
#         'get_transfer_duration',
#         'get_status_display_with_icon'
#     )
#
#     fieldsets = (
#         ('Transfer Details', {
#             'fields': (
#                 'transfer_type',
#                 'amount',
#                 'bank_charges',
#                 'net_amount',
#                 'description'
#             )
#         }),
#         ('Banking Accounts', {
#             'fields': (
#                 'from_banking_detail',
#                 'to_banking_detail'
#             )
#         }),
#         ('Processing Information', {
#             'fields': (
#                 'transfer_mode',
#                 'status',
#                 'get_status_display_with_icon',
#                 'transaction_id',
#                 'utr_number',
#                 'reference_number'
#             )
#         }),
#         ('Beneficiary Details', {
#             'fields': (
#                 'beneficiary_name',
#                 'beneficiary_account_number',
#                 'beneficiary_ifsc'
#             )
#         }),
#         ('Purpose and Compliance', {
#             'fields': (
#                 'purpose_code',
#                 'notes'
#             )
#         }),
#         ('Related Entities', {
#             'fields': (
#                 'related_shipment',
#                 'related_driver',
#                 'related_invoice',
#                 'related_payment'
#             ),
#             'classes': ('collapse',)
#         }),
#         ('Timestamps', {
#             'fields': (
#                 'initiated_datetime',
#                 'processed_datetime',
#                 'completed_datetime',
#                 'get_transfer_duration'
#             ),
#             'classes': ('collapse',)
#         }),
#         ('API Integration', {
#             'fields': (
#                 'api_request_id',
#                 'api_response_data'
#             ),
#             'classes': ('collapse',)
#         }),
#         ('Audit Information', {
#             'fields': (
#                 'created_by',
#                 'updated_by',
#                 'created_at',
#                 'updated_at'
#             ),
#             'classes': ('collapse',)
#         })
#     )
#
#     actions = ['mark_as_completed', 'mark_as_failed', 'retry_transfer']
#
#     def mark_as_completed(self, request, queryset):
#         from django.utils import timezone
#         updated = queryset.update(
#             status='COMPLETED',
#             completed_datetime=timezone.now()
#         )
#         self.message_user(request, f"{updated} transfers marked as completed.")
#
#     mark_as_completed.short_description = "Mark transfers as completed"
#
#     def mark_as_failed(self, request, queryset):
#         updated = queryset.update(status='FAILED')
#         self.message_user(request, f"{updated} transfers marked as failed.")
#
#     mark_as_failed.short_description = "Mark transfers as failed"
#
#     def retry_transfer(self, request, queryset):
#         updated = queryset.filter(status__in=['FAILED', 'CANCELLED']).update(
#             status='PENDING'
#         )
#         self.message_user(request, f"{updated} transfers marked for retry.")
#
#     retry_transfer.short_description = "Retry failed transfers"
#
#     def get_transfer_duration(self, obj):
#         """Display transfer duration in a readable format"""
#         duration = obj.get_transfer_duration()
#         if duration:
#             total_seconds = int(duration.total_seconds())
#             hours, remainder = divmod(total_seconds, 3600)
#             minutes, seconds = divmod(remainder, 60)
#             if hours > 0:
#                 return f"{hours}h {minutes}m {seconds}s"
#             elif minutes > 0:
#                 return f"{minutes}m {seconds}s"
#             else:
#                 return f"{seconds}s"
#         return "Not completed"
#
#     get_transfer_duration.short_description = "Transfer Duration"
#
#     def get_status_display_with_icon(self, obj):
#         """Display status with icon"""
#         return obj.get_status_display_with_icon()
#
#     get_status_display_with_icon.short_description = "Status"


# Inline forms for Invoice
class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1
    fields = ('payment_date', 'amount_paid', 'payment_method', 'status', 'reference_number', 'notes')
    readonly_fields = ()


@admin.register(Invoice)
# class InvoiceAdmin(admin.ModelAdmin):
class InvoiceAdmin(NavigationButtonMixin, admin.ModelAdmin):
    change_form_template = "admin/invoice/change_form.html"

    class Media:
        css = {
            "all": ("financial/css/navigation_buttons.css",)
        }



    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related to reduce database queries"""
        return super().get_queryset(request).select_related(
            'shipment',
            'shipment__driver',
            'shipment__vehicle',
            'shipment__transporter',
            'consignmentGroup',
            # 'consignment__consignor_name',
            # 'consignment__consignee_name'
        ).prefetch_related(
            'payments',
            'shipment__expenses',
            # 'shipment__driver_advances'
        )


    list_display = [
        'invoice_id',
        'payment_buttons',
        'generate_invoice_pdf_button',
        'shipment',
        'total_freight',
        'total_dues',
        'status',
        'is_paid',
        'issue_date'
    ]

    #list_filter = ['status', 'is_paid', 'issue_date']
    search_fields = ['invoice_id', 'shipment__shipment_id']  # 'consignment__consignment_id',
    # readonly_fields = [
    #     'invoice_id', 'issue_date', 'total_freight', 'total_advance',
    #     'payment_received', 'total_expense', 'total_dues', 'balance_amount',
    #     'detailed_breakdown_display', 'payment_breakdown_display',
    #     'expense_breakdown_display', 'advance_breakdown_display'
    # ]

    readonly_fields = [
        'invoice_id', 'issue_date', 'total_freight', 'total_advance',
        'payment_received', 'total_expense', 'total_dues', 'balance_amount',
        'financial_ledger_display', 'expense_ledger_display'
    ]


    autocomplete_fields = ("consignmentGroup", "shipment",)
    # fieldsets = [
    #     ('Invoice Information', {
    #         'fields': [
    #             'invoice_id', 'invoice_ref',  'shipment', 'issue_date', 'due_date', 'status'
    #         ]
    #         # consignmentGroup
    #     }),
    #     ('Financial Summary', {
    #         'fields': [
    #             'total_freight','detention_amount', 'total_advance', 'payment_received', 'total_dues', 'is_paid'
    #         ]
    #     }),
    #
    #     ('Financial Breakdowns', {
    #         'fields': [
    #             'detailed_breakdown_display', 'advance_breakdown_display',
    #             'payment_breakdown_display'
    #         ],
    #
    #         'classes': ('collapse',)
    #     }),
    #     ('Expenses Summary', {
    #         'fields': [
    #             'total_expense', 'balance_amount',
    #         ]
    #     }),
    #     ('Expenses Breakdowns', {
    #         'fields': [
    #             'expense_breakdown_display',
    #         ],
    #
    #         'classes': ('collapse',)
    #     }),
    #     ('Additional Information', {
    #         'fields': ['notes']
    #     }),
    #     ('Audit Information', {
    #         'fields': ['created_by', 'updated_by'],
    #         'classes': ('collapse',)
    #     })
    # ]

    fieldsets = [
        ('Invoice Information', {
            'fields': [
                'invoice_id', 'invoice_ref', 'shipment','bill_to',
                'issue_date', 'due_date', 'status','detention_amount'
            ]
        }),

        ('Financial Ledger', {
            'fields': ['financial_ledger_display'],
        }),

        ('Expense Summary', {
            'fields': ['expense_ledger_display'],
        }),

        ('Additional Information', {
            'fields': ['notes']
        }),

        ('Audit Information', {
            'fields': ['created_by', 'updated_by'],
            'classes': ('collapse',)
        })
    ]

    inlines = [PaymentInline]
    actions = ['update_database_fields', 'calculate_totals_action', 'mark_as_paid', 'mark_as_pending']

    def detailed_breakdown_display(self, obj):
        """Display comprehensive financial breakdown including detention"""
        from django.utils.html import format_html

        if not obj.pk:
            return format_html("<em>Save the invoice first to see breakdown</em>")

        breakdown = obj.get_itemized_breakdown()

        # Base values from model breakdown
        total_freight = float(breakdown['financial_breakdown']['total_freight'] or 0)
        freight_advance = float(breakdown['financial_breakdown']['freight_advance'] or 0)
        driver_advances = float(breakdown['financial_breakdown']['driver_advances'] or 0)
        payments_received = float(breakdown['financial_breakdown']['payments_received'] or 0)

        # Detention from invoice
        detention = float(obj.detention_amount or 0)

        # Recompute remaining balance including detention
        total_advances = freight_advance + driver_advances
        remaining_balance = (total_freight + detention) - total_advances - payments_received

        html_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h4>Revenue</h4>
            <p><strong>Total Freight:</strong> ₹{total_freight:,.2f}</p>
            <p><strong>Detention Amount:</strong> ₹{detention:,.2f}</p>

            <h4>Deductions</h4>
            <p><strong>Advance Received:</strong> ₹{freight_advance:,.2f}</p>
            <p><strong>Driver Advances:</strong> ₹{driver_advances:,.2f}</p>
            <p><strong>Payments Received:</strong> ₹{payments_received:,.2f}</p>

            <h4>Final Amounts</h4>
            <p><strong>Remaining Balance (Freight + Detention) -( Advances + Payments):</strong>
               ₹{remaining_balance:,.2f}</p>

            <h4>Calculation Formula</h4>
            <p><code>(Total Freight + Detention) - (Advance + Driver Advances + Payments)</code></p>
        </div>
        """

        return format_html(html_content)

    detailed_breakdown_display.short_description = "Financial Breakdown"



    def advance_breakdown_display(self, obj):
        """Display advance breakdown"""
        from django.utils.html import format_html

        if not obj.pk:
            return format_html("<em>Save the invoice first</em>")

        advances = obj.advance_breakdown()
        shipment_advance = obj.shipment.freight_advance or 0

        html_parts = [
            f"<h4>Advance Breakdown</h4>",
            f"<p><strong>Shipment Advance:</strong> ₹{shipment_advance:,.2f}</p>",
            f"<h5>Driver Advances:</h5>"
        ]

        if advances:
            html_parts.append("<ul>")
            for advance in advances:
                status_icon = "✅" if advance['is_settled'] else "⏳"
                html_parts.append(
                    f"<li>{advance['date']} - {advance['driver']}: ₹{advance['amount']:,.2f} "
                    f"({advance['description'] or 'No description'}) {status_icon}</li>"
                )
            html_parts.append("</ul>")
        else:
            html_parts.append("<p><em>No driver advances recorded</em></p>")

        html_parts.append(f"<p><strong>Total Advances:</strong> ₹{obj.total_advance:,.2f}</p>")

        return format_html('<div style="font-family: Arial, sans-serif;">{}</div>'.format(''.join(html_parts)))

    advance_breakdown_display.short_description = "Advance Details"

    def expense_breakdown_display(self, obj):
        """Display expense breakdown"""
        from django.utils.html import format_html

        if not obj.pk:
            return format_html("<em>Save the invoice first</em>")

        expenses = obj.expense_breakdown()

        html_parts = [f"<h4>Expense Breakdown</h4>"]

        if expenses:
            html_parts.append("<ul>")
            for expense in expenses:
                html_parts.append(
                    f"<li>{expense['date']} - {expense['type']}: ₹{expense['amount']:,.2f} "
                    f"({expense['description'] or 'No description'})</li>"
                )
            html_parts.append("</ul>")
        else:
            html_parts.append("<p><em>No expenses recorded</em></p>")

        html_parts.append(f"<p><strong>Total Expenses:</strong> ₹{obj.total_expense:,.2f}</p>")

        return format_html('<div style="font-family: Arial, sans-serif;">{}</div>'.format(''.join(html_parts)))

    expense_breakdown_display.short_description = "Expense Details"

    def payment_breakdown_display(self, obj):
        """Display payment breakdown"""
        from django.utils.html import format_html

        if not obj.pk:
            return format_html("<em>Save the invoice first</em>")

        payments = obj.payment_breakdown()

        html_parts = [f"<h4>Payment Breakdown</h4>"]

        if payments:
            html_parts.append("<ul>")
            for payment in payments:
                status_icon = "✅" if payment['status'] == 'COMPLETED' else "⏳"
                html_parts.append(
                    f"<li>{payment['date']} - ₹{payment['amount']:,.2f} via {payment['method']} {status_icon}"
                )
                if payment['reference']:
                    html_parts.append(f"<br><small>Ref: {payment['reference']}</small>")
                html_parts.append("</li>")
            html_parts.append("</ul>")
        else:
            html_parts.append("<p><em>No payments recorded</em></p>")

        html_parts.append(f"<p><strong>Total Payments:</strong> ₹{obj.payment_received:,.2f}</p>")

        return format_html('<div style="font-family: Arial, sans-serif;">{}</div>'.format(''.join(html_parts)))

    payment_breakdown_display.short_description = "Payment Details"

    # Real-time calculated field display methods
    def total_freight_display(self, obj):
        """Display calculated total freight"""
        # Get freight amount from multiple sources with priority order
        freight = 0
        freight_source = "Unknown"

        # Priority 1: ConsignmentGroup total_amount
        if obj.consignmentGroup and obj.consignmentGroup.total_amount:
            freight = float(obj.consignmentGroup.total_amount)
            freight_source = "ConsignmentGroup"
        # Priority 2: Shipment total_freight_amount
        elif obj.shipment and obj.shipment.total_freight_amount:
            freight = float(obj.shipment.total_freight_amount)
            freight_source = "Shipment"
        # Priority 3: Invoice total_freight field
        elif obj.total_freight:
            freight = float(obj.total_freight)
            freight_source = "Invoice"

        return f"₹{freight:,.2f}"

    def total_advance_display(self, obj):
        """Display calculated total advances"""
        from django.apps import apps
        from django.db.models import Sum

        try:
            DriverAdvance = apps.get_model('operations', 'DriverAdvance')
            shipment_advance = obj.shipment.freight_advance or 0
            driver_advance_total = DriverAdvance.objects.filter(
                shipment=obj.shipment
            ).aggregate(total=Sum('amount'))['total'] or 0
            total = shipment_advance + driver_advance_total
            return f"₹{total:,.2f}"
        except:
            return f"₹{obj.total_advance or 0:,.2f}"

    def total_expense_display(self, obj):
        """Display calculated total expenses"""
        from django.apps import apps
        from django.db.models import Sum

        try:
            ShipmentExpense = apps.get_model('operations', 'ShipmentExpense')
            expense_total = ShipmentExpense.objects.filter(
                shipment=obj.shipment
            ).aggregate(total=Sum('amount'))['total'] or 0
            return f"₹{expense_total:,.2f}"
        except:
            return f"₹{obj.total_expense or 0:,.2f}"

    def payment_received_display(self, obj):
        """Display calculated payment received"""
        from django.db.models import Sum

        payment_total = Payment.objects.filter(
            invoice=obj
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        return f"₹{payment_total:,.2f}"

    def total_dues_display(self, obj):
        """Display calculated total dues including detention amount"""
        from django.db.models import Sum

        try:
            # 1. Freight
            if obj.consignmentGroup and obj.consignmentGroup.total_amount:
                freight = float(obj.consignmentGroup.total_amount)
            elif obj.shipment and obj.shipment.total_freight_amount:
                freight = float(obj.shipment.total_freight_amount)
            else:
                freight = float(obj.total_freight or 0)

            # 2. Detention Amount
            detention = float(obj.detention_amount or 0)

            # 3. Advances
            if obj.shipment:
                from operations.models import DriverAdvance
                shipment_advance = float(obj.shipment.freight_advance or 0)
                driver_advances = DriverAdvance.objects.filter(
                    shipment=obj.shipment
                ).aggregate(total=Sum('amount'))['total'] or 0
                total_advances = shipment_advance + float(driver_advances)
            else:
                total_advances = float(obj.total_advance or 0)

            # 4. Payments
            payments = Payment.objects.filter(invoice=obj).aggregate(
                total=Sum('amount_paid')
            )['total'] or 0
            payments = float(payments)

            # 5. FINAL FORMULA: (freight + detention) - advances - payments
            total_dues = (freight + detention) - (total_advances + payments)

            # 6. Color coding
            color = "green" if total_dues <= 0 else "red"
            status = " (Fully Paid)" if total_dues <= 0 else " (Outstanding)"

            return format_html(
                '<span style="color:{}; font-weight:bold;">₹{:,.2f}{}</span>',
                color, total_dues, status
            )

        except Exception:
            total_dues = obj.total_dues or 0
            color = "green" if total_dues <= 0 else "red"
            status = " (Fully Paid)" if total_dues <= 0 else " (Outstanding)"
            return format_html(
                '<span style="color:{}; font-weight:bold;">₹{:,.2f}{}</span>',
                color, total_dues, status
            )

    def balance_amount_display(self, obj):
        """Display calculated balance amount (freight - expenses)"""
        # Get freight amount from multiple sources with priority order
        freight = 0

        # Priority 1: ConsignmentGroup total_amount
        if obj.consignmentGroup and obj.consignmentGroup.total_amount:
            freight = float(obj.consignmentGroup.total_amount)
        # Priority 2: Shipment total_freight_amount
        elif obj.shipment and obj.shipment.total_freight_amount:
            freight = float(obj.shipment.total_freight_amount)
        # Priority 3: Invoice total_freight field
        elif obj.total_freight:
            freight = float(obj.total_freight)

        # Get real-time expenses
        from django.apps import apps
        from django.db.models import Sum

        try:
            ShipmentExpense = apps.get_model('operations', 'ShipmentExpense')
            expense_total = ShipmentExpense.objects.filter(
                shipment=obj.shipment
            ).aggregate(total=Sum('amount'))['total'] or 0
            expense_total = float(expense_total)
        except:
            expense_total = float(obj.total_expense or 0)

        balance = freight - expense_total
        return f"₹{balance:,.2f}"

    def save_model(self, request, obj, form, change):
        """Override save to automatically update calculated fields"""
        super().save_model(request, obj, form, change)
        # Trigger calculation update after saving
        try:
            obj.calculate_totals()
        except Exception as e:
            # Log error but don't break the save process
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating totals for invoice {obj.id}: {str(e)}")

    def calculate_totals_action(self, request, queryset):
        """Admin action to recalculate totals for selected invoices"""
        success_count = 0
        error_count = 0

        for invoice in queryset:
            try:
                invoice.calculate_totals()
                success_count += 1
                logger.info(f"Recalculated totals for invoice {invoice.id} by user {request.user.username}")
            except Exception as e:
                error_count += 1
                logger.error(f"Error recalculating totals for invoice {invoice.id}: {str(e)}", exc_info=True)

        if success_count > 0:
            messages.success(request, f"Totals recalculated for {success_count} invoices.")
        if error_count > 0:
            messages.error(request, f"Failed to recalculate totals for {error_count} invoices. Check logs for details.")

    calculate_totals_action.short_description = "Recalculate totals"

    def update_database_fields(self, request, queryset):
        """Admin action to update calculated fields in database for selected invoices"""
        from django.apps import apps
        from django.db.models import Sum

        success_count = 0
        error_count = 0

        for invoice in queryset:
            try:
                DriverAdvance = apps.get_model('operations', 'DriverAdvance')
                ShipmentExpense = apps.get_model('operations', 'ShipmentExpense')

                # Total freight (from consignment group if available)
                if invoice.consignmentGroup and hasattr(invoice.consignmentGroup, 'total_amount'):
                    invoice.total_freight = invoice.consignmentGroup.total_amount or 0

                # Total advances
                shipment_advance = invoice.shipment.freight_advance or 0
                driver_advance_total = DriverAdvance.objects.filter(
                    shipment=invoice.shipment
                ).aggregate(total=Sum('amount'))['total'] or 0
                invoice.total_advance = shipment_advance + driver_advance_total

                # Total expenses
                expense_total = ShipmentExpense.objects.filter(
                    shipment=invoice.shipment
                ).aggregate(total=Sum('amount'))['total'] or 0
                invoice.total_expense = expense_total

                # Payments received
                payment_total = Payment.objects.filter(
                    invoice=invoice
                ).aggregate(total=Sum('amount_paid'))['total'] or 0
                invoice.payment_received = payment_total

                # Detention
                detention = float(invoice.detention_amount or 0)

                # Calculate totals: (freight + detention) - (advances + payments)
                total_deductions = invoice.total_advance + invoice.payment_received
                invoice.total_dues = (invoice.total_freight + invoice.detention_amount) - total_deductions

                # Balance (freight - expenses) – detention does NOT affect this
                invoice.balance_amount = invoice.total_freight - invoice.total_expense

                # Update payment status
                invoice.is_paid = invoice.total_dues <= 0
                if invoice.is_paid and invoice.status != 'CANCELLED':
                    invoice.status = 'PAID'
                elif invoice.total_dues > 0:
                    invoice.status = 'PENDING'

                invoice.save(skip_calculation=True)
                success_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Error updating database fields for invoice {invoice.id}: {str(e)}", exc_info=True)

        if success_count > 0:
            messages.success(request, f"Database fields updated for {success_count} invoices.")
        if error_count > 0:
            messages.error(
                request,
                f"Failed to update database fields for {error_count} invoices. Check logs for details."
            )

    update_database_fields.short_description = "Update calculated fields in database"



    def mark_as_paid(self, request, queryset):
        """Admin action to mark invoices as paid"""
        queryset.update(is_paid=True, status='PAID')
        self.message_user(request, f"{queryset.count()} invoices marked as paid.")

    mark_as_paid.short_description = "Mark as paid"

    def mark_as_pending(self, request, queryset):
        """Admin action to mark invoices as pending"""
        queryset.update(is_paid=False, status='PENDING')
        self.message_user(request, f"{queryset.count()} invoices marked as pending.")



    @admin.display(description="Next", ordering=None)
    def next_step_list_button(self, obj):
        payment = obj.payments.first()  # related_name='payments'

        if payment:
            return self.nav_button(
                "View",
                "admin:financial_payment_change",
                payment.pk
            )
        else:
            return self.nav_button(
                "Add",
                "admin:financial_payment_add",
                params={"invoice": obj.pk}
            )

    @admin.display(description="Payments", ordering=None)
    def payment_buttons(self, obj):
        count = obj.payments.count()

        if count == 0:
            # Only "Add Payment"
            return self.nav_button(
                "Add Payment",
                "admin:financial_payment_add",
                params={"invoice": obj.pk}
            )

        # "Add New" + "View All (N)"
        add_btn = self.nav_button(
            "Add New",
            "admin:financial_payment_add",
            params={"invoice": obj.pk}
        )
        view_btn = self.nav_button(
            f"View All ({count})",
            "admin:financial_payment_changelist",
            params={"invoice__id__exact": obj.pk}
        )
        return format_html('{}&nbsp;{}', add_btn, view_btn)

    # ---------- CHANGE FORM PAYMENT BUTTONS (bottom row) ----------

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)

        payment_count = obj.payments.count() if obj else 0

        add_payment_url = reverse("admin:financial_payment_add") + f"?invoice={obj.pk}"
        view_payment_url = reverse("admin:financial_payment_changelist") + f"?invoice__id__exact={obj.pk}"

        # Back button
        if obj and obj.shipment:
            back_step_url = reverse("admin:operations_shipment_change", args=[obj.shipment.pk])
            back_step_label = "Back to Shipment"
        else:
            back_step_url = reverse("admin:index")
            back_step_label = "Back to Dashboard"

        # -----------------------------
        # BILL TO LOGIC (CORRECT PLACE)
        # -----------------------------
        bill_to_party = None
        bill_to_address = None
        bill_to_gst = None

        consignments = []
        if obj.shipment and obj.shipment.consignment_group:
            consignments = obj.shipment.consignment_group.consignments.all()

        party = None

        if obj.bill_to == "CONSIGNOR":
            party = consignments[0].consignor if consignments else None

        elif obj.bill_to == "CONSIGNEE":
            party = consignments[0].consignee if consignments else None

        elif obj.bill_to == "TRANSPORTER":
            party = obj.shipment.transporter if obj.shipment and obj.shipment.transporter else None

        elif obj.bill_to == "BROKER":
            party = obj.shipment.broker if obj.shipment and obj.shipment.broker else None

        if party:
            bill_to_party = getattr(party, "organization_name", str(party))
            bill_to_address = party.get_formatted_address() if hasattr(party, "get_formatted_address") else ""
            bill_to_gst = getattr(party, "GST_NO", "")

        # -----------------------------

        extra_context = extra_context or {}
        extra_context.update({
            "payment_count": payment_count,
            "add_payment_url": add_payment_url,
            "view_payment_url": view_payment_url,

            "bill_to_party": bill_to_party,
            "bill_to_address": bill_to_address,
            "bill_to_gst": bill_to_gst,

            "back_step_url": back_step_url,
            "back_step_label": back_step_label,
        })

        return super().change_view(request, object_id, form_url, extra_context)

    @admin.display(description="PDF")
    def generate_invoice_pdf_button(self, obj):
        url = reverse("admin:financial_invoice_pdf", args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank" class="button" '
            'style="margin-left: 5px;">Invoice</a>',
            url
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:invoice_id>/pdf/",
                self.admin_site.admin_view(self.generate_invoice_pdf_view),
                name="financial_invoice_pdf",
            ),
        ]
        return custom_urls + urls

    def generate_invoice_pdf_view(self, request, invoice_id):
        invoice = Invoice.objects.select_related(
            "shipment",
            "shipment__driver",
            "shipment__vehicle",
            "shipment__consignment_group",
        ).prefetch_related(
            "shipment__consignment_group__consignments",
            "payments",
        ).get(pk=invoice_id)

        consignments = invoice.shipment.consignment_group.consignments.all() \
            if invoice.shipment and invoice.shipment.consignment_group else []

        # Load signature
        signature_uri = None
        signature_path = Path(settings.BASE_DIR) / "operations" / "static" / "images" / "authorized_signature.png"
        if signature_path.exists():
            with open(signature_path, "rb") as f:
                signature_uri = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

        # -----------------------------
        # BILL TO LOGIC
        # -----------------------------
        bill_to_party = None
        bill_to_address = None
        bill_to_gst = None
        party = None

        if invoice.bill_to == "CONSIGNOR":
            party = consignments[0].consignor if consignments else None

        elif invoice.bill_to == "CONSIGNEE":
            party = consignments[0].consignee if consignments else None

        elif invoice.bill_to == "TRANSPORTER":
            party = invoice.shipment.transporter if invoice.shipment and invoice.shipment.transporter else None

        elif invoice.bill_to == "BROKER":
            party = invoice.shipment.broker if invoice.shipment and invoice.shipment.broker else None

        if party:
            bill_to_party = getattr(party, "organization_name", str(party))
            bill_to_address = party.get_formatted_address() if hasattr(party, "get_formatted_address") else ""
            bill_to_gst = getattr(party, "GST_NO", "")

        # -----------------------------

        context = {
            "invoice": invoice,
            "shipment": invoice.shipment,
            "consignments": consignments,
            "detention_amount": invoice.detention_amount,
            "breakdown": invoice.get_itemized_breakdown(),
            "signature_uri": signature_uri,
        }

        # ⭐ ADD THIS ⭐
        context.update({
            "bill_to_party": bill_to_party,
            "bill_to_address": bill_to_address,
            "bill_to_gst": bill_to_gst,
        })

        html = render_to_string("admin/invoice/invoice_pdf.html", context)

        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)

        if pdf.err:
            return HttpResponse("Error generating PDF", status=500)

        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="invoice_{invoice.invoice_id}.pdf"'
        return response


    mark_as_pending.short_description = "Mark as pending"

    # Field descriptions for database fields are handled by model field definitions
    @admin.display(description="Financial Ledger")
    def financial_ledger_display(self, obj):
        if not obj.pk:
            return mark_safe("<em>Save invoice to view ledger</em>")

        breakdown = obj.get_itemized_breakdown()

        total_freight = float(breakdown['financial_breakdown']['total_freight'] or 0)
        detention = float(obj.detention_amount or 0)
        freight_advance = float(breakdown['financial_breakdown']['freight_advance'] or 0)
        driver_advances = float(breakdown['financial_breakdown']['driver_advances'] or 0)
        payments_received = float(breakdown['financial_breakdown']['payments_received'] or 0)
        total_expense = float(obj.total_expense or 0)

        total_advances = freight_advance + driver_advances
        final_dues = (total_freight + detention) - (total_advances + payments_received)

        color = "lime" if final_dues <= 0 else "red"
        status = "PAID" if final_dues <= 0 else "OUTSTANDING"

        html = f"""
        <table style="width:100%; border-collapse: collapse; font-size:14px;
                      background:#000; color:#fff; border:1px solid #444;">

            <tr>
                <th colspan="3" style="text-align:left; padding:8px; background:#111; color:#fff;">
                    Financial Ledger
                </th>
            </tr>

            <tr>
                <td rowspan="2" style="padding:6px; border-bottom:1px solid #333;"><strong>Freight</strong></td>
                <td style="padding:6px;">Total Freight</td>
                <td style="padding:6px;">₹{total_freight:,.2f}</td>
            </tr>
            <tr>
                <td style="padding:6px;">Detention</td>
                <td style="padding:6px;">₹{detention:,.2f}</td>
            </tr>

            <tr>
                <td rowspan="3" style="padding:6px; border-bottom:1px solid #333;"><strong>Advances</strong></td>
                <td style="padding:6px;">Shipment Advance</td>
                <td style="padding:6px;">₹{freight_advance:,.2f}</td>
            </tr>
            <tr>
                <td style="padding:6px;">Driver Advances</td>
                <td style="padding:6px;">₹{driver_advances:,.2f}</td>
            </tr>
            <tr>
                <td style="padding:6px;"><strong>Total Advances</strong></td>
                <td style="padding:6px;"><strong>₹{total_advances:,.2f}</strong></td>
            </tr>

            <tr>
                <td style="padding:6px;"><strong>Payments</strong></td>
                <td style="padding:6px;">Payments Received</td>
                <td style="padding:6px;">₹{payments_received:,.2f}</td>
            </tr>

            <tr>
                <td rowspan="2" style="padding:6px;"><strong>Final Dues</strong></td>
                <td style="padding:6px;"><strong>Status: {status}</strong></td>
                <td style="padding:6px; color:{color};"><strong>₹{final_dues:,.2f}</strong></td>
            </tr>
        </table>
        """

        return mark_safe(html)

    @admin.display(description="Expense Summary")
    def expense_ledger_display(self, obj):
        if not obj.pk:
            return mark_safe("<em>Save invoice to view expenses</em>")

        expenses = obj.expense_breakdown()

        html = """
        <table style="width:100%; border-collapse: collapse; font-size:14px;
                      background:#000; color:#fff; border:1px solid #444;">

            <tr>
                <th colspan="4" style="text-align:left; padding:8px; background:#111; color:#fff;">
                    Expense Summary
                </th>
            </tr>

            <tr>
                <th style="padding:6px; border-bottom:1px solid #333;">Date</th>
                <th style="padding:6px; border-bottom:1px solid #333;">Type</th>
                <th style="padding:6px; border-bottom:1px solid #333;">Description</th>
                <th style="padding:6px; border-bottom:1px solid #333;">Amount</th>
            </tr>
        """

        if expenses:
            for e in expenses:
                html += f"""
                <tr>
                    <td style="padding:6px; border-bottom:1px solid #222;">{e['date']}</td>
                    <td style="padding:6px; border-bottom:1px solid #222;">{e['type']}</td>
                    <td style="padding:6px; border-bottom:1px solid #222;">{e['description'] or '-'}</td>
                    <td style="padding:6px; border-bottom:1px solid #222;">₹{e['amount']:,.2f}</td>
                </tr>
                """
        else:
            html += """
            <tr>
                <td colspan="4" style="padding:6px;"><em>No expenses recorded</em></td>
            </tr>
            """

        html += f"""
            <tr style="background:#111;">
                <td colspan="3" style="padding:6px; text-align:right;"><strong>Total Expenses:</strong></td>
                <td style="padding:6px;"><strong>₹{obj.total_expense:,.2f}</strong></td>
            </tr>
        </table>
        """

        return mark_safe(html)



@admin.register(OfficeExpense)
class OfficeExpenseAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Expense Details', {
            'fields': ('category', 'amount', 'expense_date', 'paid_by'),
            'description': 'Basic expense information and who paid for it.'
        }),
        ('Description & Documentation', {
            'fields': ('description', 'invoice_document'),
            'description': 'Detailed description and supporting documents.'
        })
    )

    list_display = ('category', 'amount', 'expense_date', 'paid_by')
    # list_filter = ('category', 'expense_date')
    search_fields = ('description', 'paid_by')
    date_hierarchy = 'expense_date'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'category', 'transaction_type', 'amount', 'transaction_date', 'description']
    # list_filter = ['category', 'transaction_date', 'transaction_type', 'shipment', 'driver', ]
    search_fields = ['description', 'reference_number', 'shipment__shipment_id', 'driver__first_name',
                     'driver__last_name', ]
    readonly_fields = ['transaction_id', 'reference_number', 'created_by', ]

    fieldsets = [
        ('Transaction Information', {
            'fields': [
                'transaction_id', 'category', 'transaction_type', 'amount', 'transaction_date', 'description'
            ]
        }),
        ('Related Entities', {
            'fields': [
                'shipment', 'driver', 'vehicle'
            ]
        }),
        ('Related Records', {
            'fields': [
                'related_shipment_expense', 'related_driver_advance', 'related_maintenance_record',
                'related_tyre', 'related_tyre_transaction', 'related_other_expense', 'related_payment'
            ],
            'classes': ['collapse']
        }),
        ('Additional Information', {
            'fields': [
                'reference_number', 'created_by'
            ],
            'classes': ['collapse']
        })
    ]
