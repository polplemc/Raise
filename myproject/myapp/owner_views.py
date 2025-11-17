from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
import json
from .models import Supplier, Product, Inventory, Order, OrderItem, UserProfile, SupplierProfile, ConnectionRequest, StockOut, ActivityLog, SupplierProduct, SupplierOrder
from .forms import SupplierForm, ProfileForm, AddToCartForm, StockOutForm, PlaceOrderForm, StaffCreateForm, StaffEditForm, StaffPasswordResetForm, UpdatePaymentStatusForm
from .decorators import owner_required, staff_access_check, get_business_owner_for_user
from .notifications import notify_order_placed, notify_payment_status_change


# Note: owner_required decorator is now imported from decorators.py


@owner_required
def owner_dashboard(request):
    """Main dashboard with inventory tracking"""
    # Get inventory stats
    inventory_items = Inventory.objects.filter(owner=request.user).select_related('product')
    total_products = inventory_items.count()
    low_stock_items = inventory_items.filter(quantity__lte=10, quantity__gt=0).count()
    out_of_stock = inventory_items.filter(quantity=0).count()
    in_stock = total_products - low_stock_items - out_of_stock
    
    # Get recent orders from NEW system (SupplierOrder)
    recent_orders = SupplierOrder.objects.filter(
        store_owner=request.user
    ).select_related('supplier_product', 'supplier_product__supplier').order_by('-created_at')[:5]
    
    # Pending orders count from NEW system
    pending_orders = SupplierOrder.objects.filter(store_owner=request.user, status='pending').count()
    
    # Get supplier order stats
    total_supplier_orders = SupplierOrder.objects.filter(store_owner=request.user).count()
    delivered_orders = SupplierOrder.objects.filter(store_owner=request.user, status='delivered').count()
    
    # Get inventory data for chart
    inventory_data = []
    for item in inventory_items[:10]:  # Top 10 items
        inventory_data.append({
            'name': item.product.name[:20],
            'quantity': item.quantity,
            'is_low': item.is_low_stock
        })
    
    context = {
        'total_products': total_products,
        'low_stock_items': low_stock_items,
        'out_of_stock': out_of_stock,
        'in_stock': in_stock,
        'pending_orders': pending_orders,
        'recent_orders': recent_orders,
        'inventory_data': json.dumps(inventory_data),
        'total_supplier_orders': total_supplier_orders,
        'delivered_orders': delivered_orders,
    }
    return render(request, 'owner/dashboard.html', context)


@owner_required
def owner_profile(request):
    """View and edit profile"""
    profile = request.user.profile
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('owner_profile')
    else:
        form = ProfileForm(instance=profile, user=request.user)
    
    # Get stats for profile page - these are already accessible via template but adding for clarity
    context = {
        'form': form,
    }
    
    return render(request, 'owner/profile.html', context)


@owner_required
def inventory_list(request):
    """List all inventory items"""
    inventory_items = Inventory.objects.filter(
        owner=request.user
    ).select_related('product', 'product__supplier').order_by('product__name')
    
    # Filter by search
    search = request.GET.get('search', '')
    if search:
        inventory_items = inventory_items.filter(
            Q(product__name__icontains=search) |
            Q(product__supplier__name__icontains=search)
        )
    
    # Filter by stock status
    status = request.GET.get('status', '')
    if status == 'low':
        inventory_items = inventory_items.filter(quantity__lte=10, quantity__gt=0)
    elif status == 'out':
        inventory_items = inventory_items.filter(quantity=0)
    
    context = {
        'inventory_items': inventory_items,
        'search': search,
        'status': status,
    }
    return render(request, 'owner/inventory_list.html', context)


@owner_required
def inventory_delete(request, pk):
    """Delete an inventory item (only if out of stock)"""
    inventory = get_object_or_404(Inventory, pk=pk, owner=request.user)
    product_name = inventory.product.name
    
    # Only allow deletion if quantity is 0
    if inventory.quantity > 0:
        messages.error(request, f'Cannot delete "{product_name}". Products with stock cannot be deleted. Stock out all items first.')
        return redirect('owner_inventory_list')
    
    if request.method == 'POST':
        # Log the deletion
        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            description=f'Deleted inventory item: {product_name}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        inventory.delete()
        messages.success(request, f'Successfully deleted "{product_name}" from inventory.')
        return redirect('owner_inventory_list')
    
    context = {
        'inventory': inventory,
    }
    return render(request, 'owner/inventory_confirm_delete.html', context)


@owner_required
def supplier_list(request):
    """List all suppliers"""
    suppliers = Supplier.objects.filter(owner=request.user)
    
    # Filter by search
    search = request.GET.get('search', '')
    if search:
        suppliers = suppliers.filter(
            Q(name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(email__icontains=search)
        )
    
    context = {
        'suppliers': suppliers,
        'search': search,
    }
    return render(request, 'owner/supplier_list.html', context)


@owner_required
def supplier_add(request):
    """Add new supplier"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.owner = request.user
            supplier.save()
            messages.success(request, f"Supplier '{supplier.name}' added successfully!")
            return redirect('owner_supplier_list')
    else:
        form = SupplierForm()
    
    return render(request, 'owner/supplier_form.html', {'form': form, 'action': 'Add'})


@owner_required
def supplier_edit(request, pk):
    """Edit supplier"""
    supplier = get_object_or_404(Supplier, pk=pk, owner=request.user)
    
    # Check if this supplier is connected via SupplierProfile (connection request)
    if supplier.supplier_profile:
        messages.warning(request, "You cannot edit suppliers connected through connection requests. Only the supplier can update their information.")
        return redirect('owner_supplier_list')
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supplier '{supplier.name}' updated successfully!")
            return redirect('owner_supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    
    return render(request, 'owner/supplier_form.html', {'form': form, 'action': 'Edit', 'supplier': supplier})


@owner_required
def supplier_delete(request, pk):
    """Delete supplier connection"""
    supplier = get_object_or_404(Supplier, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        name = supplier.name
        supplier.delete()
        if supplier.supplier_profile:
            messages.success(request, f"Connection with '{name}' removed successfully!")
        else:
            messages.success(request, f"Supplier '{name}' deleted successfully!")
        return redirect('owner_supplier_list')
    
    return render(request, 'owner/supplier_confirm_delete.html', {'supplier': supplier})


# OLD PRODUCT/ORDER SYSTEM VIEWS REMOVED
# The system now uses SupplierProduct and SupplierOrder models exclusively
# See browse_supplier_products, supplier_product_detail, owner_supplier_orders below


@owner_required
def search_suppliers(request):
    """Search for suppliers to connect with"""
    search_query = request.GET.get('search', '')
    suppliers = []
    
    if search_query:
        # Search supplier profiles
        suppliers = SupplierProfile.objects.filter(
            Q(business_name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(email__icontains=search_query)
        ).select_related('user')
        
        # Annotate with connection status
        for supplier in suppliers:
            # Check if already connected
            existing_supplier = Supplier.objects.filter(
                owner=request.user,
                supplier_profile=supplier
            ).first()
            supplier.is_connected = existing_supplier is not None
            
            # Check if connection request exists
            connection_request = ConnectionRequest.objects.filter(
                owner=request.user,
                supplier_profile=supplier
            ).first()
            supplier.connection_request = connection_request
    
    context = {
        'suppliers': suppliers,
        'search_query': search_query,
    }
    return render(request, 'owner/search_suppliers.html', context)


@owner_required
def send_connection_request(request, supplier_profile_id):
    """Send connection request to a supplier"""
    supplier_profile = get_object_or_404(SupplierProfile, pk=supplier_profile_id)
    
    # Check if already connected
    if Supplier.objects.filter(owner=request.user, supplier_profile=supplier_profile).exists():
        messages.warning(request, "You are already connected with this supplier.")
        return redirect('owner_search_suppliers')
    
    # Check if request already exists
    existing_request = ConnectionRequest.objects.filter(
        owner=request.user,
        supplier_profile=supplier_profile
    ).first()
    
    if existing_request:
        if existing_request.status == 'pending':
            messages.warning(request, "You have already sent a connection request to this supplier.")
        elif existing_request.status == 'rejected':
            messages.warning(request, "Your previous connection request was rejected.")
        return redirect('owner_search_suppliers')
    
    if request.method == 'POST':
        message = request.POST.get('message', '')
        ConnectionRequest.objects.create(
            owner=request.user,
            supplier_profile=supplier_profile,
            message=message
        )
        messages.success(request, f"Connection request sent to {supplier_profile.business_name}!")
        return redirect('owner_search_suppliers')
    
    context = {
        'supplier_profile': supplier_profile,
    }
    return render(request, 'owner/send_connection_request.html', context)


@owner_required
def view_connection_requests(request):
    """View all connection requests sent by owner"""
    requests = ConnectionRequest.objects.filter(
        owner=request.user
    ).select_related('supplier_profile').order_by('-created_at')
    
    context = {
        'requests': requests,
    }
    return render(request, 'owner/connection_requests.html', context)


# ===== STOCK OUT FUNCTIONALITY =====

@owner_required
def stock_out_form(request):
    """Form to record stock out (sales/usage)"""
    if request.method == 'POST':
        form = StockOutForm(request.POST, owner=request.user)
        if form.is_valid():
            stock_out = form.save(commit=False)
            stock_out.owner = request.user
            stock_out.processed_by = request.user
            
            # Get the inventory item and deduct stock
            try:
                inventory = Inventory.objects.get(
                    owner=request.user, 
                    product=stock_out.product
                )
                
                # Double-check stock availability
                if stock_out.quantity > inventory.quantity:
                    messages.error(request, 
                        f"Cannot process stock out. Only {inventory.quantity} {stock_out.product.unit} available."
                    )
                    return render(request, 'owner/stock_out_form.html', {'form': form})
                
                # Deduct stock
                inventory.quantity -= stock_out.quantity
                inventory.save()
                
                # Save stock out record
                stock_out.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=request.user,
                    action='stock_out',
                    description=f'Stock out: {stock_out.quantity} {stock_out.product.unit} of {stock_out.product.name} ({stock_out.reason})',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, 
                    f'Successfully recorded stock out: {stock_out.quantity} {stock_out.product.unit} of {stock_out.product.name}. '
                    f'Remaining stock: {inventory.quantity} {stock_out.product.unit}'
                )
                return redirect('owner_stock_out_form')
                
            except Inventory.DoesNotExist:
                messages.error(request, f"Product '{stock_out.product.name}' not found in your inventory.")
                return render(request, 'owner/stock_out_form.html', {'form': form})
                
    else:
        form = StockOutForm(owner=request.user)
    
    # Get recent stock out transactions
    recent_stock_outs = StockOut.objects.filter(
        owner=request.user
    ).select_related('product', 'processed_by').order_by('-created_at')[:10]
    
    context = {
        'form': form,
        'recent_stock_outs': recent_stock_outs,
    }
    return render(request, 'owner/stock_out_form.html', context)


@owner_required
def stock_out_report(request):
    """Stock out report with filters"""
    stock_outs = StockOut.objects.filter(owner=request.user).select_related('product', 'processed_by')
    
    # Filter by product
    product_filter = request.GET.get('product')
    if product_filter:
        stock_outs = stock_outs.filter(product_id=product_filter)
    
    # Filter by reason
    reason_filter = request.GET.get('reason')
    if reason_filter:
        stock_outs = stock_outs.filter(reason=reason_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        stock_outs = stock_outs.filter(created_at__date__gte=date_from)
    if date_to:
        stock_outs = stock_outs.filter(created_at__date__lte=date_to)
    
    stock_outs = stock_outs.order_by('-created_at')
    
    # Get filter options
    products = Product.objects.filter(
        id__in=Inventory.objects.filter(owner=request.user).values_list('product', flat=True)
    ).order_by('name')
    
    # Calculate totals
    total_quantity = sum(so.quantity for so in stock_outs)
    total_records = stock_outs.count()
    
    context = {
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
    }
    return render(request, 'owner/stock_out_report.html', context)


# ========== NEW SUPPLIER PRODUCT BROWSING VIEWS ==========

@owner_required
def browse_supplier_products(request):
    """Browse available products from connected suppliers"""
    # Get connected suppliers
    connected_suppliers = Supplier.objects.filter(owner=request.user, is_active=True)
    supplier_profiles = [s.supplier_profile for s in connected_suppliers if s.supplier_profile]
    
    # Get all active products from connected suppliers
    products = SupplierProduct.objects.filter(
        supplier__in=[sp.user for sp in supplier_profiles],
        is_active=True
    ).select_related('supplier')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Filter by supplier
    supplier_filter = request.GET.get('supplier', '')
    if supplier_filter:
        products = products.filter(supplier__id=supplier_filter)
    
    # Get suppliers for filter dropdown
    available_suppliers = [sp.user for sp in supplier_profiles]
    
    context = {
        'products': products,
        'search': search,
        'supplier_filter': supplier_filter,
        'available_suppliers': available_suppliers,
        'connected_suppliers_count': len(supplier_profiles),
    }
    return render(request, 'owner/browse_supplier_products.html', context)


@owner_required
def supplier_product_detail(request, pk):
    """View details of a supplier product and place order"""
    product = get_object_or_404(SupplierProduct, pk=pk, is_active=True)
    
    # Check if this store owner is connected to this supplier
    connected_suppliers = Supplier.objects.filter(
        owner=request.user, 
        supplier_profile__user=product.supplier,
        is_active=True
    )
    
    if not connected_suppliers.exists():
        messages.error(request, "You are not connected to this supplier.")
        return redirect('browse_supplier_products')
    
    if request.method == 'POST':
        form = PlaceOrderForm(request.POST, supplier_product=product)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            payment_method = form.cleaned_data['payment_method']
            payment_status = form.cleaned_data['payment_status']
            
            # Calculate total amount
            total_amount = quantity * product.unit_price
            
            # Create the order
            order = SupplierOrder.objects.create(
                supplier_product=product,
                store_owner=request.user,
                quantity=quantity,
                unit_price=product.unit_price,
                total_amount=total_amount,
                notes=notes,
                payment_method=payment_method,
                payment_status=payment_status,
                status='pending'
            )
            
            # Debug: Print order details
            print(f"DEBUG: Order created - ID: {order.id}, Product: {product.name}, Supplier: {product.supplier.username}, Owner: {request.user.username}, Total: {total_amount}")
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action='order',
                description=f'Placed order for {quantity} {product.unit} of {product.name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Send notification to supplier
            notify_order_placed(order, request.user)
            
            messages.success(request, f'Order placed successfully! Order #{order.id} is now pending approval.')
            return redirect('owner_supplier_orders')
    else:
        form = PlaceOrderForm(supplier_product=product)
    
    # Get recent orders for this product
    recent_orders = SupplierOrder.objects.filter(
        supplier_product=product,
        store_owner=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'product': product,
        'form': form,
        'recent_orders': recent_orders,
    }
    return render(request, 'owner/supplier_product_detail.html', context)


@owner_required
def owner_supplier_orders(request):
    """View all orders placed to suppliers"""
    orders = SupplierOrder.objects.filter(store_owner=request.user).select_related(
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
    total_orders = SupplierOrder.objects.filter(store_owner=request.user).count()
    pending_orders = SupplierOrder.objects.filter(store_owner=request.user, order_status='pending').count()
    completed_orders = SupplierOrder.objects.filter(store_owner=request.user, order_status='completed').count()
    delivered_orders = SupplierOrder.objects.filter(store_owner=request.user, delivery_status='delivered').count()
    total_spent = SupplierOrder.objects.filter(
        store_owner=request.user, 
        order_status='completed',
        delivery_status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    context = {
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
    }
    return render(request, 'owner/supplier_orders.html', context)


@owner_required
def owner_supplier_order_detail(request, pk):
    """View details of a specific supplier order"""
    order = get_object_or_404(SupplierOrder, pk=pk, store_owner=request.user)
    
    context = {'order': order}
    return render(request, 'owner/supplier_order_detail.html', context)


# ========== STAFF MANAGEMENT VIEWS ==========

@owner_required
def staff_list(request):
    """List all staff members under this owner"""
    staff_members = UserProfile.objects.filter(
        role='staff',
        owner=request.user
    ).select_related('user').order_by('-created_at')
    
    # Get stats
    total_staff = staff_members.count()
    active_staff = staff_members.filter(is_active=True).count()
    inactive_staff = total_staff - active_staff
    
    context = {
        'staff_members': staff_members,
        'total_staff': total_staff,
        'active_staff': active_staff,
        'inactive_staff': inactive_staff,
    }
    return render(request, 'owner/staff_list.html', context)


@owner_required
def staff_add(request):
    """Add a new staff member"""
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            try:
                staff_profile = form.save(owner=request.user)
                
                # Log activity
                ActivityLog.objects.create(
                    user=request.user,
                    action='create',
                    description=f'Added new staff member: {staff_profile.user.username}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Staff member {staff_profile.user.username} has been created successfully!')
                return redirect('owner_staff_list')
            except Exception as e:
                messages.error(request, f'Error creating staff member: {str(e)}')
    else:
        form = StaffCreateForm()
    
    context = {'form': form}
    return render(request, 'owner/staff_form.html', context)


@owner_required
def staff_edit(request, staff_id):
    """Edit an existing staff member"""
    staff_profile = get_object_or_404(
        UserProfile, 
        id=staff_id, 
        role='staff', 
        owner=request.user
    )
    
    if request.method == 'POST':
        form = StaffEditForm(request.POST, instance=staff_profile)
        if form.is_valid():
            form.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action='update',
                description=f'Updated staff member: {staff_profile.user.username}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Staff member {staff_profile.user.username} has been updated successfully!')
            return redirect('owner_staff_list')
    else:
        form = StaffEditForm(instance=staff_profile)
    
    context = {
        'form': form,
        'staff_profile': staff_profile,
        'is_edit': True,
    }
    return render(request, 'owner/staff_form.html', context)


@owner_required
def staff_toggle_active(request, staff_id):
    """Toggle staff member active status"""
    staff_profile = get_object_or_404(
        UserProfile, 
        id=staff_id, 
        role='staff', 
        owner=request.user
    )
    
    # Toggle active status
    staff_profile.is_active = not staff_profile.is_active
    staff_profile.save()
    
    status = "activated" if staff_profile.is_active else "deactivated"
    
    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        action='update',
        description=f'Staff member {staff_profile.user.username} {status}',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    messages.success(request, f'Staff member {staff_profile.user.username} has been {status}!')
    return redirect('owner_staff_list')


@owner_required
def staff_reset_password(request, staff_id):
    """Reset staff member password"""
    staff_profile = get_object_or_404(
        UserProfile, 
        id=staff_id, 
        role='staff', 
        owner=request.user
    )
    
    if request.method == 'POST':
        form = StaffPasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            staff_profile.user.set_password(new_password)
            staff_profile.user.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action='update',
                description=f'Reset password for staff member: {staff_profile.user.username}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Password for {staff_profile.user.username} has been reset successfully!')
            return redirect('owner_staff_list')
    else:
        form = StaffPasswordResetForm()
    
    context = {
        'form': form,
        'staff_profile': staff_profile,
    }
    return render(request, 'owner/staff_password_reset.html', context)


@owner_required
def staff_delete(request, staff_id):
    """Delete a staff member (confirmation required)"""
    staff_profile = get_object_or_404(
        UserProfile, 
        id=staff_id, 
        role='staff', 
        owner=request.user
    )
    
    if request.method == 'POST':
        username = staff_profile.user.username
        
        # Log activity before deletion
        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            description=f'Deleted staff member: {username}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Delete the user (this will cascade to UserProfile)
        staff_profile.user.delete()
        
        messages.success(request, f'Staff member {username} has been deleted successfully!')
        return redirect('owner_staff_list')
    
    context = {'staff_profile': staff_profile}
    return render(request, 'owner/staff_confirm_delete.html', context)


# ========== PAYMENT VERIFICATION VIEWS ==========

@owner_required
def update_payment_status(request, order_id):
    """Owner updates payment status for their order"""
    order = get_object_or_404(SupplierOrder, pk=order_id, store_owner=request.user)
    
    if request.method == 'POST':
        form = UpdatePaymentStatusForm(request.POST, instance=order)
        if form.is_valid():
            old_status = order.payment_status
            form.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action='update',
                description=f'Updated payment status for Order #{order.id} from {old_status} to {order.payment_status}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Payment status updated to {order.get_payment_status_display()}!')
            return redirect('owner_supplier_order_detail', pk=order_id)
    else:
        form = UpdatePaymentStatusForm(instance=order)
    
    context = {
        'order': order,
        'form': form,
    }
    return render(request, 'owner/update_payment_status.html', context)


@owner_required
def owner_payment_verification_report(request):
    """View payment verification status for owner's orders"""
    # Get all orders by this owner
    orders = SupplierOrder.objects.filter(
        store_owner=request.user
    ).select_related('supplier_product', 'supplier_product__supplier')
    
    # Filter options
    verification_filter = request.GET.get('verification', '')
    payment_status_filter = request.GET.get('payment_status', '')
    
    if verification_filter == 'verified':
        orders = orders.filter(payment_verified=True)
    elif verification_filter == 'unverified':
        orders = orders.filter(payment_verified=False, payment_status='paid')
    
    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)
    
    # Statistics
    total_orders = SupplierOrder.objects.filter(store_owner=request.user).count()
    
    paid_orders = SupplierOrder.objects.filter(
        store_owner=request.user,
        payment_status='paid'
    ).count()
    
    verified_payments = SupplierOrder.objects.filter(
        store_owner=request.user,
        payment_verified=True
    ).count()
    
    pending_verification = SupplierOrder.objects.filter(
        store_owner=request.user,
        payment_status='paid',
        payment_verified=False
    ).count()
    
    total_paid_amount = SupplierOrder.objects.filter(
        store_owner=request.user,
        payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    total_verified_amount = SupplierOrder.objects.filter(
        store_owner=request.user,
        payment_verified=True
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'paid_orders': paid_orders,
        'verified_payments': verified_payments,
        'pending_verification': pending_verification,
        'total_paid_amount': total_paid_amount,
        'total_verified_amount': total_verified_amount,
        'verification_filter': verification_filter,
        'payment_status_filter': payment_status_filter,
    }
    return render(request, 'owner/payment_verification_report.html', context)
