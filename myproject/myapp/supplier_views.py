from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
import json
from .models import Supplier, Product, Inventory, Order, OrderItem, UserProfile, SupplierProfile, ConnectionRequest, SupplierProduct, SupplierOrder, StockMovement, ActivityLog, SupplierPaymentInfo
from .forms import ProfileForm, SupplierProductForm, RestockForm, OrderStatusUpdateForm, VerifyPaymentForm, SupplierPaymentInfoForm, CombinedStatusUpdateForm
from .decorators import supplier_required
from .notifications import notify_order_status_change, notify_delivery_status_change, notify_payment_verified


# Note: supplier_required decorator is now imported from decorators.py


def process_inventory_deduction(order, user, request=None):
    """
    Helper function to handle automatic inventory deduction for orders
    that reach qualifying status milestones.
    
    Args:
        order: SupplierOrder instance
        user: User performing the action
        request: HTTP request object (optional, for messages)
    
    Returns:
        bool: True if inventory was deducted, False otherwise
    """
    # Handle automatic inventory updates based on multiple trigger conditions
    # Inventory should be deducted when order reaches certain milestones
    
    # New order status triggers
    order_status_triggers = ['confirmed', 'processing', 'completed']
    delivery_status_triggers = ['out_for_delivery', 'delivered']
    
    # Legacy status triggers
    legacy_status_triggers = ['approved', 'delivered']
    
    # Check if current status qualifies for inventory deduction
    order_status_qualifies = order.order_status in order_status_triggers
    delivery_status_qualifies = order.delivery_status in delivery_status_triggers
    legacy_status_qualifies = order.status in legacy_status_triggers
    
    should_update_inventory = (
        (order_status_qualifies or delivery_status_qualifies or legacy_status_qualifies) and 
        not order.inventory_updated  # Use a flag to prevent duplicates
    )
    
    if should_update_inventory:
        # Set delivered timestamp and flag
        if not order.delivered_at:
            order.delivered_at = timezone.now()
        order.inventory_updated = True
        
        # Deduct from supplier's stock
        try:
            supplier_product = order.supplier_product
            previous_stock = supplier_product.available_stock
            
            # Always deduct stock, even if it goes negative (will show warning)
            supplier_product.available_stock -= order.quantity
            supplier_product.save()
            
            # Record stock movement
            StockMovement.objects.create(
                supplier_product=supplier_product,
                movement_type='sale',
                quantity=order.quantity,
                previous_stock=previous_stock,
                new_stock=supplier_product.available_stock,
                notes=f'Order #{order.id} - Status: {order.order_status}/{order.delivery_status} - Customer: {order.store_owner.first_name or order.store_owner.username}',
                created_by=user
            )
            
            if request:
                if previous_stock >= order.quantity:
                    messages.success(request, f'✓ Supplier stock updated: -{order.quantity} {supplier_product.unit} (Stock: {previous_stock} → {supplier_product.available_stock})')
                else:
                    messages.warning(request, f"⚠ Stock deducted but now negative: -{order.quantity} {supplier_product.unit} (Stock: {previous_stock} → {supplier_product.available_stock})")
        except Exception as e:
            if request:
                messages.error(request, f"✗ Stock deduction failed: {str(e)}")
            import logging
            logging.error(f"Stock deduction failed for order #{order.id}: {str(e)}")
        
        # Update owner's inventory
        try:
            supplier_user = order.supplier_product.supplier
            supplier_profile = getattr(supplier_user, 'supplier_profile', None)
            
            if supplier_profile:
                # Find or create corresponding Product for the owner
                product, created = Product.objects.get_or_create(
                    supplier_profile=supplier_profile,
                    name=order.supplier_product.name,
                    defaults={
                        'description': order.supplier_product.description,
                        'price': order.unit_price,
                        'unit': order.supplier_product.unit,
                        'manufactured_date': order.supplier_product.manufactured_date,
                        'expiration_date': order.supplier_product.expiration_date,
                        'is_available': True,
                    }
                )
                
                # Update or create inventory for the owner
                inventory, created = Inventory.objects.get_or_create(
                    owner=order.store_owner,
                    product=product,
                    defaults={'quantity': 0, 'low_stock_threshold': 10}
                )
                
                inventory.quantity += order.quantity
                inventory.last_restocked = timezone.now()
                inventory.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=order.store_owner,
                    action='inventory_updated',
                    description=f'Inventory updated: +{order.quantity} {order.supplier_product.unit} of {order.supplier_product.name} from Order #{order.id}',
                    ip_address=request.META.get('REMOTE_ADDR') if request else '127.0.0.1'
                )
                
                if request:
                    messages.success(request, f'✓ Owner inventory updated: +{order.quantity} {product.unit} of {product.name}')
        except Exception as e:
            if request:
                messages.error(request, f"✗ Owner inventory update failed: {str(e)}")
            import logging
            logging.error(f"Owner inventory update failed for order #{order.id}: {str(e)}")
        
        # Save order with inventory_updated flag
        order.save()
        return True
    
    return False


def get_or_create_supplier_profile(user):
    """Get or create SupplierProfile for the user"""
    try:
        return SupplierProfile.objects.get(user=user)
    except SupplierProfile.DoesNotExist:
        # Create a default supplier profile
        profile = SupplierProfile.objects.create(
            user=user,
            business_name=f"{user.first_name}'s Business" if user.first_name else user.username,
            contact_person=user.first_name or user.username,
            email=user.email,
            phone=user.profile.phone if hasattr(user, 'profile') and user.profile.phone else '',
            address=user.profile.address if hasattr(user, 'profile') and user.profile.address else ''
        )
        return profile


@supplier_required
def supplier_dashboard(request):
    """Main dashboard - Minimal and Fast"""
    # Get or create supplier profile
    supplier_profile = get_or_create_supplier_profile(request.user)
    
    # Recent orders - limit to 5
    recent_orders = SupplierOrder.objects.filter(
        supplier_product__supplier=request.user
    ).select_related('supplier_product', 'store_owner').order_by('-created_at')[:5]
    
    # Pending connection requests count only
    pending_requests_count = ConnectionRequest.objects.filter(
        supplier_profile=supplier_profile,
        status='pending'
    ).count()
    
    # Product statistics for charts
    products = SupplierProduct.objects.filter(supplier=request.user, is_active=True)
    
    # Product quantities for bar chart
    product_quantities = []
    for product in products:
        product_quantities.append({
            'name': product.name,
            'quantity': product.available_stock
        })
    
    # Stock status distribution for pie chart
    in_stock_count = 0
    low_stock_count = 0
    out_of_stock_count = 0
    
    for product in products:
        if product.available_stock == 0:
            out_of_stock_count += 1
        elif product.available_stock <= product.low_stock_threshold:
            low_stock_count += 1
        else:
            in_stock_count += 1
    
    context = {
        'recent_orders': recent_orders,
        'pending_requests_count': pending_requests_count,
        'supplier_profile': supplier_profile,
        'product_quantities': json.dumps(product_quantities),
        'in_stock_count': in_stock_count,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
    }
    return render(request, 'supplier/dashboard.html', context)


@supplier_required
def supplier_profile(request):
    """View and edit profile"""
    profile = request.user.profile
    
    # Get or create payment info
    from .models import SupplierPaymentInfo
    from .forms import SupplierPaymentInfoForm
    payment_info, created = SupplierPaymentInfo.objects.get_or_create(supplier=request.user)
    
    if request.method == 'POST':
        # Check which form was submitted
        if 'profile_submit' in request.POST:
            form = ProfileForm(request.POST, instance=profile, user=request.user)
            payment_form = SupplierPaymentInfoForm(instance=payment_info)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('supplier_profile')
        elif 'payment_submit' in request.POST:
            form = ProfileForm(instance=profile, user=request.user)
            payment_form = SupplierPaymentInfoForm(request.POST, instance=payment_info)
            if payment_form.is_valid():
                payment_form.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=request.user,
                    action='update' if not created else 'create',
                    description=f'Updated payment information',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, "Payment information updated successfully!")
                return redirect('supplier_profile')
    else:
        form = ProfileForm(instance=profile, user=request.user)
        payment_form = SupplierPaymentInfoForm(instance=payment_info)
    
    # Get stats for profile page
    total_products = request.user.supplier_products.count()
    active_products = request.user.supplier_products.filter(is_active=True).count()
    # Get orders for products owned by this supplier
    from .models import SupplierOrder
    total_orders = SupplierOrder.objects.filter(supplier_product__supplier=request.user).count()
    
    context = {
        'form': form,
        'payment_form': payment_form,
        'payment_info': payment_info,
        'has_payment_info': payment_info.has_gcash() or payment_info.has_paymaya() or payment_info.has_bank_transfer(),
        'total_products': total_products,
        'active_products': active_products,
        'total_orders': total_orders,
    }
    
    return render(request, 'supplier/profile.html', context)


@supplier_required
def product_list(request):
    """List all products"""
    # Get or create supplier profile
    supplier_profile = get_or_create_supplier_profile(request.user)
    
    # Get products linked to this supplier profile
    products = Product.objects.filter(supplier_profile=supplier_profile)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Filter by availability
    status = request.GET.get('status', '')
    if status == 'available':
        products = products.filter(is_available=True)
    elif status == 'unavailable':
        products = products.filter(is_available=False)
    
    context = {
        'products': products,
        'search': search,
        'status': status,
        'supplier_profile': supplier_profile,
    }
    return render(request, 'supplier/product_list.html', context)


@supplier_required
def product_add(request):
    """Add new product"""
    from django import forms
    
    # Get or create supplier profile
    supplier_profile = get_or_create_supplier_profile(request.user)
    
    class ProductForm(forms.ModelForm):
        class Meta:
            model = Product
            fields = ['name', 'description', 'price', 'unit', 'manufactured_date', 'expiration_date', 'is_available']
            widgets = {
                'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
                'name': forms.TextInput(attrs={'class': 'form-control'}),
                'price': forms.NumberInput(attrs={'class': 'form-control'}),
                'unit': forms.Select(attrs={'class': 'form-select'}),
                'manufactured_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                'expiration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            }
        
        def clean(self):
            cleaned_data = super().clean()
            manufactured_date = cleaned_data.get('manufactured_date')
            expiration_date = cleaned_data.get('expiration_date')
            
            if manufactured_date and expiration_date:
                if expiration_date <= manufactured_date:
                    raise forms.ValidationError("Expiration date must be after the manufactured date.")
            
            if manufactured_date:
                from django.utils import timezone
                today = timezone.now().date()
                if manufactured_date > today:
                    raise forms.ValidationError("Manufactured date cannot be in the future.")
            
            return cleaned_data
    
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.supplier_profile = supplier_profile
            product.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action='create',
                description=f'Added new product: {product.name} (₱{product.price}/{product.unit})',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f"Product '{product.name}' added successfully!")
            return redirect('supplier_product_list')
    else:
        form = ProductForm()
    
    return render(request, 'supplier/product_form.html', {'form': form, 'action': 'Add'})


@supplier_required
def product_edit(request, pk):
    """Edit product"""
    from django import forms
    
    # Get supplier profile
    supplier_profile = get_or_create_supplier_profile(request.user)
    
    # Get product owned by this supplier
    product = get_object_or_404(Product, pk=pk, supplier_profile=supplier_profile)
    
    class ProductForm(forms.ModelForm):
        class Meta:
            model = Product
            fields = ['name', 'description', 'price', 'unit', 'manufactured_date', 'expiration_date', 'is_available']
            widgets = {
                'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
                'name': forms.TextInput(attrs={'class': 'form-control'}),
                'price': forms.NumberInput(attrs={'class': 'form-control'}),
                'unit': forms.Select(attrs={'class': 'form-select'}),
                'manufactured_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                'expiration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            }
        
        def clean(self):
            cleaned_data = super().clean()
            manufactured_date = cleaned_data.get('manufactured_date')
            expiration_date = cleaned_data.get('expiration_date')
            
            if manufactured_date and expiration_date:
                if expiration_date <= manufactured_date:
                    raise forms.ValidationError("Expiration date must be after the manufactured date.")
            
            if manufactured_date:
                from django.utils import timezone
                today = timezone.now().date()
                if manufactured_date > today:
                    raise forms.ValidationError("Manufactured date cannot be in the future.")
            
            return cleaned_data
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action='update',
                description=f'Updated product: {product.name} (₱{product.price}/{product.unit})',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect('supplier_product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'supplier/product_form.html', {
        'form': form,
        'action': 'Edit',
        'product': product
    })


@supplier_required
def product_delete(request, pk):
    """Delete product"""
    # Get supplier profile
    supplier_profile = get_or_create_supplier_profile(request.user)
    
    # Get product owned by this supplier
    product = get_object_or_404(Product, pk=pk, supplier_profile=supplier_profile)
    
    if request.method == 'POST':
        name = product.name
        product.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            description=f'Deleted product: {name}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, f"Product '{name}' deleted successfully!")
        return redirect('supplier_product_list')
    
    return render(request, 'supplier/product_confirm_delete.html', {'product': product})


@supplier_required
def order_list(request):
    """List all orders"""
    my_suppliers = Supplier.objects.filter(
        Q(email=request.user.email) | Q(contact_person=request.user.first_name)
    )
    
    orders = Order.objects.filter(
        supplier__in=my_suppliers
    ).exclude(status='cart').select_related('owner', 'supplier').order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    context = {
        'orders': orders,
        'status': status,
    }
    return render(request, 'supplier/order_list.html', context)


@supplier_required
def order_detail(request, pk):
    """View order details and update status"""
    my_suppliers = Supplier.objects.filter(
        Q(email=request.user.email) | Q(contact_person=request.user.first_name)
    )
    
    order = get_object_or_404(Order, pk=pk, supplier__in=my_suppliers)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES).keys():
            old_status = order.status
            order.status = new_status
            order.save()
            
            # Update inventory when order is marked as delivered
            if new_status == 'delivered' and old_status != 'delivered':
                for item in order.items.all():
                    inventory, created = Inventory.objects.get_or_create(
                        owner=order.owner,
                        product=item.product,
                        defaults={'quantity': 0}
                    )
                    inventory.quantity += item.quantity
                    inventory.last_restocked = timezone.now()
                    inventory.save()
                messages.success(request, f"Order #{order.id} marked as delivered! Owner's inventory has been updated.")
            else:
                messages.success(request, f"Order #{order.id} status updated to {order.get_status_display()}!")
            
            return redirect('supplier_order_detail', pk=order.id)
    
    context = {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'supplier/order_detail.html', context)


@supplier_required
def buyer_list(request):
    """List all buyers (store owners)"""
    # Get supplier profile
    supplier_profile = get_or_create_supplier_profile(request.user)
    
    my_suppliers = Supplier.objects.filter(supplier_profile=supplier_profile)
    
    # Get unique buyers
    buyers = []
    buyer_ids = set()
    
    for supplier in my_suppliers:
        owners = Supplier.objects.filter(id=supplier.id).values_list('owner', flat=True)
        for owner_id in owners:
            if owner_id not in buyer_ids:
                buyer_ids.add(owner_id)
                from django.contrib.auth.models import User
                owner = User.objects.get(id=owner_id)
                if hasattr(owner, 'profile'):
                    # Get order stats from SupplierOrder model
                    # Get all supplier products for this supplier
                    supplier_products = SupplierProduct.objects.filter(supplier=request.user)
                    
                    # Count total orders from this buyer for this supplier's products
                    total_orders = SupplierOrder.objects.filter(
                        store_owner=owner,
                        supplier_product__in=supplier_products
                    ).count()
                    
                    # Calculate total spent (sum of all orders)
                    total_spent = SupplierOrder.objects.filter(
                        store_owner=owner,
                        supplier_product__in=supplier_products
                    ).aggregate(total=Sum('total_amount'))['total'] or 0
                    
                    buyers.append({
                        'owner': owner,
                        'profile': owner.profile,
                        'supplier': supplier,
                        'total_orders': total_orders,
                        'total_spent': total_spent,
                    })
    
    # Get pending connection requests count
    pending_requests_count = ConnectionRequest.objects.filter(
        supplier_profile=supplier_profile,
        status='pending'
    ).count()
    
    # Search
    search = request.GET.get('search', '')
    if search:
        buyers = [b for b in buyers if 
                  search.lower() in b['owner'].first_name.lower() or
                  search.lower() in b['owner'].email.lower() or
                  (b['profile'].store_name and search.lower() in b['profile'].store_name.lower())]
    
    context = {
        'buyers': buyers,
        'search': search,
        'pending_requests_count': pending_requests_count,
    }
    return render(request, 'supplier/buyer_list.html', context)


@supplier_required
def buyer_detail(request, owner_id, supplier_id):
    """View buyer details and order history"""
    from django.contrib.auth.models import User
    
    my_suppliers = Supplier.objects.filter(
        Q(email=request.user.email) | Q(contact_person=request.user.first_name)
    )
    
    supplier = get_object_or_404(Supplier, pk=supplier_id, id__in=my_suppliers)
    owner = get_object_or_404(User, pk=owner_id)
    
    # Get SupplierOrders (orders from this owner to this supplier)
    orders = SupplierOrder.objects.filter(
        store_owner=owner,
        supplier_product__supplier=request.user
    ).select_related('supplier_product').order_by('-created_at')
    
    # Stats - use new order_status and delivery_status fields
    total_orders = orders.count()
    completed_orders = orders.filter(order_status='completed').count()
    delivered_orders = orders.filter(delivery_status='delivered').count()
    pending_orders = orders.filter(order_status='pending').count()
    
    # Total spent - only count completed and delivered orders
    total_spent = orders.filter(
        order_status='completed',
        delivery_status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Recent orders (last 5)
    recent_orders = orders[:5]
    
    context = {
        'buyer': owner,
        'profile': owner.profile if hasattr(owner, 'profile') else None,
        'supplier': supplier,
        'orders': orders,
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'delivered_orders': delivered_orders,
        'pending_orders': pending_orders,
        'total_spent': total_spent,
    }
    return render(request, 'supplier/buyer_detail.html', context)


@supplier_required
def buyer_delete(request, owner_id, supplier_id):
    """Remove buyer connection"""
    my_suppliers = Supplier.objects.filter(
        Q(email=request.user.email) | Q(contact_person=request.user.first_name)
    )
    
    supplier = get_object_or_404(Supplier, pk=supplier_id, id__in=my_suppliers)
    
    from django.contrib.auth.models import User
    owner = get_object_or_404(User, pk=owner_id)
    
    if request.method == 'POST':
        # Delete the supplier connection
        supplier.delete()
        messages.success(request, f"Connection with {owner.first_name} removed successfully!")
        return redirect('supplier_buyer_list')
    
    context = {
        'buyer': owner,
        'supplier': supplier,
    }
    return render(request, 'supplier/buyer_confirm_delete.html', context)


@supplier_required
def connection_requests(request):
    """View all connection requests"""
    supplier_profile = get_or_create_supplier_profile(request.user)
    
    # Get all connection requests
    requests = ConnectionRequest.objects.filter(
        supplier_profile=supplier_profile
    ).select_related('owner', 'owner__profile').order_by('-created_at')
    
    context = {
        'requests': requests,
        'supplier_profile': supplier_profile,
    }
    return render(request, 'supplier/connection_requests.html', context)


@supplier_required
def accept_connection_request(request, request_id):
    """Accept a connection request"""
    supplier_profile = get_or_create_supplier_profile(request.user)
    connection_request = get_object_or_404(
        ConnectionRequest,
        pk=request_id,
        supplier_profile=supplier_profile,
        status='pending'
    )
    
    if request.method == 'POST':
        # Update request status
        connection_request.status = 'accepted'
        connection_request.save()
        
        # Create Supplier connection
        Supplier.objects.create(
            owner=connection_request.owner,
            supplier_profile=supplier_profile,
            name=supplier_profile.business_name,
            contact_person=supplier_profile.contact_person,
            email=supplier_profile.email,
            phone=supplier_profile.phone,
            address=supplier_profile.address,
            is_active=True
        )
        
        messages.success(request, f"Connection with {connection_request.owner.first_name} accepted!")
        return redirect('supplier_connection_requests')
    
    return redirect('supplier_connection_requests')


@supplier_required
def reject_connection_request(request, request_id):
    """Reject a connection request"""
    supplier_profile = get_or_create_supplier_profile(request.user)
    connection_request = get_object_or_404(
        ConnectionRequest,
        pk=request_id,
        supplier_profile=supplier_profile,
        status='pending'
    )
    
    if request.method == 'POST':
        connection_request.status = 'rejected'
        connection_request.save()
        messages.info(request, f"Connection request from {connection_request.owner.first_name} rejected.")
        return redirect('supplier_connection_requests')
    
    return redirect('supplier_connection_requests')


# ========== NEW SUPPLIER INVENTORY MANAGEMENT VIEWS ==========

@supplier_required
def supplier_inventory_list(request):
    """List all supplier products with stock levels"""
    products = SupplierProduct.objects.filter(supplier=request.user)
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        products = products.filter(category=category_filter)
    
    # Filter by stock status
    stock_filter = request.GET.get('stock', '')
    if stock_filter == 'low':
        products = [p for p in products if p.is_low_stock and not p.is_out_of_stock]
    elif stock_filter == 'out':
        products = [p for p in products if p.is_out_of_stock]
    elif stock_filter == 'available':
        products = products.filter(available_stock__gt=0)
    
    # Filter by active status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)
    
    # Calculate summary stats only (removed unused chart data)
    all_products = SupplierProduct.objects.filter(supplier=request.user)
    
    # Stock status counts
    low_stock_count = all_products.filter(available_stock__lte=F('low_stock_threshold'), available_stock__gt=0).count()
    out_of_stock_count = all_products.filter(available_stock=0).count()
    in_stock_count = all_products.filter(available_stock__gt=F('low_stock_threshold')).count()
    
    # Calculate summary stats
    total_products = all_products.count()
    
    context = {
        'products': products,
        'search': search,
        'category_filter': category_filter,
        'category_choices': SupplierProduct.CATEGORY_CHOICES,
        'stock_filter': stock_filter,
        'status_filter': status_filter,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'in_stock_count': in_stock_count,
    }
    return render(request, 'supplier/inventory_list.html', context)


@supplier_required
def supplier_product_add(request):
    """Add new supplier product"""
    if request.method == 'POST':
        form = SupplierProductForm(request.POST)
        if form.is_valid():
            # Check for duplicate product name for this supplier
            name = form.cleaned_data['name']
            if SupplierProduct.objects.filter(supplier=request.user, name=name).exists():
                form.add_error('name', 'You already have a product with this name. Please choose a different name.')
            else:
                product = form.save(commit=False)
                product.supplier = request.user
                product.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=request.user,
                    action='create',
                    description=f'Added new product: {product.name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                # Create initial stock movement record
                StockMovement.objects.create(
                    supplier_product=product,
                    movement_type='restock',
                    quantity=product.available_stock,
                    previous_stock=0,
                    new_stock=product.available_stock,
                    notes=f'Initial stock for new product',
                    created_by=request.user
                )
                
                messages.success(request, f'Product "{product.name}" added successfully!')
                return redirect('supplier_inventory_list')
        else:
            # Add form errors to messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = SupplierProductForm()
    
    context = {'form': form}
    return render(request, 'supplier/product_add.html', context)


@supplier_required
def supplier_product_edit(request, pk):
    """Edit supplier product"""
    product = get_object_or_404(SupplierProduct, pk=pk, supplier=request.user)
    
    if request.method == 'POST':
        form = SupplierProductForm(request.POST, instance=product)
        if form.is_valid():
            # Check for duplicate product name for this supplier (excluding current product)
            name = form.cleaned_data['name']
            duplicate_check = SupplierProduct.objects.filter(supplier=request.user, name=name).exclude(pk=product.pk)
            if duplicate_check.exists():
                form.add_error('name', 'You already have another product with this name. Please choose a different name.')
            else:
                old_stock = product.available_stock
                product = form.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=request.user,
                    action='update',
                    description=f'Updated product: {product.name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                # Create stock movement if stock changed
                if old_stock != product.available_stock:
                    StockMovement.objects.create(
                        supplier_product=product,
                        movement_type='adjustment',
                        quantity=product.available_stock - old_stock,
                        previous_stock=old_stock,
                        new_stock=product.available_stock,
                        notes=f'Stock adjusted during product update',
                        created_by=request.user
                    )
                
                messages.success(request, f'Product "{product.name}" updated successfully!')
                return redirect('supplier_inventory_list')
        else:
            # Add form errors to messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = SupplierProductForm(instance=product)
    
    context = {'form': form, 'product': product}
    return render(request, 'supplier/product_edit.html', context)


@supplier_required
def supplier_product_delete(request, pk):
    """Delete supplier product"""
    product = get_object_or_404(SupplierProduct, pk=pk, supplier=request.user)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            description=f'Deleted product: {product_name}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('supplier_inventory_list')
    
    context = {'product': product}
    return render(request, 'supplier/product_confirm_delete.html', context)


@supplier_required
def supplier_product_restock(request, pk):
    """Restock supplier product"""
    product = get_object_or_404(SupplierProduct, pk=pk, supplier=request.user)
    
    if request.method == 'POST':
        form = RestockForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            
            old_stock = product.available_stock
            product.available_stock += quantity
            product.save()
            
            # Create stock movement record
            StockMovement.objects.create(
                supplier_product=product,
                movement_type='restock',
                quantity=quantity,
                previous_stock=old_stock,
                new_stock=product.available_stock,
                notes=notes or f'Restocked {quantity} {product.unit}',
                created_by=request.user
            )
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action='restock',
                description=f'Restocked {product.name}: +{quantity} {product.unit}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Successfully restocked {quantity} {product.unit} of "{product.name}"!')
            return redirect('supplier_inventory_list')
    else:
        form = RestockForm()
    
    context = {'form': form, 'product': product}
    return render(request, 'supplier/product_restock.html', context)


@supplier_required
def supplier_orders_list(request):
    """List all orders from store owners - Separated into Active and Completed"""
    # Get all orders for products owned by this supplier
    all_orders = SupplierOrder.objects.filter(
        supplier_product__supplier=request.user
    ).select_related('supplier_product', 'store_owner')
    
    # Search by store owner name or product name
    search = request.GET.get('search', '')
    if search:
        all_orders = all_orders.filter(
            Q(store_owner__first_name__icontains=search) |
            Q(store_owner__username__icontains=search) |
            Q(supplier_product__name__icontains=search)
        )
    
    # Filter by order status
    status_filter = request.GET.get('status', '')
    if status_filter:
        all_orders = all_orders.filter(order_status=status_filter)
    
    # Separate active orders from completed/delivered orders
    active_orders = all_orders.exclude(
        order_status='completed',
        delivery_status='delivered'
    ).order_by('-created_at')
    
    completed_orders = all_orders.filter(
        order_status='completed',
        delivery_status='delivered'
    ).order_by('-created_at')
    
    # Pagination for active orders
    active_paginator = Paginator(active_orders, 10)
    active_page_number = request.GET.get('active_page')
    active_page_obj = active_paginator.get_page(active_page_number)
    
    # Pagination for completed orders
    completed_paginator = Paginator(completed_orders, 10)
    completed_page_number = request.GET.get('completed_page')
    completed_page_obj = completed_paginator.get_page(completed_page_number)
    
    context = {
        'active_orders': active_page_obj,
        'completed_orders': completed_page_obj,
        'active_page_obj': active_page_obj,
        'completed_page_obj': completed_page_obj,
        'status_filter': status_filter,
        'search': search,
        'status_choices': SupplierOrder.ORDER_STATUS_CHOICES,
    }
    return render(request, 'supplier/orders_list.html', context)


@supplier_required
def supplier_order_detail(request, pk):
    """View individual order details - Status updates handled by update_order_delivery_status view"""
    order = get_object_or_404(SupplierOrder, pk=pk, supplier_product__supplier=request.user)
    
    context = {'order': order}
    return render(request, 'supplier/supplier_order_detail.html', context)


@supplier_required
def supplier_reports(request):
    """Transaction history and reports"""
    # Date filtering
    from datetime import datetime, timedelta
    from django.db.models import Count
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)  # Default to last 30 days
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
    
    # Get delivered orders in date range
    delivered_orders = SupplierOrder.objects.filter(
        supplier_product__supplier=request.user,
        status='delivered',
        delivered_at__range=[start_date, end_date]
    ).select_related('supplier_product', 'store_owner')
    
    # Calculate summary statistics
    total_revenue = delivered_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_units_sold = delivered_orders.aggregate(total=Sum('quantity'))['total'] or 0
    total_orders = delivered_orders.count()
    
    # Top selling products
    top_products = delivered_orders.values(
        'supplier_product__name'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('total_amount')
    ).order_by('-total_sold')[:10]
    
    # Recent stock movements
    stock_movements = StockMovement.objects.filter(
        supplier_product__supplier=request.user,
        created_at__range=[start_date, end_date]
    ).select_related('supplier_product').order_by('-created_at')[:20]
    
    context = {
        'delivered_orders': delivered_orders,
        'total_revenue': total_revenue,
        'total_units_sold': total_units_sold,
        'total_orders': total_orders,
        'top_products': top_products,
        'stock_movements': stock_movements,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'supplier/reports.html', context)


# ========== PAYMENT VERIFICATION VIEWS ==========

@supplier_required
def verify_payment(request, order_id):
    """Supplier verifies that they have received payment for an order"""
    order = get_object_or_404(SupplierOrder, pk=order_id, supplier_product__supplier=request.user)
    
    # Check if payment status is 'paid'
    if order.payment_status != 'paid':
        messages.error(request, 'Payment verification can only be done for orders marked as "Paid" by the store owner.')
        return redirect('supplier_order_detail', pk=order_id)
    
    # Check if already verified
    if order.payment_verified:
        messages.info(request, 'This payment has already been verified.')
        return redirect('supplier_order_detail', pk=order_id)
    
    if request.method == 'POST':
        form = VerifyPaymentForm(request.POST)
        if form.is_valid():
            # Update order with verification
            order.payment_verified = True
            order.verified_by = request.user
            order.verified_date = timezone.now()
            
            # Add verification notes to order notes if provided
            verification_notes = form.cleaned_data.get('verification_notes')
            if verification_notes:
                order.notes = f"{order.notes}\n\n[Payment Verified by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}]\n{verification_notes}" if order.notes else f"[Payment Verified]\n{verification_notes}"
            
            order.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action='order_delivered',
                description=f'Verified payment for Order #{order.id} - {order.supplier_product.name} - ₱{order.total_amount}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Send notification to owner
            notify_payment_verified(order, request.user)
            
            messages.success(request, f'Payment for Order #{order.id} has been verified successfully!')
            return redirect('supplier_order_detail', pk=order_id)
    else:
        form = VerifyPaymentForm()
    
    context = {
        'order': order,
        'form': form,
    }
    return render(request, 'supplier/verify_payment.html', context)


@supplier_required
def payment_verification_report(request):
    """View payment verification status for all orders"""
    # Get all orders for this supplier
    orders = SupplierOrder.objects.filter(
        supplier_product__supplier=request.user
    ).select_related('supplier_product', 'store_owner')
    
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
    total_paid_orders = SupplierOrder.objects.filter(
        supplier_product__supplier=request.user,
        payment_status='paid'
    ).count()
    
    verified_payments = SupplierOrder.objects.filter(
        supplier_product__supplier=request.user,
        payment_verified=True
    ).count()
    
    pending_verification = SupplierOrder.objects.filter(
        supplier_product__supplier=request.user,
        payment_status='paid',
        payment_verified=False
    ).count()
    
    total_verified_amount = SupplierOrder.objects.filter(
        supplier_product__supplier=request.user,
        payment_verified=True
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    context = {
        'orders': orders,
        'total_paid_orders': total_paid_orders,
        'verified_payments': verified_payments,
        'pending_verification': pending_verification,
        'total_verified_amount': total_verified_amount,
        'verification_filter': verification_filter,
        'payment_status_filter': payment_status_filter,
    }
    return render(request, 'supplier/payment_verification_report.html', context)


# ========== SUPPLIER PAYMENT INFORMATION VIEWS ==========

@supplier_required
def supplier_payment_info(request):
    """View and manage supplier's payment receiving information"""
    # Get or create payment info for this supplier
    payment_info, created = SupplierPaymentInfo.objects.get_or_create(
        supplier=request.user
    )
    
    if request.method == 'POST':
        form = SupplierPaymentInfoForm(request.POST, instance=payment_info)
        if form.is_valid():
            form.save()
            
            # Log activity
            action = 'create' if created else 'update'
            ActivityLog.objects.create(
                user=request.user,
                action=action,
                description=f'{"Added" if created else "Updated"} payment receiving information',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Payment information saved successfully!')
            return redirect('supplier_payment_info')
    else:
        form = SupplierPaymentInfoForm(instance=payment_info)
    
    context = {
        'form': form,
        'payment_info': payment_info,
        'has_payment_info': payment_info.has_gcash() or payment_info.has_paymaya() or payment_info.has_bank_transfer(),
    }
    return render(request, 'supplier/payment_info.html', context)


@supplier_required
def update_order_delivery_status(request, pk):
    """Update order status and delivery status for an order"""
    order = get_object_or_404(SupplierOrder, pk=pk, supplier_product__supplier=request.user)
    
    if request.method == 'POST':
        form = CombinedStatusUpdateForm(request.POST, instance=order)
        if form.is_valid():
            old_order_status = order.order_status
            old_delivery_status = order.delivery_status
            status_notes = form.cleaned_data.get('status_notes', '')
            
            order = form.save(commit=False)
            
            # Track if order status changed
            if order.order_status != old_order_status:
                order.order_status_updated_at = timezone.now()
                order.status_updated_by = request.user
                
                # Log activity for order status change
                ActivityLog.objects.create(
                    user=request.user,
                    action='order_status_updated',
                    description=f'Order #{order.id} status changed from {old_order_status} to {order.order_status}' + (f' - {status_notes}' if status_notes else ''),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                # Send notification to owner
                notify_order_status_change(order, old_order_status, order.order_status, request.user)
                
                messages.success(request, f'Order status updated to {order.get_order_status_display()}!')
            
            # Track if delivery status changed
            if order.delivery_status != old_delivery_status:
                order.delivery_status_updated_at = timezone.now()
                order.status_updated_by = request.user
                
                # Log activity for delivery status change
                ActivityLog.objects.create(
                    user=request.user,
                    action='delivery_status_updated',
                    description=f'Order #{order.id} delivery status changed from {old_delivery_status} to {order.delivery_status}' + (f' - {status_notes}' if status_notes else ''),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                # Send notification to owner
                notify_delivery_status_change(order, old_delivery_status, order.delivery_status, request.user)
                
                messages.success(request, f'Delivery status updated to {order.get_delivery_status_display()}!')
            
            # Save the order first to update timestamps
            order.save()
            
            # Handle automatic inventory deduction using helper function
            process_inventory_deduction(order, request.user, request)
            
            # Add status notes to order notes if provided
            if status_notes:
                if order.notes:
                    order.notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] Status Update: {status_notes}"
                else:
                    order.notes = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')}] Status Update: {status_notes}"
                order.save()
            
            return redirect('supplier_order_detail', pk=order.pk)
    else:
        form = CombinedStatusUpdateForm(instance=order)
    
    context = {
        'order': order,
        'form': form,
    }
    return render(request, 'supplier/update_order_delivery_status.html', context)
