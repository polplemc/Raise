from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from django.utils import timezone
import json
from .models import Supplier, Product, Inventory, Order, OrderItem, UserProfile, ActivityLog, SupplierProduct, SupplierOrder, BusinessOwnerProfile, SupplierProfile
from .forms import OwnerCreateForm, OwnerEditForm, StaffCreateForm, SupplierCreateForm, SupplierEditForm, UserApprovalForm


# Decorator to ensure only admins can access
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_superuser:
            messages.error(request, "Access denied. Admin account required.")
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper


# Helper function to log activities
def log_activity(user, action, description, ip_address=None):
    """Create activity log entry"""
    ActivityLog.objects.create(
        user=user,
        action=action,
        description=description,
        ip_address=ip_address
    )


@admin_required
def admin_dashboard(request):
    """Main admin dashboard with overview"""
    # Get counts
    total_users = User.objects.count()
    total_owners = UserProfile.objects.filter(role='owner').count()
    total_suppliers = UserProfile.objects.filter(role='supplier').count()
    total_staff = UserProfile.objects.filter(role='staff').count()
    
    # User approval counts
    pending_users_count = UserProfile.objects.filter(is_approved=False).count()
    approved_users_count = UserProfile.objects.filter(is_approved=True).count()
    
    # Product and Order counts (NEW system only)
    total_products = SupplierProduct.objects.count()
    total_orders = SupplierOrder.objects.count()
    
    # Revenue from orders
    total_revenue = SupplierOrder.objects.filter(status='delivered').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Recent activity
    recent_activities = ActivityLog.objects.select_related('user').all()[:10]
    
    # Recent orders from NEW system
    recent_orders = SupplierOrder.objects.select_related(
        'supplier_product', 'supplier_product__supplier', 'store_owner'
    ).order_by('-created_at')[:5]
    
    # Get owner list (top 5)
    owners = User.objects.filter(profile__role='owner').select_related('profile')[:5]
    
    # Get supplier list (top 5)
    suppliers_profiles = UserProfile.objects.filter(role='supplier').select_related('user')[:5]
    
    # Get staff list (top 5)
    staff_profiles = UserProfile.objects.filter(role='staff').select_related('user', 'owner')[:5]
    
    # Activity data for chart
    activity_data = []
    for log in ActivityLog.objects.all()[:10]:
        activity_data.append({
            'user': log.user.username,
            'action': log.get_action_display(),
            'time': log.timestamp.strftime('%H:%M')
        })
    
    context = {
        'total_users': total_users,
        'total_owners': total_owners,
        'total_suppliers': total_suppliers,
        'total_staff': total_staff,
        'pending_users_count': pending_users_count,
        'approved_users_count': approved_users_count,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_activities': recent_activities,
        'recent_orders': recent_orders,
        'owners': owners,
        'suppliers_profiles': suppliers_profiles,
        'staff_profiles': staff_profiles,
        'activity_data': json.dumps(activity_data),
    }
    return render(request, 'admin/dashboard.html', context)


@admin_required
def admin_owners_list(request):
    """List all store owners (view only)"""
    owners = User.objects.filter(profile__role='owner').select_related('profile')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        owners = owners.filter(
            Q(first_name__icontains=search) |
            Q(email__icontains=search) |
            Q(profile__store_name__icontains=search)
        )
    
    # Get stats for each owner
    owner_data = []
    for owner in owners:
        total_orders = SupplierOrder.objects.filter(store_owner=owner).count()
        total_spent = SupplierOrder.objects.filter(
            store_owner=owner, status='delivered'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        inventory_count = Inventory.objects.filter(owner=owner).count()
        staff_count = UserProfile.objects.filter(role='staff', owner=owner).count()
        
        owner_data.append({
            'user': owner,
            'profile': owner.profile,
            'total_orders': total_orders,
            'total_spent': total_spent,
            'inventory_count': inventory_count,
            'staff_count': staff_count,
        })
    
    context = {
        'owner_data': owner_data,
        'search': search,
    }
    return render(request, 'admin/owners_list.html', context)


@admin_required
def admin_owner_detail(request, user_id):
    """View owner details (view only)"""
    owner = get_object_or_404(User, id=user_id, profile__role='owner')
    
    # Get stats
    orders = SupplierOrder.objects.filter(store_owner=owner).select_related(
        'supplier_product', 'supplier_product__supplier'
    ).order_by('-created_at')
    inventory_items = Inventory.objects.filter(owner=owner).select_related('product')
    suppliers = Supplier.objects.filter(owner=owner)
    
    # Get staff members
    staff_members = UserProfile.objects.filter(
        role='staff', 
        owner=owner
    ).select_related('user').order_by('-created_at')
    
    total_orders = orders.count()
    total_spent = orders.filter(status='delivered').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Recent activity
    recent_activities = ActivityLog.objects.filter(user=owner)[:10]
    
    context = {
        'owner': owner,
        'profile': owner.profile,
        'orders': orders[:10],
        'inventory_items': inventory_items[:10],
        'suppliers': suppliers,
        'staff_members': staff_members,
        'staff_count': staff_members.count(),
        'total_orders': total_orders,
        'total_spent': total_spent,
        'recent_activities': recent_activities,
    }
    return render(request, 'admin/owner_detail.html', context)


@admin_required
def admin_owner_create(request):
    """Create a new owner account"""
    if request.method == 'POST':
        form = OwnerCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_activity(
                request.user,
                'create',
                f'Created owner account: {user.username}',
                request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Owner account "{user.username}" created successfully!')
            return redirect('admin_owner_detail', user_id=user.id)
    else:
        form = OwnerCreateForm()
    
    context = {
        'form': form,
    }
    return render(request, 'admin/owner_create.html', context)


@admin_required
def admin_owner_edit(request, user_id):
    """Edit an existing owner account"""
    owner = get_object_or_404(User, id=user_id, profile__role='owner')
    
    if request.method == 'POST':
        form = OwnerEditForm(request.POST, instance=owner)
        if form.is_valid():
            user = form.save()
            log_activity(
                request.user,
                'update',
                f'Updated owner account: {user.username}',
                request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Owner account "{user.username}" updated successfully!')
            return redirect('admin_owner_detail', user_id=user.id)
    else:
        form = OwnerEditForm(instance=owner)
    
    context = {
        'form': form,
        'owner': owner,
    }
    return render(request, 'admin/owner_edit.html', context)


@admin_required
def admin_owner_delete(request, user_id):
    """Delete an owner account"""
    owner = get_object_or_404(User, id=user_id, profile__role='owner')
    
    if request.method == 'POST':
        username = owner.username
        log_activity(
            request.user,
            'delete',
            f'Deleted owner account: {username}',
            request.META.get('REMOTE_ADDR')
        )
        owner.delete()
        messages.success(request, f'Owner account "{username}" deleted successfully!')
        return redirect('admin_owners_list')
    
    context = {
        'owner': owner,
    }
    return render(request, 'admin/owner_delete.html', context)


@admin_required
def admin_owner_staff_create(request, owner_id):
    """Create a staff account for a specific owner"""
    owner = get_object_or_404(User, id=owner_id, profile__role='owner')
    
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            staff_user = form.save(commit=False)
            staff_user.save()
            
            # Create staff profile linked to this owner
            UserProfile.objects.create(
                user=staff_user,
                role='staff',
                owner=owner,
                phone=form.cleaned_data.get('phone', ''),
                is_active=True
            )
            
            log_activity(
                request.user,
                'create',
                f'Created staff account: {staff_user.username} for owner: {owner.username}',
                request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Staff account "{staff_user.username}" created successfully!')
            return redirect('admin_owner_detail', user_id=owner.id)
    else:
        form = StaffCreateForm()
    
    context = {
        'form': form,
        'owner': owner,
    }
    return render(request, 'admin/owner_staff_create.html', context)


@admin_required
def admin_suppliers_list(request):
    """List all suppliers (view only)"""
    suppliers_profiles = UserProfile.objects.filter(role='supplier').select_related('user')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        suppliers_profiles = suppliers_profiles.filter(
            Q(user__first_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    # Get stats for each supplier
    supplier_data = []
    for profile in suppliers_profiles:
        user = profile.user
        
        # Get supplier stats from NEW system
        products_count = SupplierProduct.objects.filter(supplier=user).count()
        orders_count = SupplierOrder.objects.filter(supplier_product__supplier=user).count()
        revenue = SupplierOrder.objects.filter(
            supplier_product__supplier=user, status='delivered'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        supplier_data.append({
            'user': user,
            'profile': profile,
            'products_count': products_count,
            'orders_count': orders_count,
            'revenue': revenue,
        })
    
    context = {
        'supplier_data': supplier_data,
        'search': search,
    }
    return render(request, 'admin/suppliers_list.html', context)


@admin_required
def admin_supplier_detail(request, user_id):
    """View supplier details (view only)"""
    user = get_object_or_404(User, id=user_id, profile__role='supplier')
    
    # Get products and orders from NEW system
    products = SupplierProduct.objects.filter(supplier=user)
    orders = SupplierOrder.objects.filter(
        supplier_product__supplier=user
    ).select_related('supplier_product', 'store_owner').order_by('-created_at')
    
    # Stats
    products_count = products.count()
    orders_count = orders.count()
    completed_orders = orders.filter(order_status='completed').count()
    delivered_orders = orders.filter(delivery_status='delivered').count()
    pending_orders = orders.filter(order_status='pending').count()
    
    # Revenue - only count completed AND delivered orders
    revenue = orders.filter(
        order_status='completed',
        delivery_status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Recent activity
    recent_activities = ActivityLog.objects.filter(user=user)[:10]
    
    context = {
        'supplier_user': user,
        'profile': user.profile,
        'products': products[:10],
        'orders': orders[:10],
        'products_count': products_count,
        'orders_count': orders_count,
        'completed_orders': completed_orders,
        'delivered_orders': delivered_orders,
        'pending_orders': pending_orders,
        'revenue': revenue,
        'recent_activities': recent_activities,
    }
    return render(request, 'admin/supplier_detail.html', context)


@admin_required
def admin_supplier_create(request):
    """Create a new supplier account"""
    if request.method == 'POST':
        form = SupplierCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_activity(
                request.user,
                'create',
                f'Created supplier account: {user.username}',
                request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Supplier account "{user.username}" created successfully!')
            return redirect('admin_supplier_detail', user_id=user.id)
    else:
        form = SupplierCreateForm()
    
    context = {
        'form': form,
    }
    return render(request, 'admin/supplier_create.html', context)


@admin_required
def admin_supplier_edit(request, user_id):
    """Edit an existing supplier account"""
    supplier = get_object_or_404(User, id=user_id, profile__role='supplier')
    
    if request.method == 'POST':
        form = SupplierEditForm(request.POST, instance=supplier)
        if form.is_valid():
            user = form.save()
            log_activity(
                request.user,
                'update',
                f'Updated supplier account: {user.username}',
                request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Supplier account "{user.username}" updated successfully!')
            return redirect('admin_supplier_detail', user_id=user.id)
    else:
        form = SupplierEditForm(instance=supplier)
    
    context = {
        'form': form,
        'supplier': supplier,
    }
    return render(request, 'admin/supplier_edit.html', context)


@admin_required
def admin_supplier_delete(request, user_id):
    """Delete a supplier account"""
    supplier = get_object_or_404(User, id=user_id, profile__role='supplier')
    
    if request.method == 'POST':
        username = supplier.username
        log_activity(
            request.user,
            'delete',
            f'Deleted supplier account: {username}',
            request.META.get('REMOTE_ADDR')
        )
        supplier.delete()
        messages.success(request, f'Supplier account "{username}" deleted successfully!')
        return redirect('admin_suppliers_list')
    
    context = {
        'supplier': supplier,
    }
    return render(request, 'admin/supplier_delete.html', context)


@admin_required
def admin_products_list(request):
    """List all products (view only) - NEW system"""
    products = SupplierProduct.objects.select_related('supplier').all()
    
    # Search
    search = request.GET.get('search', '')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(supplier__first_name__icontains=search) |
            Q(supplier__username__icontains=search)
        )
    
    # Filter by availability
    status = request.GET.get('status', '')
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)
    
    context = {
        'products': products,
        'search': search,
        'status': status,
    }
    return render(request, 'admin/products_list.html', context)


@admin_required
def admin_orders_list(request):
    """List all orders (view only) - NEW system"""
    orders = SupplierOrder.objects.select_related(
        'store_owner', 'supplier_product', 'supplier_product__supplier'
    ).order_by('-created_at')
    
    # Filter by order status
    order_status = request.GET.get('order_status', '')
    if order_status:
        orders = orders.filter(order_status=order_status)
    
    # Filter by delivery status
    delivery_status = request.GET.get('delivery_status', '')
    if delivery_status:
        orders = orders.filter(delivery_status=delivery_status)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(store_owner__first_name__icontains=search) |
            Q(supplier_product__name__icontains=search) |
            Q(supplier_product__supplier__username__icontains=search)
        )
    
    # Stats
    total_orders = SupplierOrder.objects.count()
    pending_orders = SupplierOrder.objects.filter(order_status='pending').count()
    completed_orders = SupplierOrder.objects.filter(order_status='completed').count()
    delivered_orders = SupplierOrder.objects.filter(delivery_status='delivered').count()
    
    context = {
        'orders': orders,
        'order_status': order_status,
        'delivery_status': delivery_status,
        'search': search,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'delivered_orders': delivered_orders,
        'order_status_choices': SupplierOrder.ORDER_STATUS_CHOICES,
        'delivery_status_choices': SupplierOrder.DELIVERY_STATUS_CHOICES,
    }
    return render(request, 'admin/orders_list.html', context)


@admin_required
def admin_order_detail(request, order_id):
    """View order details (view only) - NEW system"""
    order = get_object_or_404(
        SupplierOrder.objects.select_related('supplier_product', 'supplier_product__supplier', 'store_owner'),
        id=order_id
    )
    
    context = {
        'order': order,
    }
    return render(request, 'admin/order_detail.html', context)


@admin_required
def admin_activity_logs(request):
    """View all user activity logs"""
    logs = ActivityLog.objects.select_related('user').all()
    
    # Filter by user role
    role = request.GET.get('role', '')
    if role == 'owner':
        logs = logs.filter(user__profile__role='owner')
    elif role == 'supplier':
        logs = logs.filter(user__profile__role='supplier')
    elif role == 'staff':
        logs = logs.filter(user__profile__role='staff')
    elif role == 'admin':
        logs = logs.filter(user__is_superuser=True)
    
    # Filter by action
    action = request.GET.get('action', '')
    if action:
        logs = logs.filter(action=action)
    
    # Search by user
    search = request.GET.get('search', '')
    if search:
        logs = logs.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(description__icontains=search)
        )
    
    context = {
        'logs': logs[:100],  # Limit to 100 recent logs
        'role': role,
        'action': action,
        'search': search,
        'action_choices': ActivityLog.ACTION_CHOICES,
    }
    return render(request, 'admin/activity_logs.html', context)


@admin_required
def admin_staff_list(request):
    """List all staff members"""
    staff_members = UserProfile.objects.filter(role='staff').select_related('user', 'owner')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        staff_members = staff_members.filter(
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(owner__username__icontains=search)
        )
    
    # Filter by status
    status = request.GET.get('status', '')
    if status == 'active':
        staff_members = staff_members.filter(is_active=True)
    elif status == 'inactive':
        staff_members = staff_members.filter(is_active=False)
    
    context = {
        'staff_members': staff_members,
        'search': search,
        'status': status,
    }
    return render(request, 'admin/staff_list.html', context)


@admin_required
def admin_staff_detail(request, user_id):
    """View staff member details"""
    staff_user = get_object_or_404(User, id=user_id, profile__role='staff')
    staff_profile = staff_user.profile
    
    # Get staff activity logs
    recent_activities = ActivityLog.objects.filter(user=staff_user).order_by('-timestamp')[:20]
    
    context = {
        'staff_user': staff_user,
        'staff_profile': staff_profile,
        'recent_activities': recent_activities,
    }
    return render(request, 'admin/staff_detail.html', context)


@admin_required
def admin_staff_create(request, owner_id):
    """Create a staff account for a specific owner"""
    owner = get_object_or_404(User, id=owner_id, profile__role='owner')
    
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            staff_user = form.save(commit=False)
            staff_user.save()
            
            # Create staff profile linked to this owner
            UserProfile.objects.create(
                user=staff_user,
                role='staff',
                owner=owner,
                phone=form.cleaned_data.get('phone', ''),
                is_active=True
            )
            
            log_activity(
                request.user,
                'create',
                f'Admin created staff account: {staff_user.username} for owner: {owner.username}',
                request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Staff account "{staff_user.username}" created successfully!')
            return redirect('admin_owner_detail', user_id=owner.id)
    else:
        form = StaffCreateForm()
    
    context = {
        'form': form,
        'owner': owner,
    }
    return render(request, 'admin/staff_create.html', context)


@admin_required
def admin_staff_edit(request, user_id):
    """Edit an existing staff account"""
    staff_user = get_object_or_404(User, id=user_id, profile__role='staff')
    
    if request.method == 'POST':
        # Update user fields
        staff_user.first_name = request.POST.get('first_name', '')
        staff_user.last_name = request.POST.get('last_name', '')
        staff_user.email = request.POST.get('email', '')
        staff_user.save()
        
        # Update profile fields
        profile = staff_user.profile
        profile.phone = request.POST.get('phone', '')
        profile.is_active = request.POST.get('is_active') == 'on'
        profile.save()
        
        log_activity(
            request.user,
            'update',
            f'Admin updated staff account: {staff_user.username}',
            request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f'Staff account "{staff_user.username}" updated successfully!')
        return redirect('admin_staff_detail', user_id=staff_user.id)
    
    context = {
        'staff_user': staff_user,
    }
    return render(request, 'admin/staff_edit.html', context)


@admin_required
def admin_staff_delete(request, user_id):
    """Delete a staff account"""
    staff_user = get_object_or_404(User, id=user_id, profile__role='staff')
    owner = staff_user.profile.owner
    
    if request.method == 'POST':
        username = staff_user.username
        log_activity(
            request.user,
            'delete',
            f'Admin deleted staff account: {username}',
            request.META.get('REMOTE_ADDR')
        )
        staff_user.delete()
        messages.success(request, f'Staff account "{username}" deleted successfully!')
        
        # Redirect to owner detail if owner exists, otherwise to staff list
        if owner:
            return redirect('admin_owner_detail', user_id=owner.id)
        return redirect('admin_staff_list')
    
    context = {
        'staff_user': staff_user,
    }
    return render(request, 'admin/staff_delete.html', context)


# ✅ User Approval Management Views

@admin_required
def admin_pending_users(request):
    """List all pending user registrations"""
    pending_users = UserProfile.objects.filter(is_approved=False).select_related('user')
    
    context = {
        'pending_users': pending_users,
    }
    return render(request, 'admin/pending_users.html', context)


@admin_required
def admin_user_approval_detail(request, user_id):
    """View details of a pending user and approve/reject"""
    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(UserProfile, user=user, is_approved=False)
    
    # Get role-specific profile
    business_owner_profile = None
    supplier_profile = None
    
    if profile.role == 'owner':
        try:
            business_owner_profile = BusinessOwnerProfile.objects.get(user=user)
        except BusinessOwnerProfile.DoesNotExist:
            pass
    elif profile.role == 'supplier':
        try:
            supplier_profile = SupplierProfile.objects.get(user=user)
        except SupplierProfile.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = UserApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            
            if action == 'approve':
                # Approve the user
                profile.is_approved = True
                profile.approved_by = request.user
                profile.approved_at = timezone.now()
                profile.save()
                
                # Activate the user account
                user.is_active = True
                user.save()
                
                # Log the activity
                log_activity(
                    request.user,
                    'order_approved',
                    f'Admin approved user registration: {user.username} ({profile.role})',
                    request.META.get('REMOTE_ADDR')
                )
                
                # Send approval email (we'll implement this in the next step)
                from .email_notifications import send_user_approval_email
                send_user_approval_email(user, approved=True)
                
                messages.success(request, f'User {user.username} has been approved successfully!')
                return redirect('admin_pending_users')
                
            elif action == 'reject':
                # Reject the user
                rejection_reason = form.cleaned_data['rejection_reason']
                profile.rejection_reason = rejection_reason
                profile.save()
                
                # Log the activity
                log_activity(
                    request.user,
                    'order_rejected',
                    f'Admin rejected user registration: {user.username} ({profile.role}) - Reason: {rejection_reason}',
                    request.META.get('REMOTE_ADDR')
                )
                
                # Send rejection email
                from .email_notifications import send_user_approval_email
                send_user_approval_email(user, approved=False, rejection_reason=rejection_reason)
                
                messages.warning(request, f'User {user.username} has been rejected.')
                return redirect('admin_pending_users')
    else:
        form = UserApprovalForm()
    
    context = {
        'user': user,
        'profile': profile,
        'business_owner_profile': business_owner_profile,
        'supplier_profile': supplier_profile,
        'form': form,
    }
    return render(request, 'admin/user_approval_detail.html', context)


@admin_required
def admin_approved_users(request):
    """List all approved users"""
    approved_users = UserProfile.objects.filter(is_approved=True).select_related('user', 'approved_by')
    
    context = {
        'approved_users': approved_users,
    }
    return render(request, 'admin/approved_users.html', context)
