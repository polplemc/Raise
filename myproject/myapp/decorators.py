from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from functools import wraps


def role_required(allowed_roles):
    """
    Decorator that restricts access to users with specific roles.
    
    Usage:
    @role_required(['owner', 'staff'])
    def my_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not hasattr(request.user, 'profile'):
                messages.error(request, "Access denied. User profile not found.")
                return redirect('landing')
            
            user_role = request.user.profile.role
            if user_role not in allowed_roles:
                messages.error(request, f"Access denied. {user_role.title()} role not authorized.")
                return redirect('landing')
            
            # Check if staff user is active
            if user_role == 'staff' and not request.user.profile.is_active:
                messages.error(request, "Access denied. Your account has been deactivated.")
                return redirect('landing')
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def owner_required(view_func):
    """Decorator to ensure only business owners can access"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'owner':
            messages.error(request, "Access denied. Business owner account required.")
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """Decorator to ensure only staff members can access"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'staff':
            messages.error(request, "Access denied. Staff account required.")
            return redirect('landing')
        
        # Check if staff account is active
        if not request.user.profile.is_active:
            messages.error(request, "Access denied. Your account has been deactivated.")
            return redirect('landing')
            
        return view_func(request, *args, **kwargs)
    return wrapper


def owner_or_staff_required(view_func):
    """Decorator to ensure only owners or their staff can access"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile'):
            messages.error(request, "Access denied. User profile not found.")
            return redirect('landing')
        
        user_role = request.user.profile.role
        if user_role not in ['owner', 'staff']:
            messages.error(request, "Access denied. Owner or staff account required.")
            return redirect('landing')
        
        # Check if staff account is active
        if user_role == 'staff' and not request.user.profile.is_active:
            messages.error(request, "Access denied. Your account has been deactivated.")
            return redirect('landing')
            
        return view_func(request, *args, **kwargs)
    return wrapper


def supplier_required(view_func):
    """Decorator to ensure only suppliers can access"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'supplier':
            messages.error(request, "Access denied. Supplier account required.")
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_access_check(user, owner_user):
    """
    Helper function to check if a staff user can access data belonging to an owner.
    Returns True if access is allowed, False otherwise.
    """
    if not hasattr(user, 'profile'):
        return False
    
    profile = user.profile
    
    # Owner can access their own data
    if profile.role == 'owner' and user == owner_user:
        return True
    
    # Staff can access their owner's data
    if profile.role == 'staff' and profile.owner == owner_user and profile.is_active:
        return True
    
    return False


def get_business_owner_for_user(user):
    """
    Helper function to get the business owner for a user.
    Returns the owner User object or None.
    """
    if not hasattr(user, 'profile'):
        return None
    
    profile = user.profile
    
    if profile.role == 'owner':
        return user
    elif profile.role == 'staff' and profile.owner:
        return profile.owner
    
    return None
