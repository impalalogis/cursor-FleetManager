"""
Financial API serializers.
"""

from rest_framework import serializers

from financial.models import BankTransfer, Invoice, OfficeExpense, Payment, Transaction


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"


class OtherExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficeExpense
        fields = "__all__"


class BankTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankTransfer
        fields = "__all__"

