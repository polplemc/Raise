# Appendices: Raise Supply Chain Management Platform

## Table of Contents
1. [Source Code Snippets](#1-source-code-snippets)
2. [Database Schema](#2-database-schema)
3. [API Endpoints Reference](#3-api-endpoints-reference)
4. [Testing Documentation](#4-testing-documentation)
5. [Configuration Files](#5-configuration-files)
6. [Deployment Guide](#6-deployment-guide)
7. [Security & Compliance](#7-security--compliance)
8. [Developer Information](#8-developer-information)
9. [Troubleshooting Guide](#9-troubleshooting-guide)
10. [Raw Data Samples](#10-raw-data-samples)

---

## 1. Source Code Snippets

### 1.1 User Authentication Model
```python
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('supplier', 'Supplier'),
        ('owner', 'Rural Store Owner'),
        ('staff', 'Staff Member'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 1.2 Order Management Model
```python
class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    supplier_profile = models.ForeignKey(SupplierProfile, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 1.3 Payment Processing Model
```python
class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### 1.4 Notification System Model
```python
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('order', 'Order Update'),
        ('payment', 'Payment Update'),
        ('connection', 'Connection Request'),
        ('approval', 'Account Approval'),
        ('message', 'New Message'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
```

### 1.5 Login View with Role-Based Redirect
```python
def login_page(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Check approval status
            if hasattr(user, 'profile') and not user.profile.is_approved and not user.is_superuser:
                messages.error(request, "Your account is pending admin approval.")
                return redirect('login')
            
            login(request, user)
            
            # Role-based redirect
            if user.is_superuser:
                return redirect('admin_dashboard')
            elif user.profile.role == 'supplier':
                return redirect('supplier_dashboard')
            elif user.profile.role == 'owner':
                return redirect('owner_dashboard')
            elif user.profile.role == 'staff':
                return redirect('staff_dashboard')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})
```

---

## 2. Database Schema

### 2.1 Core Tables

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| auth_user | Django authentication | id, username, email, password |
| myapp_userprofile | User roles & profiles | user_id, role, is_approved |
| myapp_supplierprofile | Supplier business info | user_id, business_name, products_supplied |
| myapp_inventory | Store inventory | owner_id, product_name, quantity |
| myapp_supplierproduct | Products for sale | supplier_profile_id, name, price, stock |
| myapp_order | Purchase orders | owner_id, supplier_profile_id, status |
| myapp_orderitem | Order line items | order_id, product_id, quantity |
| myapp_payment | Payment records | order_id, amount, status, verified_by |
| myapp_notification | User notifications | user_id, notification_type, is_read |
| myapp_connectionrequest | Supplier connections | owner_id, supplier_profile_id, status |
| myapp_activitylog | System audit logs | user_id, action, ip_address |

### 2.2 Relationships
- User → UserProfile (1:1)
- User → SupplierProfile (1:1)
- UserProfile → Inventory (1:N)
- SupplierProfile → SupplierProduct (1:N)
- SupplierProfile → Order (1:N)
- Order → OrderItem (1:N)
- Order → Payment (1:1)
- User → Notification (1:N)

---

## 3. API Endpoints Reference

### 3.1 Authentication
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Landing page |
| POST | `/signup/` | User registration |
| POST | `/login/` | User login |
| GET | `/logout/` | User logout |

### 3.2 Admin Routes
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/sysadmin/dashboard/` | Admin dashboard |
| GET | `/sysadmin/pending-users/` | Pending approvals |
| GET | `/sysadmin/owners/` | List owners |
| GET | `/sysadmin/suppliers/` | List suppliers |
| GET | `/sysadmin/orders/` | View all orders |
| GET | `/sysadmin/logs/` | Activity logs |

### 3.3 Owner Routes
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/owner/dashboard/` | Owner dashboard |
| GET | `/owner/inventory/` | View inventory |
| GET | `/owner/browse-products/` | Browse products |
| POST | `/owner/supplier-orders/` | Place order |
| GET | `/owner/staff/` | Manage staff |
| GET | `/owner/search-suppliers/` | Search suppliers |

### 3.4 Supplier Routes
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/supplier/dashboard/` | Supplier dashboard |
| GET | `/supplier/products/` | View products |
| POST | `/supplier/products/add/` | Add product |
| GET | `/supplier/orders/` | View orders |
| GET | `/supplier/buyers/` | View buyers |
| GET | `/supplier/connection-requests/` | Connection requests |

### 3.5 Staff Routes
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/staff/dashboard/` | Staff dashboard |
| GET | `/staff/inventory/` | View inventory |
| GET | `/staff/stock-out/` | Report stock out |
| GET | `/staff/supplier-orders/` | View orders |

### 3.6 Notification Routes
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/notifications/` | List notifications |
| POST | `/notifications/<id>/read/` | Mark as read |
| DELETE | `/notifications/<id>/delete/` | Delete notification |
| GET | `/api/notifications/` | Get JSON notifications |

---

## 4. Testing Documentation

### 4.1 Unit Test Example
```python
from django.test import TestCase
from django.contrib.auth.models import User
from myapp.models import UserProfile, Order

class UserRegistrationTest(TestCase):
    def test_user_registration(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        profile = UserProfile.objects.create(
            user=user,
            role='owner'
        )
        self.assertEqual(profile.role, 'owner')
        self.assertFalse(profile.is_approved)
```

### 4.2 Integration Test Example
```python
class OrderFlowTest(TestCase):
    def test_complete_order_flow(self):
        owner = User.objects.create_user(username='owner', password='pass')
        supplier = User.objects.create_user(username='supplier', password='pass')
        
        order = Order.objects.create(
            owner=owner,
            order_number='ORD-001',
            total_amount=100.00
        )
        
        self.assertEqual(order.status, 'pending')
        order.status = 'completed'
        order.save()
        self.assertEqual(order.status, 'completed')
```

### 4.3 Test Commands
```bash
# Run all tests
python manage.py test

# Run specific test class
python manage.py test myapp.tests.UserRegistrationTest

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

---

## 5. Configuration Files

### 5.1 Requirements.txt
```
Django==5.2.7
openpyxl==3.1.2
xhtml2pdf==0.2.13
reportlab==4.0.7
Pillow
whitenoise
gunicorn
dj-database-url
psycopg2-binary
```

### 5.2 Django Settings Essentials
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myapp',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
```

---

## 6. Deployment Guide

### 6.1 Local Development Setup
```bash
# Create virtual environment
python -m venv myenv

# Activate environment
myenv\Scripts\activate  # Windows
source myenv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### 6.2 Production Deployment
```bash
# Collect static files
python manage.py collectstatic --noinput

# Run with gunicorn
gunicorn myproject.wsgi:application --bind 0.0.0.0:8000

# Use environment variables for sensitive data
export SECRET_KEY='your-secret-key'
export DEBUG=False
export ALLOWED_HOSTS='yourdomain.com'
```

---

## 7. Security & Compliance

### 7.1 Security Measures Implemented
- **Authentication**: Django's built-in user authentication system
- **Authorization**: Role-based access control (RBAC)
- **Password Security**: Django password validators
- **CSRF Protection**: Django CSRF middleware
- **SQL Injection Prevention**: Django ORM parameterized queries
- **Session Management**: Secure session handling
- **Activity Logging**: All user actions logged for audit trail

### 7.2 Data Protection
- User data encrypted in transit (HTTPS)
- Sensitive fields validated before storage
- Payment information handled securely
- Business documents uploaded with validation

### 7.3 Compliance Checklist
- [ ] GDPR compliance for user data
- [ ] Data retention policies implemented
- [ ] User consent mechanisms in place
- [ ] Privacy policy published
- [ ] Terms of service established
- [ ] Incident response plan documented

---

## 8. Developer Information

### 8.1 Development Team Structure
- **Backend Developer**: Django/Python development
- **Frontend Developer**: HTML/CSS/JavaScript templates
- **Database Administrator**: Database design and optimization
- **QA Engineer**: Testing and quality assurance
- **DevOps Engineer**: Deployment and infrastructure

### 8.2 Development Standards
- Follow PEP 8 Python style guide
- Use meaningful variable and function names
- Add docstrings to all functions
- Write unit tests for new features
- Use version control (Git) for all code
- Code review before merging to main branch

### 8.3 Project Structure
```
Raise/
├── myproject/          # Django project settings
├── myapp/              # Main application
│   ├── models.py       # Database models
│   ├── views.py        # View logic
│   ├── urls.py         # URL routing
│   ├── forms.py        # Form definitions
│   ├── templates/      # HTML templates
│   └── static/         # CSS, JS, images
├── requirements.txt    # Python dependencies
├── manage.py           # Django management
└── db.sqlite3          # SQLite database
```

---

## 9. Troubleshooting Guide

### 9.1 Common Issues

**Issue**: User cannot login after registration
- **Solution**: Check if user is approved in admin panel. Unapproved users cannot login.

**Issue**: Order not appearing in supplier dashboard
- **Solution**: Verify supplier connection is accepted. Orders only show for connected suppliers.

**Issue**: Payment verification fails
- **Solution**: Ensure payment reference number matches order. Check payment method is supported.

**Issue**: Static files not loading in production
- **Solution**: Run `python manage.py collectstatic` and configure web server to serve static files.

**Issue**: Database migration errors
- **Solution**: Delete migrations folder (except __init__.py) and run `python manage.py makemigrations` and `python manage.py migrate`.

### 9.2 Debug Mode
```python
# Enable debug logging in settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

---

## 10. Raw Data Samples

### 10.1 Sample User Registration Data
```json
{
  "username": "john_supplier",
  "email": "john@supplier.com",
  "password": "SecurePass123!",
  "role": "supplier",
  "phone": "+63912345678",
  "business_name": "John's Wholesale",
  "contact_person": "John Doe",
  "address": "123 Business St, Manila"
}
```

### 10.2 Sample Order Data
```json
{
  "order_number": "ORD-20251123-001",
  "owner_id": 5,
  "supplier_profile_id": 3,
  "items": [
    {
      "product_id": 12,
      "quantity": 50,
      "unit_price": 25.00
    },
    {
      "product_id": 15,
      "quantity": 30,
      "unit_price": 15.00
    }
  ],
  "total_amount": 1700.00,
  "payment_method": "gcash",
  "delivery_address": "456 Store Ave, Quezon City"
}
```

### 10.3 Sample Product Data
```json
{
  "name": "Premium Rice 25kg",
  "description": "High quality white rice",
  "price": 1200.00,
  "unit": "bag",
  "stock_quantity": 100,
  "manufactured_date": "2025-11-01",
  "expiration_date": "2026-11-01",
  "supplier_profile_id": 3
}
```

### 10.4 Sample Payment Data
```json
{
  "order_id": 42,
  "amount": 1700.00,
  "payment_method": "gcash",
  "reference_number": "GCH-20251123-5678",
  "status": "verified",
  "verified_by_id": 3,
  "verified_at": "2025-11-23T14:30:00Z"
}
```

---

## Document Information

**Document Version**: 1.0  
**Last Updated**: November 23, 2025  
**Platform**: Raise Supply Chain Management System  
**Technology Stack**: Django 5.2.7, Python 3.x, PostgreSQL/SQLite  
**Status**: Complete

---

*This appendices document provides supplementary material for the Raise platform documentation. For additional information, refer to the main system documentation and API reference guides.*
