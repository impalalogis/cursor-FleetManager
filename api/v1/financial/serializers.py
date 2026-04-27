"""
Financial Serializers for Fleet Manager API
Comprehensive serializers matching admin panel functionality
"""

from rest_framework import serializers
from financial.models import (
    Invoice, Payment, Transaction, OfficeExpense, BankTransfer
)
from operations.models import Shipment, Consignment
from setting.models import Choice, BankingDetail


class InvoiceSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Invoice model"""
    shipment_id = serializers.CharField(source='shipment.shipment_id', read_only=True)
    consignment_group_id = serializers.CharField(source='consignmentGroup.group_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_paid = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_id', 'invoice_ref', 'shipment', 'shipment_id',
            'consignmentGroup', 'consignment_group_id', 'issue_date', 'due_date',
            'total_freight', 'total_expense', 'total_advance', 'balance_amount',
            'payment_received', 'total_dues', 'total_paid', 'balance_due',
            'status', 'status_display', 'is_paid', 'notes', 'created_by', 'updated_by'
        ]
        read_only_fields = ['invoice_id', 'issue_date', 'created_by', 'updated_by']
    

    
    def get_total_paid(self, obj):
        """Get total amount paid"""
        payments = obj.payments.filter(status='COMPLETED')
        return float(sum(payment.amount_paid for payment in payments))
    
    def get_balance_due(self, obj):
        """Get balance due"""
        total_paid = self.get_total_paid(obj)
        return float((obj.total_dues or 0) - total_paid)


class InvoiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Invoice list view"""
    shipment_id = serializers.CharField(source='shipment.shipment_id', read_only=True)
    total_paid = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_id', 'shipment_id', 'issue_date',
            'due_date', 'total_dues', 'total_paid', 'balance_due',
            'status', 'is_paid'
        ]
    
    def get_total_paid(self, obj):
        """Get total amount paid"""
        payments = obj.payments.filter(status='COMPLETED')
        return float(sum(payment.amount_paid for payment in payments))
    
    def get_balance_due(self, obj):
        """Get balance due"""
        total_paid = self.get_total_paid(obj)
        return float((obj.total_dues or 0) - total_paid)


class PaymentSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Payment model"""
    invoice_id = serializers.CharField(source='invoice.invoice_id', read_only=True)
    method_display = serializers.CharField(source='method.display_name', read_only=True)
    from_bank_name = serializers.CharField(source='from_banking_detail.bank_name', read_only=True)
    to_bank_name = serializers.CharField(source='to_banking_detail.bank_name', read_only=True)
    net_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'invoice', 'invoice_id', 'payment_date', 'amount_paid',
            'method', 'method_display', 'reference_number', 'transaction_reference',
            'utr_number', 'transaction_id', 'cheque_number', 'cheque_date',
            'cheque_status', 'from_banking_detail', 'from_bank_name',
            'to_banking_detail', 'to_bank_name', 'status', 'net_amount',
            'notes', 'created_at', 'updated_at'
        ]
    
    def get_net_amount(self, obj):
        """Get net amount after deductions"""
        try:
            return float(obj.get_net_amount())
        except:
            return float(obj.amount_paid or 0)


class TransactionSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Transaction model"""
    payment_invoice = serializers.CharField(source='payment.invoice.invoice_number', read_only=True)
    payment_method = serializers.CharField(source='payment.method.display_name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'payment', 'payment_invoice', 'payment_method',
            'transaction_date', 'amount', 'transaction_type', 'reference_number',
            'bank_charges', 'gst_on_charges', 'net_amount', 'reconciled',
            'reconciliation_date', 'notes'
        ]


class OtherExpenseSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for OfficeExpense model"""
    expense_type_display = serializers.CharField(source='expense_type.display_name', read_only=True)
    
    class Meta:
        model = OfficeExpense
        fields = [
            'id', 'expense_type', 'expense_type_display', 'amount',
            'expense_date', 'description', 'receipt_image', 'notes',
            'created_at', 'updated_at'
        ]


class BankTransferSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for BankTransfer model"""
    from_bank_name = serializers.CharField(source='from_banking_detail.bank_name', read_only=True)
    to_bank_name = serializers.CharField(source='to_banking_detail.bank_name', read_only=True)
    
    class Meta:
        model = BankTransfer
        fields = [
            'id', 'from_banking_detail', 'from_bank_name',
            'to_banking_detail', 'to_bank_name', 'amount',
            'transfer_date', 'reference_number', 'purpose',
            'charges', 'net_amount', 'status', 'notes',
            'created_at', 'updated_at'
        ]