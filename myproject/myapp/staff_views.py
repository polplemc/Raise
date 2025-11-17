from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from .models import Supplier, Product, Inventory, Order, OrderItem, UserProfile, StockOut, ActivityLog, SupplierProduct, SupplierOrder
from .forms import AddToCartForm, StockOutForm
from .decorators import staff_required, owner_or_staff_required, get_business_owner_for_user


@staff_required
def staff_dashboard(request):
    """Staff dashboard with limited access to owner's data"""
    # Get the business owner this staff works for
    business_owner = request.user.profile.owner
    
    if not business_owner:
        messages.error(request, "No business owner assigned to your account.")
        return redirect('landing')
    
    # Get inventory stats for the business owner
    inventory_items = Inventory.objects.filter(owner=business_owner).select_related('product')
    total_products = inventory_items.count()
    low_stock_items = inventory_items.filter(quantity__lte=10).count()
    out_of_stock = inventory_items.filter(quantity=0).count()
    
    # Get recent orders for the business owner from NEW system (SupplierOrder)
    recent_orders = SupplierOrder.objects.filter(
        store_owner=business_owner
    ).select_related('supplier_product', 'supplier_product__supplier').order_by('-created_at')[:5]
    
    # Pending orders count from NEW system
    pending_orders = SupplierOrder.objects.filter(store_owner=business_owner, order_status='pending').count()
    
    # Get recent stock out records
    recent_stock_outs = StockOut.objects.filter(
        owner=business_owner
    ).order_by('-created_at')[:5]
    
    # Get inventory data for chart (top 10 items)
    inventory_data = []
    for item in inventory_items[:10]:
        inventory_data.append({
            'name': item.product.name[:20],
            'quantity': item.quantity,
            'is_low': item.is_low_stock
        })
    
    # Get stock out reasons data for chart
    stock_out_reasons = StockOut.objects.filter(
        owner=business_owner
    ).values('reason').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Prepare stock out reasons data for chart
    stock_out_reasons_data = {
        'labels': [],
        'counts': []
    }
    
    reason_labels = {
        'sale': 'Sale',
        'damage': 'Damage',
        'expired': 'Expired',
        'lost': 'Lost',
        'return': 'Return',
        'other': 'Other'
    }
    
    for item in stock_out_reasons:
        stock_out_reasons_data['labels'].append(reason_labels.get(item['reason'], item['reason']))
        stock_out_reasons_data['counts'].append(item['count'])
    
    context = {
        'business_owner': business_owner,
        'total_products': total_products,
        'low_stock_items': low_stock_items,
        'out_of_stock': out_of_stock,
        'recent_orders': recent_orders,
        'pending_orders': pending_orders,
        'recent_stock_outs': recent_stock_outs,
        'inventory_data': inventory_data,
        'stock_out_reasons_data': stock_out_reasons_data,
    }
    return render(request, 'staff/dashboard.html', context)


@owner_or_staff_required
def staff_inventory_list(request):
    """View inventory for the business owner (accessible by owner and staff)"""
    business_owner = get_business_owner_for_user(request.user)
    
    if not business_owner:
        messages.error(request, "Unable to determine business owner.")
        return redirect('landing')
    
    # Get inventory items for the business owner
    inventory_items = Inventory.objects.filter(owner=business_owner).select_related('product')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        inventory_items = inventory_items.filter(
            Q(product__name__icontains=search) |
            Q(product__description__icontains=search)
        )
    
    # Filter by stock level
    stock_filter = request.GET.get('stock', '')
    if stock_filter == 'low':
        inventory_items = inventory_items.filter(quantity__lte=10, quantity__gt=0)
    elif stock_filter == 'out':
        inventory_items = inventory_items.filter(quantity=0)
    elif stock_filter == 'available':
        inventory_items = inventory_items.filter(quantity__gt=10)
    
    # Calculate stats
    total_items = inventory_items.count()
    low_stock_count = inventory_items.filter(quantity__lte=10, quantity__gt=0).count()
    out_of_stock_count = inventory_items.filter(quantity=0).count()
    
    context = {
        'business_owner': business_owner,
        'inventory_items': inventory_items,
        'search': search,
        'stock_filter': stock_filter,
        'total_items': total_items,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'is_staff': request.user.profile.role == 'staff',
    }
    return render(request, 'staff/inventory_list.html', context)


@owner_or_staff_required
def staff_stock_out_form(request):
    """Record stock out transactions (accessible by owner and staff)"""
    business_owner = get_business_owner_for_user(request.user)
    
    if not business_owner:
        messages.error(request, "Unable to determine business owner.")
        return redirect('landing')
    
    if request.method == 'POST':
        form = StockOutForm(request.POST, owner=business_owner)
        if form.is_valid():
            stock_out = form.save(commit=False)
            stock_out.owner = business_owner
            stock_out.processed_by = request.user  # Track who recorded it
            
            # Get the inventory item and deduct stock
            try:
                inventory = Inventory.objects.get(
                    owner=business_owner, 
                    product=stock_out.product
                )
                
                # Double-check stock availability
                if stock_out.quantity > inventory.quantity:
                    messages.error(request, 
                        f"Cannot process stock out. Only {inventory.quantity} {stock_out.product.unit} available."
                    )
                    return render(request, 'staff/stock_out_form.html', {
                        'form': form, 
                        'business_owner': business_owner,
                        'is_staff': request.user.profile.role == 'staff'
                    })
                
                # Deduct stock
                inventory.quantity -= stock_out.quantity
                inventory.save()
                
                # Save stock out record
                stock_out.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=request.user,
                    action='stock_out',
                    description=f'Recorded stock out: {stock_out.quantity} {stock_out.product.unit} of {stock_out.product.name} ({stock_out.reason})',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, 
                    f'Successfully recorded stock out: {stock_out.quantity} {stock_out.product.unit} of {stock_out.product.name}. '
                    f'Remaining stock: {inventory.quantity} {stock_out.product.unit}'
                )
                return redirect('staff_inventory_list')
                
            except Inventory.DoesNotExist:
                messages.error(request, f"Product '{stock_out.product.name}' not found in inventory.")
                return render(request, 'staff/stock_out_form.html', {
                    'form': form, 
                    'business_owner': business_owner,
                    'is_staff': request.user.profile.role == 'staff'
                })
    else:
        form = StockOutForm(owner=business_owner)
    
    context = {
        'form': form,
        'business_owner': business_owner,
        'is_staff': request.user.profile.role == 'staff',
    }
    return render(request, 'staff/stock_out_form.html', context)


@owner_or_staff_required
def staff_stock_out_report(request):
    """View stock out reports (accessible by owner and staff)"""
    business_owner = get_business_owner_for_user(request.user)
    
    if not business_owner:
        messages.error(request, "Unable to determine business owner.")
        return redirect('landing')
    
    # Get all stock outs for the business owner
    stock_outs = StockOut.objects.filter(owner=business_owner).select_related(
        'product', 'processed_by'
    ).order_by('-created_at')
    
    # Filter by product
    product_filter = request.GET.get('product', '')
    if product_filter:
        stock_outs = stock_outs.filter(product__id=product_filter)
    
    # Filter by reason
    reason_filter = request.GET.get('reason', '')
    if reason_filter:
        stock_outs = stock_outs.filter(reason=reason_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        stock_outs = stock_outs.filter(created_at__date__gte=date_from)
    if date_to:
        stock_outs = stock_outs.filter(created_at__date__lte=date_to)
    
    # Get products for filter dropdown
    products = Product.objects.filter(
        inventory__owner=business_owner
    ).distinct().order_by('name')
    
    # Calculate totals
    total_quantity = sum(so.quantity for so in stock_outs)
    total_records = stock_outs.count()
    
    context = {
        'business_owner': business_owner,
        'stock_outs': stock_outs,
        'products': products,
        'reason_choices': StockOut.REASON_CHOICES,
        'filters': {
            'product': product_filter,
            'reason': reason_filter,
            'date_from': date_from,
            'date_to': date_to,
        },
        'total_quantity': total_quantity,
        'total_records': total_records,
        'is_staff': request.user.profile.role == 'staff',
    }
    return render(request, 'staff/stock_out_report.html', context)


@owner_or_staff_required
def staff_supplier_orders(request):
    """View supplier orders for the business owner (accessible by owner and staff)"""
    business_owner = get_business_owner_for_user(request.user)
    
    if not business_owner:
        messages.error(request, "Unable to determine business owner.")
        return redirect('landing')
    
    # Get supplier orders for the business owner
    orders = SupplierOrder.objects.filter(store_owner=business_owner).select_related(
        'supplier_product', 'supplier_product__supplier'
    ).order_by('-created_at')
    
    # Filter by order status
    order_status_filter = request.GET.get('order_status', '')
    if order_status_filter:
        orders = orders.filter(order_status=order_status_filter)
    
    # Filter by delivery status
    delivery_status_filter = request.GET.get('delivery_status', '')
    if delivery_status_filter:
        orders = orders.filter(delivery_status=delivery_status_filter)
    
    # Search by product name or supplier
    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(supplier_product__name__icontains=search) |
            Q(supplier_product__supplier__first_name__icontains=search) |
            Q(supplier_product__supplier__username__icontains=search)
        )
    
    # Calculate summary stats
    total_orders = SupplierOrder.objects.filter(store_owner=business_owner).count()
    pending_orders = SupplierOrder.objects.filter(store_owner=business_owner, order_status='pending').count()
    completed_orders = SupplierOrder.objects.filter(store_owner=business_owner, order_status='completed').count()
    delivered_orders = SupplierOrder.objects.filter(store_owner=business_owner, delivery_status='delivered').count()
    
    # Total spent - only count completed AND delivered orders
    total_spent = SupplierOrder.objects.filter(
        store_owner=business_owner, 
        order_status='completed',
        delivery_status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    context = {
        'business_owner': business_owner,
        'orders': orders,
        'order_status_filter': order_status_filter,
        'delivery_status_filter': delivery_status_filter,
        'search': search,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'delivered_orders': delivered_orders,
        'total_spent': total_spent,
        'order_status_choices': SupplierOrder.ORDER_STATUS_CHOICES,
        'delivery_status_choices': SupplierOrder.DELIVERY_STATUS_CHOICES,
        'is_staff': request.user.profile.role == 'staff',
    }
    return render(request, 'staff/supplier_orders.html', context)


@owner_or_staff_required
def staff_supplier_order_detail(request, pk):
    """View details of a specific supplier order (accessible by owner and staff)"""
    business_owner = get_business_owner_for_user(request.user)
    
    if not business_owner:
        messages.error(request, "Unable to determine business owner.")
        return redirect('landing')
    
    order = get_object_or_404(SupplierOrder, pk=pk, store_owner=business_owner)
    
    context = {
        'business_owner': business_owner,
        'order': order,
        'is_staff': request.user.profile.role == 'staff',
    }
    return render(request, 'staff/supplier_order_detail.html', context)


@staff_required
def staff_profile(request):
    """Staff profile view"""
    context = {
        'staff_profile': request.user.profile,
        'business_owner': request.user.profile.owner,
    }
    return render(request, 'staff/profile.html', context)
