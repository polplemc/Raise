from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import SignUpForm, LoginForm
from .models import UserProfile, ActivityLog


def landing_page(request):
    return render(request, 'landing.html')


# ✅ Signup View with Admin Approval (using comprehensive SignUpForm)
def signup_page(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Send admin notification about new user registration
            from .email_notifications import send_admin_new_user_notification
            send_admin_new_user_notification(user)
            
            messages.success(request, 
                "Your account has been created successfully! Your registration is pending admin approval. "
                "You'll receive an email once your account is approved.")
            return redirect('signup_confirmation')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})


# ✅ Signup Confirmation Page
def signup_confirmation(request):
    return render(request, 'signup_confirmation.html')


# ✅ Login View (with role-based redirect)
def login_page(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Check if user is approved before allowing login
            if hasattr(user, 'profile') and not user.profile.is_approved and not user.is_superuser:
                messages.error(request, "Your account is pending admin approval. Please wait for approval before logging in.")
                return redirect('login')
            
            login(request, user)
            
            # Log the login activity
            ActivityLog.objects.create(
                user=user,
                action='login',
                description=f'User logged in',
                ip_address=request.META.get('REMOTE_ADDR')
            )

            if user.is_superuser:
                return redirect('admin_dashboard')
            elif hasattr(user, 'profile'):
                if user.profile.role == 'supplier':
                    return redirect('supplier_dashboard')
                elif user.profile.role == 'owner':
                    return redirect('owner_dashboard')
                elif user.profile.role == 'staff':
                    # Check if staff account is active
                    if user.profile.is_active:
                        return redirect('staff_dashboard')
                    else:
                        logout(request)
                        messages.error(request, "Your staff account has been deactivated. Please contact your manager.")
                        return redirect('login')
            else:
                messages.error(request, "No role found for this user.")
                return redirect('login')
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


# Note: Dashboard views have been moved to their respective view files:
# - admin_views.py for admin_dashboard
# - supplier_views.py for supplier_dashboard  
# - owner_views.py for owner_dashboard

# Test view for Bootstrap
def test_bootstrap(request):
    return render(request, 'test_bootstrap.html')


# Custom logout view with activity logging
def logout_view(request):
    """Logout user and log the activity"""
    if request.user.is_authenticated:
        # Log the logout activity
        ActivityLog.objects.create(
            user=request.user,
            action='logout',
            description='User logged out',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        # Logout the user
        logout(request)
        messages.success(request, "You have been logged out successfully.")
    
    return redirect('landing')
