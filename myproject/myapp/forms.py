from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    UserProfile, Supplier, Product, OrderItem, StockOut, Inventory, 
    SupplierProduct, SupplierOrder, StockMovement, SupplierPaymentInfo,
    Message, Notification, BusinessOwnerProfile, SupplierProfile,
    PAYMENT_METHOD_CHOICES, PAYMENT_STATUS_CHOICES
)


# ✅ Comprehensive Signup Form with Admin Approval
class SignUpForm(forms.Form):
    # Basic user information
    full_name = forms.CharField(max_length=100, required=True, label="Full Name")
    email = forms.EmailField(required=True, label="Email Address")
    username = forms.CharField(max_length=150, required=True, label="Username")
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True, label="Confirm Password")
    
    # Contact information
    phone = forms.CharField(max_length=15, required=True, label="Contact Number")
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True, label="Address")
    
    # Role selection - exclude 'staff' role from signup
    role = forms.ChoiceField(
        choices=[choice for choice in UserProfile.ROLE_CHOICES if choice[0] != 'staff'],
        required=True,
        label="Register As",
        widget=forms.RadioSelect
    )
    
    # Business Owner specific fields
    store_name = forms.CharField(max_length=200, required=False, label="Store/Business Name")
    store_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, 
                                  label="Store Address/Location")
    store_type = forms.ChoiceField(choices=BusinessOwnerProfile.STORE_TYPE_CHOICES, required=False,
                                 label="Type of Store")
    owner_contact_person = forms.CharField(max_length=200, required=False, label="Primary Contact Person")
    owner_contact_phone = forms.CharField(max_length=15, required=False, label="Store Contact Number")
    owner_contact_email = forms.EmailField(required=False, label="Store Contact Email")
    owner_business_permit = forms.FileField(required=False, label="Business Permit/Proof of Registration",
                                          help_text="Upload your business permit or registration document (optional)")
    
    # Supplier specific fields
    supplier_business_name = forms.CharField(max_length=200, required=False, label="Company/Supplier Name")
    supplier_contact_person = forms.CharField(max_length=200, required=False, label="Contact Person")
    supplier_email = forms.EmailField(required=False, label="Business Email")
    supplier_phone = forms.CharField(max_length=15, required=False, label="Business Phone")
    products_supplied = forms.ChoiceField(choices=SupplierProfile.PRODUCT_TYPE_CHOICES, required=False,
                                        label="Type of Products Supplied")
    business_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False,
                                     label="Business Address")
    supplier_business_permit = forms.FileField(required=False, label="Business Permit/Certificate",
                                             help_text="Upload your business permit or certificate (optional)")
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        role = cleaned_data.get('role')
        
        # Validate password confirmation
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        # Validate role-specific required fields
        if role == 'owner':
            required_owner_fields = ['store_name', 'store_address', 'store_type', 
                                   'owner_contact_person', 'owner_contact_phone', 'owner_contact_email']
            for field in required_owner_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, "This field is required for Business Owners.")
        
        elif role == 'supplier':
            required_supplier_fields = ['supplier_business_name', 'supplier_contact_person', 
                                      'supplier_email', 'supplier_phone', 'products_supplied', 'business_address']
            for field in required_supplier_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, "This field is required for Suppliers.")
        
        return cleaned_data
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username
    
    def save(self, commit=True):
        cleaned_data = self.cleaned_data
        
        # Create user account with is_active=False (pending approval)
        user = User(
            username=cleaned_data['username'],
            email=cleaned_data['email'],
            first_name=cleaned_data['full_name'],
            is_active=False  # User cannot login until approved
        )
        user.set_password(cleaned_data['password'])
        
        if commit:
            user.save()
            
            # Create UserProfile with approval fields
            profile = UserProfile.objects.create(
                user=user,
                role=cleaned_data['role'],
                phone=cleaned_data['phone'],
                address=cleaned_data['address'],
                is_approved=False  # Pending admin approval
            )
            
            # Create role-specific profile
            if cleaned_data['role'] == 'owner':
                BusinessOwnerProfile.objects.create(
                    user=user,
                    store_name=cleaned_data['store_name'],
                    store_address=cleaned_data['store_address'],
                    store_type=cleaned_data['store_type'],
                    contact_person=cleaned_data['owner_contact_person'],
                    contact_phone=cleaned_data['owner_contact_phone'],
                    contact_email=cleaned_data['owner_contact_email'],
                    business_permit=cleaned_data.get('owner_business_permit')
                )
            
            elif cleaned_data['role'] == 'supplier':
                SupplierProfile.objects.create(
                    user=user,
                    business_name=cleaned_data['supplier_business_name'],
                    contact_person=cleaned_data['supplier_contact_person'],
                    email=cleaned_data['supplier_email'],
                    phone=cleaned_data['supplier_phone'],
                    address=cleaned_data['address'],
                    products_supplied=cleaned_data['products_supplied'],
                    business_address=cleaned_data['business_address'],
                    business_permit=cleaned_data.get('supplier_business_permit')
                )
        
        return user


# ✅ Login Form
class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'autofocus': True}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


# Profile Form
class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, required=True, label="Full Name")
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = UserProfile
        fields = ['phone', 'address', 'store_name']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.email = self.cleaned_data['email']
            self.user.username = self.cleaned_data['email']
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile


# Supplier Form
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }


# Add to Cart Form
class AddToCartForm(forms.Form):
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(min_value=1, initial=1, label="Quantity")


# Stock Out Form
class StockOutForm(forms.ModelForm):
    class Meta:
        model = StockOut
        fields = ['product', 'quantity', 'reason', 'remarks']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes about this stock out...'}),
        }
        labels = {
            'product': 'Product',
            'quantity': 'Quantity Sold/Used',
            'reason': 'Reason',
            'remarks': 'Remarks (Optional)',
        }
    
    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        
        # Only show products that the owner has in inventory
        if self.owner:
            inventory_products = Inventory.objects.filter(
                owner=self.owner, 
                quantity__gt=0
            ).values_list('product', flat=True)
            
            self.fields['product'].queryset = Product.objects.filter(
                id__in=inventory_products
            ).order_by('name')
            
            # Add current stock info to product choices
            choices = []
            for product in self.fields['product'].queryset:
                try:
                    inventory = Inventory.objects.get(owner=self.owner, product=product)
                    stock_info = f" (Stock: {inventory.quantity} {product.unit})"
                    choices.append((product.id, f"{product.name}{stock_info}"))
                except Inventory.DoesNotExist:
                    choices.append((product.id, product.name))
            
            self.fields['product'].choices = [('', '--- Select Product ---')] + choices
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if product and quantity and self.owner:
            try:
                inventory = Inventory.objects.get(owner=self.owner, product=product)
                if quantity > inventory.quantity:
                    raise forms.ValidationError(
                        f"Cannot sell/use {quantity} {product.unit}. "
                        f"Only {inventory.quantity} {product.unit} available in stock."
                    )
            except Inventory.DoesNotExist:
                raise forms.ValidationError(f"Product '{product.name}' not found in your inventory.")
        
        return cleaned_data


# Supplier Product Form
class SupplierProductForm(forms.ModelForm):
    class Meta:
        model = SupplierProduct
        fields = ['name', 'category', 'description', 'unit_price', 'available_stock', 'minimum_order_quantity', 'unit', 'manufactured_date', 'expiration_date', 'low_stock_threshold', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Product description...'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'available_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'minimum_order_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'manufactured_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Product Name',
            'category': 'Product Category',
            'description': 'Description',
            'unit_price': 'Unit Price (₱)',
            'available_stock': 'Available Stock',
            'minimum_order_quantity': 'Minimum Order Quantity',
            'unit': 'Unit of Measurement',
            'manufactured_date': 'Manufactured Date',
            'expiration_date': 'Expiration Date',
            'low_stock_threshold': 'Low Stock Alert Threshold',
            'is_active': 'Active Product',
        }

    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price and unit_price <= 0:
            raise forms.ValidationError("Unit price must be greater than 0.")
        return unit_price
    
    def clean(self):
        cleaned_data = super().clean()
        manufactured_date = cleaned_data.get('manufactured_date')
        expiration_date = cleaned_data.get('expiration_date')
        
        # Validate that expiration date is after manufactured date
        if manufactured_date and expiration_date:
            if expiration_date <= manufactured_date:
                self.add_error('expiration_date', "Expiration date must be after the manufactured date.")
        
        # Validate that manufactured date is not in the future
        if manufactured_date:
            from django.utils import timezone
            today = timezone.now().date()
            if manufactured_date > today:
                self.add_error('manufactured_date', "Manufactured date cannot be in the future.")
        
        return cleaned_data
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check for duplicate product name for the same supplier
            # We need to get the supplier from the view context, but since we can't access it here,
            # we'll handle this in the view instead
            pass
        return name

    def clean_minimum_order_quantity(self):
        min_qty = self.cleaned_data.get('minimum_order_quantity')
        if min_qty and min_qty <= 0:
            raise forms.ValidationError("Minimum order quantity must be at least 1.")
        return min_qty


# Stock Restock Form
class RestockForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        label='Quantity to Add'
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes about this restock...'}),
        label='Notes (Optional)'
    )


# Store Owner Order Form (for placing orders to suppliers)
class PlaceOrderForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        label='Quantity'
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Payment Method',
        initial='cod'
    )
    payment_status = forms.ChoiceField(
        choices=PAYMENT_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Payment Status',
        initial='pending'
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes for the supplier...'}),
        label='Notes (Optional)'
    )

    def __init__(self, *args, **kwargs):
        self.supplier_product = kwargs.pop('supplier_product', None)
        super().__init__(*args, **kwargs)
        
        if self.supplier_product:
            self.fields['quantity'].widget.attrs['max'] = self.supplier_product.available_stock
            self.fields['quantity'].help_text = f"Available: {self.supplier_product.available_stock} {self.supplier_product.unit}"

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if self.supplier_product:
            if quantity < self.supplier_product.minimum_order_quantity:
                raise forms.ValidationError(
                    f"Minimum order quantity is {self.supplier_product.minimum_order_quantity} {self.supplier_product.unit}"
                )
            if quantity > self.supplier_product.available_stock:
                raise forms.ValidationError(
                    f"Only {self.supplier_product.available_stock} {self.supplier_product.unit} available in stock"
                )
        return quantity


# ========== OWNER MANAGEMENT FORMS (FOR ADMIN) ==========

class OwnerCreateForm(forms.ModelForm):
    """Form for admin to create new owner accounts"""
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        required=True
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    store_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Store Name'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        
        if commit:
            user.save()
            # Create owner profile
            UserProfile.objects.create(
                user=user,
                role='owner',
                store_name=self.cleaned_data.get('store_name', ''),
                phone=self.cleaned_data.get('phone', ''),
                address=self.cleaned_data.get('address', ''),
                is_active=True
            )
        return user


class OwnerEditForm(forms.ModelForm):
    """Form for admin to edit existing owner accounts"""
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    store_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Store Name'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3})
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['store_name'].initial = self.instance.profile.store_name
            self.fields['phone'].initial = self.instance.profile.phone
            self.fields['address'].initial = self.instance.profile.address
            self.fields['is_active'].initial = self.instance.profile.is_active
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        
        if commit and hasattr(user, 'profile'):
            profile = user.profile
            profile.store_name = self.cleaned_data.get('store_name', '')
            profile.phone = self.cleaned_data.get('phone', '')
            profile.address = self.cleaned_data.get('address', '')
            profile.is_active = self.cleaned_data.get('is_active', True)
            profile.save()
        
        return user


# ========== SUPPLIER MANAGEMENT FORMS (FOR ADMIN) ==========

class SupplierCreateForm(forms.ModelForm):
    """Form for admin to create new supplier accounts"""
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        required=True
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        
        if commit:
            user.save()
            # Create supplier profile
            UserProfile.objects.create(
                user=user,
                role='supplier',
                phone=self.cleaned_data.get('phone', ''),
                address=self.cleaned_data.get('address', ''),
                is_active=True
            )
        return user


class SupplierEditForm(forms.ModelForm):
    """Form for admin to edit existing supplier accounts"""
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3})
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['phone'].initial = self.instance.profile.phone
            self.fields['address'].initial = self.instance.profile.address
            self.fields['is_active'].initial = self.instance.profile.is_active
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        
        if commit and hasattr(user, 'profile'):
            profile = user.profile
            profile.phone = self.cleaned_data.get('phone', '')
            profile.address = self.cleaned_data.get('address', '')
            profile.is_active = self.cleaned_data.get('is_active', True)
            profile.save()
        
        return user


# ========== STAFF MANAGEMENT FORMS ==========

class StaffCreateForm(forms.ModelForm):
    """Form for creating new staff members"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}),
        help_text="Username for login (must be unique)"
    )
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
        label="First Name"
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
        label="Last Name"
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
        label="Email Address"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
        label="Password",
        help_text="Password for the staff member to login"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        label="Confirm Password"
    )
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'address']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter address'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match.")
        return confirm_password

    def save(self, owner, commit=True):
        """Create user and staff profile linked to owner"""
        # Create the User
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data.get('email', ''),
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data.get('last_name', ''),
            password=self.cleaned_data['password']
        )
        
        # Create the UserProfile for staff
        if commit:
            profile = UserProfile.objects.create(
                user=user,
                role='staff',
                owner=owner,
                phone=self.cleaned_data.get('phone', ''),
                address=self.cleaned_data.get('address', ''),
                is_active=True
            )
            return profile
        return user


class StaffEditForm(forms.ModelForm):
    """Form for editing existing staff members"""
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="First Name"
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Last Name"
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label="Email Address"
    )
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'address', 'is_active']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': 'Account Active',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Update User fields
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data.get('last_name', '')
            user.email = self.cleaned_data.get('email', '')
            user.save()
            
            # Save profile
            profile.save()
        return profile


class StaffPasswordResetForm(forms.Form):
    """Form for resetting staff member password"""
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        label="Confirm Password"
    )

    def clean_confirm_password(self):
        password = self.cleaned_data.get('new_password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match.")
        return confirm_password


# ========== PAYMENT VERIFICATION FORMS ==========

class UpdatePaymentStatusForm(forms.ModelForm):
    """Form for owners to update payment status on their orders"""
    class Meta:
        model = SupplierOrder
        fields = ['payment_status']
        widgets = {
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'payment_status': 'Payment Status',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only allow setting to 'paid' or 'pending', not 'failed' during normal updates
        self.fields['payment_status'].choices = [
            ('pending', 'Pending'),
            ('paid', 'Paid'),
        ]


class VerifyPaymentForm(forms.Form):
    """Form for suppliers to verify they received payment"""
    confirm = forms.BooleanField(
        required=True,
        label="I confirm that I have received this payment",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    verification_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'Optional: Add any notes about this payment verification...'
        }),
        label='Verification Notes (Optional)'
    )


# ========== SUPPLIER PAYMENT INFORMATION FORM ==========

class SupplierPaymentInfoForm(forms.ModelForm):
    """Form for suppliers to manage their payment receiving information"""
    
    class Meta:
        model = SupplierPaymentInfo
        fields = [
            'gcash_number', 'gcash_account_name',
            'paymaya_number', 'paymaya_account_name',
            'bank_name', 'bank_account_name', 'bank_account_number',
            'payment_notes'
        ]
        widgets = {
            'gcash_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '09XX XXX XXXX'
            }),
            'gcash_account_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name as registered in GCash'
            }),
            'paymaya_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '09XX XXX XXXX'
            }),
            'paymaya_account_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name as registered in PayMaya'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., BDO, BPI, Metrobank'
            }),
            'bank_account_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account holder name'
            }),
            'bank_account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank account number'
            }),
            'payment_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional payment instructions (e.g., branch location, reference format)...'
            }),
        }
        labels = {
            'gcash_number': 'GCash Mobile Number',
            'gcash_account_name': 'GCash Account Name',
            'paymaya_number': 'PayMaya Mobile Number',
            'paymaya_account_name': 'PayMaya Account Name',
            'bank_name': 'Bank Name',
            'bank_account_name': 'Bank Account Name',
            'bank_account_number': 'Bank Account Number',
            'payment_notes': 'Additional Payment Instructions (Optional)',
        }
        help_texts = {
            'gcash_number': 'Enter your GCash-registered mobile number',
            'paymaya_number': 'Enter your PayMaya-registered mobile number',
            'bank_account_number': 'Enter your complete bank account number',
            'payment_notes': 'Add any special instructions for store owners sending payments',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # At least one payment method should be provided
        has_gcash = cleaned_data.get('gcash_number')
        has_paymaya = cleaned_data.get('paymaya_number')
        has_bank = cleaned_data.get('bank_name') and cleaned_data.get('bank_account_number')
        
        if not (has_gcash or has_paymaya or has_bank):
            raise forms.ValidationError(
                'Please provide at least one payment method (GCash, PayMaya, or Bank Transfer).'
            )
        
        # If GCash number is provided, account name should be provided too
        if has_gcash and not cleaned_data.get('gcash_account_name'):
            self.add_error('gcash_account_name', 'Please provide the account name for GCash.')
        
        # If PayMaya number is provided, account name should be provided too
        if has_paymaya and not cleaned_data.get('paymaya_account_name'):
            self.add_error('paymaya_account_name', 'Please provide the account name for PayMaya.')
        
        # If bank details are provided, all bank fields should be complete
        if cleaned_data.get('bank_name') or cleaned_data.get('bank_account_number') or cleaned_data.get('bank_account_name'):
            if not cleaned_data.get('bank_name'):
                self.add_error('bank_name', 'Bank name is required for bank transfer.')
            if not cleaned_data.get('bank_account_number'):
                self.add_error('bank_account_number', 'Account number is required for bank transfer.')
            if not cleaned_data.get('bank_account_name'):
                self.add_error('bank_account_name', 'Account name is required for bank transfer.')
        
        return cleaned_data


# Order Status Update Form (for suppliers)
class OrderStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = SupplierOrder
        fields = ['order_status']
        widgets = {
            'order_status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'order_status': 'Order Status',
        }
        help_texts = {
            'order_status': 'Update the current stage of this order',
        }


# Delivery Status Update Form (for suppliers)
class DeliveryStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = SupplierOrder
        fields = ['delivery_status']
        widgets = {
            'delivery_status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'delivery_status': 'Delivery Status',
        }
        help_texts = {
            'delivery_status': 'Update the current delivery/shipment stage',
        }


# Combined Status Update Form (for suppliers)
class CombinedStatusUpdateForm(forms.ModelForm):
    status_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes about this status update...'
        }),
        label='Status Update Notes',
        help_text='Add any relevant information about this status change'
    )
    
    class Meta:
        model = SupplierOrder
        fields = ['order_status', 'delivery_status']
        widgets = {
            'order_status': forms.Select(attrs={'class': 'form-select'}),
            'delivery_status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'order_status': 'Order Status',
            'delivery_status': 'Delivery Status',
        }
        help_texts = {
            'order_status': 'Current stage of the order transaction',
            'delivery_status': 'Current stage of the delivery/shipment',
        }


# Message Form
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Type your message here...'
            }),
        }
        labels = {
            'body': 'Message',
        }


# Quick Message Form (for order-specific messages)
class QuickMessageForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Send a message about this order...'
        }),
        label='',
        max_length=1000
    )


# ✅ Admin User Approval Form
class UserApprovalForm(forms.Form):
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.RadioSelect, required=True)
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Provide reason for rejection...'}),
        required=False,
        label="Rejection Reason",
        help_text="Required if rejecting the user"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if action == 'reject' and not rejection_reason:
            self.add_error('rejection_reason', 'Rejection reason is required when rejecting a user.')
        
        return cleaned_data
