"""
Analytics Utilities for Dashboard Charts
Provides data aggregation functions for Chart.js visualizations
"""
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth
from datetime import datetime, timedelta
from django.utils import timezone
from collections import defaultdict
import json


def get_sales_trend_data(owner, days=30):
    """
    Get daily sales data for the last N days
    Returns data formatted for Chart.js line chart
    """
    from myapp.models import StockOut
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Get daily sales
    sales = StockOut.objects.filter(
        inventory__owner=owner,
        created_at__gte=start_date,
        reason='sale'
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total_sales=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('date')
    
    # Create complete date range
    date_labels = []
    sales_data = []
    quantity_data = []
    
    sales_dict = {item['date']: item for item in sales}
    
    current_date = start_date.date()
    while current_date <= end_date.date():
        date_labels.append(current_date.strftime('%b %d'))
        
        if current_date in sales_dict:
            sales_data.append(sales_dict[current_date]['total_sales'])
            quantity_data.append(float(sales_dict[current_date]['total_quantity'] or 0))
        else:
            sales_data.append(0)
            quantity_data.append(0)
        
        current_date += timedelta(days=1)
    
    return {
        'labels': date_labels,
        'datasets': [
            {
                'label': 'Number of Sales',
                'data': sales_data,
                'borderColor': '#ffbf31',
                'backgroundColor': 'rgba(255, 191, 49, 0.1)',
                'tension': 0.4
            }
        ]
    }


def get_inventory_status_data(owner):
    """
    Get inventory status distribution
    Returns data formatted for Chart.js doughnut chart
    """
    from myapp.models import Inventory
    
    inventory = Inventory.objects.filter(owner=owner)
    
    in_stock = inventory.filter(quantity__gt=F('low_stock_threshold')).count()
    low_stock = inventory.filter(
        quantity__lte=F('low_stock_threshold'),
        quantity__gt=0
    ).count()
    out_of_stock = inventory.filter(quantity=0).count()
    
    return {
        'labels': ['In Stock', 'Low Stock', 'Out of Stock'],
        'datasets': [{
            'data': [in_stock, low_stock, out_of_stock],
            'backgroundColor': [
                '#28a745',  # Green
                '#ffc107',  # Yellow
                '#dc3545'   # Red
            ],
            'borderWidth': 2,
            'borderColor': '#fff'
        }]
    }


def get_order_status_data(owner):
    """
    Get order status distribution
    Returns data formatted for Chart.js pie chart
    """
    from myapp.models import SupplierOrder
    
    orders = SupplierOrder.objects.filter(owner=owner)
    
    status_counts = orders.values('order_status').annotate(
        count=Count('id')
    )
    
    status_labels = {
        'pending': 'Pending',
        'confirmed': 'Confirmed',
        'processing': 'Processing',
        'completed': 'Completed',
        'cancelled': 'Cancelled'
    }
    
    labels = []
    data = []
    colors = {
        'pending': '#ffc107',
        'confirmed': '#17a2b8',
        'processing': '#007bff',
        'completed': '#28a745',
        'cancelled': '#dc3545'
    }
    
    for status in status_counts:
        status_key = status['order_status']
        labels.append(status_labels.get(status_key, status_key))
        data.append(status['count'])
    
    background_colors = [colors.get(s['order_status'], '#6c757d') for s in status_counts]
    
    return {
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': background_colors,
            'borderWidth': 2,
            'borderColor': '#fff'
        }]
    }


def get_top_products_data(owner, limit=10):
    """
    Get top selling products
    Returns data formatted for Chart.js bar chart
    """
    from myapp.models import StockOut
    
    top_products = StockOut.objects.filter(
        inventory__owner=owner,
        reason='sale'
    ).values(
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Count('id')
    ).order_by('-total_quantity')[:limit]
    
    labels = [item['product__name'] for item in top_products]
    data = [float(item['total_quantity']) for item in top_products]
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Total Quantity Sold',
            'data': data,
            'backgroundColor': '#ffbf31',
            'borderColor': '#ff9800',
            'borderWidth': 1
        }]
    }


def get_monthly_revenue_data(owner, months=6):
    """
    Get monthly revenue trend
    Returns data formatted for Chart.js line chart
    """
    from myapp.models import StockOut
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=months * 30)
    
    # Note: This assumes you have a price field or can calculate revenue
    # Adjust based on your actual model structure
    monthly_data = StockOut.objects.filter(
        inventory__owner=owner,
        created_at__gte=start_date,
        reason='sale'
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total_sales=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('month')
    
    labels = [item['month'].strftime('%B %Y') for item in monthly_data]
    sales_count = [item['total_sales'] for item in monthly_data]
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Monthly Sales',
            'data': sales_count,
            'borderColor': '#28a745',
            'backgroundColor': 'rgba(40, 167, 69, 0.1)',
            'tension': 0.4,
            'fill': True
        }]
    }


def get_supplier_performance_data(owner):
    """
    Get supplier performance metrics
    Returns data formatted for Chart.js bar chart
    """
    from myapp.models import SupplierOrder
    
    supplier_data = SupplierOrder.objects.filter(
        owner=owner
    ).values(
        'supplier_product__supplier__first_name'
    ).annotate(
        total_orders=Count('id'),
        completed_orders=Count('id', filter=Q(order_status='completed')),
        pending_orders=Count('id', filter=Q(order_status='pending'))
    ).order_by('-total_orders')[:10]
    
    labels = [item['supplier_product__supplier__first_name'] for item in supplier_data]
    total = [item['total_orders'] for item in supplier_data]
    completed = [item['completed_orders'] for item in supplier_data]
    pending = [item['pending_orders'] for item in supplier_data]
    
    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Total Orders',
                'data': total,
                'backgroundColor': '#007bff'
            },
            {
                'label': 'Completed',
                'data': completed,
                'backgroundColor': '#28a745'
            },
            {
                'label': 'Pending',
                'data': pending,
                'backgroundColor': '#ffc107'
            }
        ]
    }


def get_payment_status_data(owner):
    """
    Get payment status distribution
    Returns data formatted for Chart.js doughnut chart
    """
    from myapp.models import SupplierOrder
    
    orders = SupplierOrder.objects.filter(owner=owner)
    
    pending = orders.filter(payment_status='pending').count()
    paid = orders.filter(payment_status='paid').count()
    verified = orders.filter(payment_verified=True).count()
    
    return {
        'labels': ['Pending Payment', 'Paid (Unverified)', 'Verified'],
        'datasets': [{
            'data': [pending, paid - verified, verified],
            'backgroundColor': [
                '#ffc107',  # Yellow
                '#17a2b8',  # Cyan
                '#28a745'   # Green
            ],
            'borderWidth': 2,
            'borderColor': '#fff'
        }]
    }


def get_stock_movement_data(owner, days=30):
    """
    Get stock movement trends (in vs out)
    Returns data formatted for Chart.js line chart
    """
    from myapp.models import StockMovement
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    movements = StockMovement.objects.filter(
        supplier_product__supplier=owner,
        created_at__gte=start_date
    ).annotate(
        date=TruncDate('created_at')
    ).values('date', 'movement_type').annotate(
        total_quantity=Sum('quantity')
    ).order_by('date')
    
    # Organize data by date and type
    date_labels = []
    stock_in = []
    stock_out = []
    
    movements_dict = defaultdict(lambda: {'in': 0, 'out': 0, 'adjustment': 0})
    
    for movement in movements:
        date = movement['date']
        movement_type = movement['movement_type']
        quantity = float(movement['total_quantity'] or 0)
        movements_dict[date][movement_type] = quantity
    
    current_date = start_date.date()
    while current_date <= end_date.date():
        date_labels.append(current_date.strftime('%b %d'))
        stock_in.append(movements_dict[current_date]['in'])
        stock_out.append(movements_dict[current_date]['out'])
        current_date += timedelta(days=1)
    
    return {
        'labels': date_labels,
        'datasets': [
            {
                'label': 'Stock In',
                'data': stock_in,
                'borderColor': '#28a745',
                'backgroundColor': 'rgba(40, 167, 69, 0.1)',
                'tension': 0.4
            },
            {
                'label': 'Stock Out',
                'data': stock_out,
                'borderColor': '#dc3545',
                'backgroundColor': 'rgba(220, 53, 69, 0.1)',
                'tension': 0.4
            }
        ]
    }


# Supplier-specific analytics

def get_supplier_sales_data(supplier, days=30):
    """Get supplier's sales trend"""
    from myapp.models import SupplierOrder
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    sales = SupplierOrder.objects.filter(
        supplier_product__supplier=supplier,
        created_at__gte=start_date
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total_orders=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('date')
    
    date_labels = []
    orders_data = []
    
    sales_dict = {item['date']: item for item in sales}
    
    current_date = start_date.date()
    while current_date <= end_date.date():
        date_labels.append(current_date.strftime('%b %d'))
        
        if current_date in sales_dict:
            orders_data.append(sales_dict[current_date]['total_orders'])
        else:
            orders_data.append(0)
        
        current_date += timedelta(days=1)
    
    return {
        'labels': date_labels,
        'datasets': [{
            'label': 'Orders Received',
            'data': orders_data,
            'borderColor': '#28a745',
            'backgroundColor': 'rgba(40, 167, 69, 0.1)',
            'tension': 0.4
        }]
    }


def get_supplier_product_performance(supplier, limit=10):
    """Get supplier's top performing products"""
    from myapp.models import SupplierOrder
    
    top_products = SupplierOrder.objects.filter(
        supplier_product__supplier=supplier
    ).values(
        'supplier_product__name'
    ).annotate(
        total_orders=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('-total_orders')[:limit]
    
    labels = [item['supplier_product__name'] for item in top_products]
    data = [item['total_orders'] for item in top_products]
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Total Orders',
            'data': data,
            'backgroundColor': '#28a745',
            'borderColor': '#1e7e34',
            'borderWidth': 1
        }]
    }
