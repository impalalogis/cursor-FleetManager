"""
Financial API serializers.
"""

from rest_framework import serializers

from financial.models import BankTransfer, Invoice, OfficeExpense, Payment, Transaction


class InvoiceSerializer(serializers.ModelSerializer):
    shipment_id = serializers.CharField(source="shipment.shipment_id", read_only=True)
    consignment_group_id = serializers.CharField(source="consignmentGroup.group_id", read_only=True)
    total_paid = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_id",
            "invoice_ref",
            "bill_to",
            "shipment",
            "shipment_id",
            "consignmentGroup",
            "consignment_group_id",
            "issue_date",
            "due_date",
            "detention_amount",
            "total_freight",
            "total_expense",
            "total_advance",
            "balance_amount",
            "payment_received",
            "total_dues",
            "total_paid",
            "balance_due",
            "status",
            "is_paid",
            "notes",
            "created_by",
            "updated_by",
        ]
        read_only_fields = [
            "invoice_id",
            "issue_date",
            "total_freight",
            "total_expense",
            "total_advance",
            "balance_amount",
            "payment_received",
            "total_dues",
            "created_by",
            "updated_by",
        ]

    def get_total_paid(self, obj):
        payments = obj.payments.filter(status="COMPLETED")
        return float(sum(payment.amount_paid for payment in payments))

    def get_balance_due(self, obj):
        return float((obj.total_dues or 0) - self.get_total_paid(obj))


class PaymentSerializer(serializers.ModelSerializer):
    invoice_id = serializers.CharField(source="invoice.invoice_id", read_only=True)
    method_display = serializers.CharField(source="method.display_value", read_only=True)
    from_bank_name = serializers.CharField(source="from_banking_detail.bank_name", read_only=True)
    to_bank_name = serializers.CharField(source="to_banking_detail.bank_name", read_only=True)
    net_amount = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "invoice_id",
            "payment_date",
            "amount_paid",
            "method",
            "method_display",
            "payment_method",
            "reference_number",
            "transaction_reference",
            "utr_number",
            "transaction_id",
            "cheque_number",
            "cheque_date",
            "cheque_status",
            "from_banking_detail",
            "from_bank_name",
            "to_banking_detail",
            "to_bank_name",
            "status",
            "bank_charges",
            "exchange_rate",
            "net_amount",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_net_amount(self, obj):
        return float(obj.get_net_amount())


class TransactionSerializer(serializers.ModelSerializer):
    source_model = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_id",
            "transaction_date",
            "amount",
            "transaction_type",
            "category",
            "reference_number",
            "description",
            "shipment",
            "driver",
            "vehicle",
            "related_shipment_expense",
            "related_driver_advance",
            "related_maintenance_record",
            "related_tyre",
            "related_tyre_transaction",
            "related_other_expense",
            "related_payment",
            "created_by",
            "created_at",
            "updated_at",
            "source_model",
        ]
        read_only_fields = ["transaction_id"]

    def get_source_model(self, obj):
        return obj.get_source_model()


class OtherExpenseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="category.display_value", read_only=True)

    class Meta:
        model = OfficeExpense
        fields = [
            "id",
            "category",
            "category_display",
            "amount",
            "expense_date",
            "description",
            "paid_by",
            "driver",
            "invoice_document",
        ]


class BankTransferSerializer(serializers.ModelSerializer):
    from_bank_name = serializers.CharField(source="from_banking_detail.bank_name", read_only=True)
    to_bank_name = serializers.CharField(source="to_banking_detail.bank_name", read_only=True)

    class Meta:
        model = BankTransfer
        fields = [
            "id",
            "transfer_type",
            "from_banking_detail",
            "from_bank_name",
            "to_banking_detail",
            "to_bank_name",
            "amount",
            "bank_charges",
            "net_amount",
            "transfer_mode",
            "status",
            "transaction_id",
            "utr_number",
            "reference_number",
            "initiated_datetime",
            "processed_datetime",
            "completed_datetime",
            "beneficiary_name",
            "beneficiary_account_number",
            "beneficiary_ifsc",
            "purpose_code",
            "description",
            "notes",
            "related_shipment",
            "related_driver",
            "related_invoice",
            "related_payment",
        ]
        read_only_fields = ["transaction_id", "initiated_datetime"]
