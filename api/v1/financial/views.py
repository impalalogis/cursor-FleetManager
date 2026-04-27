"""
Financial Views for Fleet Manager API
Comprehensive viewsets matching admin panel functionality
"""

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q, Sum, Count
from datetime import date, timedelta

from financial.models import (
    Invoice, Payment, Transaction, OfficeExpense, BankTransfer
)
from api.utils import IsOwnerOrReadOnly, success_response, error_response
from .serializers import (
    InvoiceSerializer, InvoiceListSerializer, PaymentSerializer,
    TransactionSerializer, OtherExpenseSerializer, BankTransferSerializer
)


class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Invoice model"""
    queryset = Invoice.objects.select_related('shipment', 'consignmentGroup').prefetch_related('payments').all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'shipment', 'consignmentGroup', 'status', 'issue_date',
        'due_date', 'is_paid'
    ]
    search_fields = [
        'invoice_id', 'shipment__shipment_id', 'consignmentGroup__group_id'
    ]
    ordering_fields = ['invoice_id', 'issue_date', 'due_date', 'total_dues']
    ordering = ['-issue_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        return InvoiceSerializer
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue invoices"""
        today = date.today()
        invoices = self.queryset.filter(
            due_date__lt=today,
            payment_status__in=['UNPAID', 'PARTIAL']
        )
        serializer = self.get_serializer(invoices, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def unpaid(self, request):
        """Get unpaid invoices"""
        invoices = self.queryset.filter(payment_status='UNPAID')
        serializer = self.get_serializer(invoices, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def partially_paid(self, request):
        """Get partially paid invoices"""
        invoices = self.queryset.filter(payment_status='PARTIAL')
        serializer = self.get_serializer(invoices, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=True, methods=['get'])
    def payment_history(self, request, pk=None):
        """Get payment history for invoice"""
        invoice = self.get_object()
        payments = invoice.payments.all().order_by('-payment_date')
        serializer = PaymentSerializer(payments, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=True, methods=['post'])
    def calculate_totals(self, request, pk=None):
        """Recalculate invoice totals"""
        invoice = self.get_object()
        
        # This would typically call a method on the model
        # invoice.calculate_totals()
        invoice.save()
        
        serializer = self.get_serializer(invoice)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get invoice summary statistics"""
        queryset = self.get_queryset()
        
        summary = {
            'total_invoices': queryset.count(),
            'total_amount': float(queryset.aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
            'unpaid_count': queryset.filter(payment_status='UNPAID').count(),
            'unpaid_amount': float(queryset.filter(payment_status='UNPAID').aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
            'overdue_count': queryset.filter(due_date__lt=date.today(), payment_status__in=['UNPAID', 'PARTIAL']).count(),
            'paid_count': queryset.filter(payment_status='PAID').count(),
        }
        
        return Response(success_response(summary))


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for Payment model"""
    queryset = Payment.objects.select_related(
        'invoice', 'method', 'from_banking_detail', 'to_banking_detail'
    ).all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'invoice', 'method', 'status', 'payment_date', 'cheque_status',
        'from_banking_detail', 'to_banking_detail'
    ]
    search_fields = [
        'reference_number', 'transaction_reference', 'utr_number',
        'transaction_id', 'cheque_number', 'invoice__invoice_number'
    ]
    ordering_fields = ['payment_date', 'amount_paid']
    ordering = ['-payment_date']
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending payments"""
        payments = self.queryset.filter(status='PENDING')
        serializer = self.get_serializer(payments, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get completed payments"""
        payments = self.queryset.filter(status='COMPLETED')
        serializer = self.get_serializer(payments, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def by_method(self, request):
        """Get payments by method"""
        method = request.query_params.get('method')
        if not method:
            return Response(error_response('Method parameter is required'), status=400)
        
        payments = self.queryset.filter(method_id=method)
        serializer = self.get_serializer(payments, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark payment as completed"""
        payment = self.get_object()
        payment.status = 'COMPLETED'
        payment.save()
        
        # Update invoice payment status if needed
        invoice = payment.invoice
        if invoice:
            total_paid = invoice.payments.filter(status='COMPLETED').aggregate(
                Sum('amount_paid')
            )['amount_paid__sum'] or 0
            
            if total_paid >= invoice.total_amount:
                invoice.payment_status = 'PAID'
            elif total_paid > 0:
                invoice.payment_status = 'PARTIAL'
            else:
                invoice.payment_status = 'UNPAID'
            
            invoice.save()
        
        serializer = self.get_serializer(payment)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get payment summary statistics"""
        queryset = self.get_queryset()
        
        summary = {
            'total_payments': queryset.count(),
            'total_amount': float(queryset.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0),
            'completed_count': queryset.filter(status='COMPLETED').count(),
            'completed_amount': float(queryset.filter(status='COMPLETED').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0),
            'pending_count': queryset.filter(status='PENDING').count(),
            'pending_amount': float(queryset.filter(status='PENDING').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0),
        }
        
        return Response(success_response(summary))


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for Transaction model"""
    queryset = Transaction.objects.select_related('payment', 'payment__invoice').all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'payment', 'transaction_type', 'reconciled', 'transaction_date',
        'reconciliation_date'
    ]
    search_fields = [
        'reference_number', 'payment__invoice__invoice_number',
        'payment__reference_number'
    ]
    ordering_fields = ['transaction_date', 'amount', 'reconciliation_date']
    ordering = ['-transaction_date']
    
    @action(detail=False, methods=['get'])
    def unreconciled(self, request):
        """Get unreconciled transactions"""
        transactions = self.queryset.filter(reconciled=False)
        serializer = self.get_serializer(transactions, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        """Mark transaction as reconciled"""
        transaction = self.get_object()
        transaction.reconciled = True
        transaction.reconciliation_date = date.today()
        transaction.save()
        
        serializer = self.get_serializer(transaction)
        return Response(success_response(serializer.data))


class OtherExpenseViewSet(viewsets.ModelViewSet):
    """ViewSet for OfficeExpense model"""
    queryset = OfficeExpense.objects.select_related('expense_type').all()
    serializer_class = OtherExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['expense_type', 'expense_date']
    search_fields = ['description', 'expense_type__display_name']
    ordering_fields = ['expense_date', 'amount']
    ordering = ['-expense_date']
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get expenses by type"""
        expense_type = request.query_params.get('type')
        if not expense_type:
            return Response(error_response('Type parameter is required'), status=400)
        
        expenses = self.queryset.filter(expense_type_id=expense_type)
        serializer = self.get_serializer(expenses, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get expense summary by type"""
        from django.db.models import Sum
        from collections import defaultdict
        
        expenses = self.get_queryset()
        summary = defaultdict(float)
        
        for expense in expenses.select_related('expense_type'):
            type_name = expense.expense_type.display_name if expense.expense_type else 'Other'
            summary[type_name] += float(expense.amount or 0)
        
        return Response(success_response(dict(summary)))


class BankTransferViewSet(viewsets.ModelViewSet):
    """ViewSet for BankTransfer model"""
    queryset = BankTransfer.objects.select_related(
        'from_banking_detail', 'to_banking_detail'
    ).all()
    serializer_class = BankTransferSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'from_banking_detail', 'to_banking_detail', 'status', 'transfer_date'
    ]
    search_fields = [
        'reference_number', 'purpose', 'from_banking_detail__bank_name',
        'to_banking_detail__bank_name'
    ]
    ordering_fields = ['transfer_date', 'amount']
    ordering = ['-transfer_date']
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending transfers"""
        transfers = self.queryset.filter(status='PENDING')
        serializer = self.get_serializer(transfers, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get completed transfers"""
        transfers = self.queryset.filter(status='COMPLETED')
        serializer = self.get_serializer(transfers, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark transfer as completed"""
        transfer = self.get_object()
        transfer.status = 'COMPLETED'
        transfer.save()
        
        serializer = self.get_serializer(transfer)
        return Response(success_response(serializer.data))