"""
Maintenance Views for Fleet Manager API
"""

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date, timedelta

from maintenance.models import MaintenanceRecord, TyreTransaction, Tyre
from api.utils import success_response, error_response
from .serializers import (
    MaintenanceRecordSerializer, TyreTransactionSerializer, TyreSerializer
)


class MaintenanceRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for MaintenanceRecord model"""
    queryset = MaintenanceRecord.objects.select_related('vehicle', 'maintenance_type').all()
    serializer_class = MaintenanceRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['vehicle', 'maintenance_type', 'maintenance_date']
    search_fields = [
        'vehicle__registration_number', 'description', 'service_provider',
        'invoice_number'
    ]
    ordering_fields = ['maintenance_date', 'cost', 'odometer_reading']
    ordering = ['-maintenance_date']
    
    @action(detail=False, methods=['get'])
    def due_soon(self, request):
        """Get maintenance records due soon"""
        days_ahead = int(request.query_params.get('days', 30))
        due_date = date.today() + timedelta(days=days_ahead)
        
        records = self.queryset.filter(
            next_service_date__lte=due_date,
            next_service_date__gte=date.today()
        )
        serializer = self.get_serializer(records, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue maintenance records"""
        records = self.queryset.filter(next_service_date__lt=date.today())
        serializer = self.get_serializer(records, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def by_vehicle(self, request):
        """Get maintenance records by vehicle"""
        vehicle_id = request.query_params.get('vehicle_id')
        if not vehicle_id:
            return Response(error_response('Vehicle ID is required'), status=400)
        
        records = self.queryset.filter(vehicle_id=vehicle_id)
        serializer = self.get_serializer(records, many=True)
        return Response(success_response(serializer.data))


class TyreViewSet(viewsets.ModelViewSet):
    """ViewSet for Tyre model"""
    queryset = Tyre.objects.select_related('vehicle', 'tyre_size', 'tyre_brand').all()
    serializer_class = TyreSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['vehicle', 'position', 'tyre_size', 'tyre_brand', 'current_condition']
    search_fields = ['vehicle__registration_number', 'position']
    ordering_fields = ['purchase_date', 'installation_date', 'purchase_price']
    ordering = ['-installation_date']
    
    @action(detail=False, methods=['get'])
    def by_vehicle(self, request):
        """Get tyres by vehicle"""
        vehicle_id = request.query_params.get('vehicle_id')
        if not vehicle_id:
            return Response(error_response('Vehicle ID is required'), status=400)
        
        tyres = self.queryset.filter(vehicle_id=vehicle_id)
        serializer = self.get_serializer(tyres, many=True)
        return Response(success_response(serializer.data))
    
    @action(detail=False, methods=['get'])
    def needs_replacement(self, request):
        """Get tyres that need replacement"""
        tyres = self.queryset.filter(current_condition__in=['WORN', 'DAMAGED'])
        serializer = self.get_serializer(tyres, many=True)
        return Response(success_response(serializer.data))


class TyreTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for TyreTransaction model"""
    queryset = TyreTransaction.objects.select_related(
        'tyre', 'tyre__vehicle', 'transaction_type'
    ).all()
    serializer_class = TyreTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tyre', 'transaction_type', 'transaction_date']
    search_fields = [
        'tyre__vehicle__registration_number', 'description',
        'service_provider', 'invoice_number'
    ]
    ordering_fields = ['transaction_date', 'cost', 'odometer_reading']
    ordering = ['-transaction_date']
    
    @action(detail=False, methods=['get'])
    def by_tyre(self, request):
        """Get transactions by tyre"""
        tyre_id = request.query_params.get('tyre_id')
        if not tyre_id:
            return Response(error_response('Tyre ID is required'), status=400)
        
        transactions = self.queryset.filter(tyre_id=tyre_id)
        serializer = self.get_serializer(transactions, many=True)
        return Response(success_response(serializer.data))