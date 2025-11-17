from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Payment Method Choices - Used across multiple models
PAYMENT_METHOD_CHOICES = [
    ('cod', 'Cash on Delivery'),
    ('gcash', 'GCash'),
    ('paymaya', 'PayMaya'),
    ('bank_transfer', 'Bank Transfer'),
]

PAYMENT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('paid', 'Paid'),
    ('failed', 'Failed'),
]

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
    store_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Staff linking to owner
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='staff_members', 
                             null=True, blank=True, 
                             help_text="The business owner this staff member works for")
    is_active = models.BooleanField(default=True, help_text="Whether this user account is active")
    
    # Admin approval fields
    is_approved = models.BooleanField(default=False, help_text="Whether this user has been approved by admin")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='approved_users', help_text="Admin who approved this user")
    approved_at = models.DateTimeField(null=True, blank=True, help_text="When this user was approved")
    rejection_reason = models.TextField(blank=True, null=True, help_text="Reason for rejection if applicable")
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        if self.role == 'staff' and self.owner:
            return f"{self.user.username} - {self.role} (under {self.owner.username})"
        return f"{self.user.username} - {self.role}"
    
    def get_business_owner(self):
        """Get the business owner for this user (self if owner, owner if staff)"""
        if self.role == 'owner':
            return self.user
        elif self.role == 'staff' and self.owner:
            return self.owner
        return None
    
    def can_manage_staff(self):
        """Check if this user can manage staff members"""
        return self.role == 'owner'
    
    def get_accessible_inventory(self):
        """Get inventory items this user can access"""
        business_owner = self.get_business_owner()
        if business_owner:
            from .models import Inventory
            return Inventory.objects.filter(owner=business_owner)
        return Inventory.objects.none()

    class Meta:
        ordering = ['-created_at']


class SupplierProfile(models.Model):
    """Direct supplier profile linked to User account"""
    PRODUCT_TYPE_CHOICES = [
        ('beverages', 'Beverages'),
        ('canned_goods', 'Canned Goods'),
        ('condiments', 'Condiments & Sauces'),
        ('dairy', 'Dairy Products'),
        ('snacks', 'Snacks & Chips'),
        ('instant_noodles', 'Instant Noodles'),
        ('rice_grains', 'Rice & Grains'),
        ('cooking_oil', 'Cooking Oil'),
        ('personal_care', 'Personal Care'),
        ('household', 'Household Items'),
        ('frozen', 'Frozen Foods'),
        ('bread_bakery', 'Bread & Bakery'),
        ('candy_sweets', 'Candy & Sweets'),
        ('cigarettes', 'Cigarettes & Tobacco'),
        ('other', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='supplier_profile')
    business_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    
    # Additional supplier verification fields
    products_supplied = models.CharField(max_length=50, choices=PRODUCT_TYPE_CHOICES, default='other', 
                                       help_text="Type of products supplied")
    business_address = models.TextField(default='', blank=True, help_text="Complete business address")
    business_permit = models.FileField(upload_to='supplier_documents/', blank=True, null=True,
                                     help_text="Business permit or certificate upload")
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.business_name} - {self.user.username}"

    class Meta:
        ordering = ['-created_at']


class BusinessOwnerProfile(models.Model):
    """Profile for business owners with verification details"""
    STORE_TYPE_CHOICES = [
        ('sari_sari', 'Sari-Sari Store'),
        ('grocery', 'Grocery Store'),
        ('mini_mart', 'Mini Mart'),
        ('convenience', 'Convenience Store'),
        ('supermarket', 'Supermarket'),
        ('other', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business_owner_profile')
    store_name = models.CharField(max_length=200, help_text="Name of the store or business")
    store_address = models.TextField(help_text="Complete store address/location")
    store_type = models.CharField(max_length=50, choices=STORE_TYPE_CHOICES, default='sari_sari',
                                help_text="Type of store")
    business_permit = models.FileField(upload_to='owner_documents/', blank=True, null=True,
                                     help_text="Business permit or proof of registration")
    
    # Contact information
    contact_person = models.CharField(max_length=200, help_text="Primary contact person")
    contact_phone = models.CharField(max_length=15, help_text="Contact phone number")
    contact_email = models.EmailField(help_text="Contact email address")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.store_name} - {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Business Owner Profile"
        verbose_name_plural = "Business Owner Profiles"


class Supplier(models.Model):
    """Connection between store owner and supplier (legacy/relationship model)"""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='suppliers')
    supplier_profile = models.ForeignKey('SupplierProfile', on_delete=models.CASCADE, related_name='connections', null=True, blank=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class Product(models.Model):
    UNIT_CHOICES = [
        ('pcs', 'Pieces'),
        ('pack', 'Pack'),
        ('box', 'Box'),
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('liter', 'Liter'),
        ('ml', 'Milliliter'),
        ('bottle', 'Bottle'),
        ('can', 'Can'),
        ('sachet', 'Sachet'),
        ('bag', 'Bag'),
        ('sack', 'Sack'),
        ('dozen', 'Dozen'),
    ]
    
    supplier_profile = models.ForeignKey('SupplierProfile', on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    # Keep legacy supplier field for backward compatibility
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, choices=UNIT_CHOICES, default='pcs')
    manufactured_date = models.DateField(null=True, blank=True, help_text="Date when the product was manufactured")
    expiration_date = models.DateField(null=True, blank=True, help_text="Date when the product expires")
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.supplier_profile:
            return f"{self.name} - {self.supplier_profile.business_name}"
        elif self.supplier:
            return f"{self.name} - {self.supplier.name}"
        return self.name
    
    def is_expired(self):
        """Check if the product has expired"""
        if self.expiration_date:
            from django.utils import timezone
            return timezone.now().date() > self.expiration_date
        return False
    
    def days_until_expiration(self):
        """Get the number of days until expiration"""
        if self.expiration_date:
            from django.utils import timezone
            today = timezone.now().date()
            if self.expiration_date >= today:
                return (self.expiration_date - today).days
            else:
                return 0  # Already expired
        return None
    
    def is_near_expiration(self, days_threshold=7):
        """Check if the product is near expiration (within threshold days)"""
        days_left = self.days_until_expiration()
        if days_left is not None:
            return days_left <= days_threshold
        return False

    class Meta:
        ordering = ['name']


class Inventory(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventory')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory')
    quantity = models.IntegerField(default=0)
    last_restocked = models.DateTimeField(null=True, blank=True)
    low_stock_threshold = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.unit}"

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    class Meta:
        verbose_name_plural = 'Inventories'
        unique_together = ['owner', 'product']


class Order(models.Model):
    STATUS_CHOICES = [
        ('cart', 'In Cart'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='cart')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_verified = models.BooleanField(default=False, help_text="Has the supplier verified receiving this payment?")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_orders', help_text="Supplier who verified the payment")
    verified_date = models.DateTimeField(null=True, blank=True, help_text="Date when payment was verified by supplier")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ordered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} - {self.owner.username} - {self.status}"

    def calculate_total(self):
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        self.save()
        return total

    class Meta:
        ordering = ['-created_at']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.price

    class Meta:
        unique_together = ['order', 'product']


class ConnectionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connection_requests_sent')
    supplier_profile = models.ForeignKey('SupplierProfile', on_delete=models.CASCADE, related_name='connection_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, help_text="Optional message from store owner")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.owner.username} -> {self.supplier_profile.business_name} ({self.status})"
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['owner', 'supplier_profile']


class StockOut(models.Model):
    """Model to track when products are sold or used (stock deduction)"""
    REASON_CHOICES = [
        ('sale', 'Sale'),
        ('used', 'Used/Consumed'),
        ('damaged', 'Damaged'),
        ('expired', 'Expired'),
        ('other', 'Other'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stock_outs')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_outs')
    quantity = models.IntegerField(help_text="Quantity sold/used")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='sale')
    remarks = models.TextField(blank=True, null=True, help_text="Optional notes about this stock out")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod', help_text="Payment method used for this transaction")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', help_text="Payment status")
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_stock_outs')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.unit} ({self.reason})"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Out'
        verbose_name_plural = 'Stock Outs'


class SupplierProduct(models.Model):
    """Products managed by suppliers with their own inventory"""
    CATEGORY_CHOICES = [
        ('beverages', 'Beverages'),
        ('canned_goods', 'Canned Goods'),
        ('condiments', 'Condiments & Sauces'),
        ('dairy', 'Dairy Products'),
        ('snacks', 'Snacks & Chips'),
        ('instant_noodles', 'Instant Noodles'),
        ('rice_grains', 'Rice & Grains'),
        ('cooking_oil', 'Cooking Oil'),
        ('personal_care', 'Personal Care'),
        ('household', 'Household Items'),
        ('frozen', 'Frozen Foods'),
        ('bread_bakery', 'Bread & Bakery'),
        ('candy_sweets', 'Candy & Sweets'),
        ('cigarettes', 'Cigarettes & Tobacco'),
        ('other', 'Other'),
    ]
    
    UNIT_CHOICES = [
        ('pcs', 'Pieces'),
        ('pack', 'Pack'),
        ('box', 'Box'),
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('liter', 'Liter'),
        ('ml', 'Milliliter'),
        ('bottle', 'Bottle'),
        ('can', 'Can'),
        ('sachet', 'Sachet'),
        ('bag', 'Bag'),
        ('sack', 'Sack'),
        ('dozen', 'Dozen'),
    ]
    
    supplier = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supplier_products')
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    available_stock = models.IntegerField(default=0)
    minimum_order_quantity = models.IntegerField(default=1)
    unit = models.CharField(max_length=50, choices=UNIT_CHOICES, default='pcs')
    manufactured_date = models.DateField(null=True, blank=True, help_text="Date when the product was manufactured")
    expiration_date = models.DateField(null=True, blank=True, help_text="Date when the product expires")
    is_active = models.BooleanField(default=True)
    low_stock_threshold = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.supplier.username}"

    @property
    def is_low_stock(self):
        return self.available_stock <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.available_stock <= 0
    
    def is_expired(self):
        """Check if the product has expired"""
        if self.expiration_date:
            from django.utils import timezone
            return timezone.now().date() > self.expiration_date
        return False
    
    def days_until_expiration(self):
        """Get the number of days until expiration"""
        if self.expiration_date:
            from django.utils import timezone
            today = timezone.now().date()
            if self.expiration_date >= today:
                return (self.expiration_date - today).days
            else:
                return 0  # Already expired
        return None
    
    def is_near_expiration(self, days_threshold=7):
        """Check if the product is near expiration (within threshold days)"""
        days_left = self.days_until_expiration()
        if days_left is not None:
            return days_left <= days_threshold
        return False

    class Meta:
        ordering = ['name']
        unique_together = ['supplier', 'name']


class SupplierOrder(models.Model):
    """Orders from store owners to suppliers"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('delivered', 'Delivered'),
    ]
    
    # New Order Status Choices
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # New Delivery Status Choices
    DELIVERY_STATUS_CHOICES = [
        ('not_shipped', 'Not Yet Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
    ]

    supplier_product = models.ForeignKey(SupplierProduct, on_delete=models.CASCADE, related_name='orders')
    store_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supplier_orders')
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of order
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # New Order Status and Delivery Status fields
    order_status = models.CharField(
        max_length=20, 
        choices=ORDER_STATUS_CHOICES, 
        default='pending',
        help_text="Current stage of the order transaction"
    )
    delivery_status = models.CharField(
        max_length=20, 
        choices=DELIVERY_STATUS_CHOICES, 
        default='not_shipped',
        help_text="Current stage of the delivery/shipment"
    )
    order_status_updated_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last time order status was updated"
    )
    delivery_status_updated_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last time delivery status was updated"
    )
    status_updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='updated_supplier_orders',
        help_text="User who last updated the status"
    )
    
    notes = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod', help_text="Payment method for this order")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', help_text="Payment status")
    payment_verified = models.BooleanField(default=False, help_text="Has the supplier verified receiving this payment?")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_supplier_orders', help_text="Supplier who verified the payment")
    verified_date = models.DateTimeField(null=True, blank=True, help_text="Date when payment was verified by supplier")
    inventory_updated = models.BooleanField(default=False, help_text="Has inventory been updated for this order?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} - {self.supplier_product.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        # Calculate total amount
        self.total_amount = self.quantity * self.unit_price
        
        # Note: Stock deduction and inventory update are handled in supplier_views.py
        # to ensure proper error handling, stock movement logging, and owner inventory updates
        
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']


class StockMovement(models.Model):
    """Track stock movements for supplier products"""
    MOVEMENT_TYPES = [
        ('restock', 'Restock'),
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
    ]

    supplier_product = models.ForeignKey(SupplierProduct, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()  # Positive for additions, negative for deductions
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.supplier_product.name} - {self.movement_type} - {self.quantity}"

    class Meta:
        ordering = ['-created_at']


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('order', 'Order Placed'),
        ('status_change', 'Status Changed'),
        ('stock_out', 'Stock Out'),
        ('restock', 'Restock'),
        ('order_approved', 'Order Approved'),
        ('order_rejected', 'Order Rejected'),
        ('order_delivered', 'Order Delivered'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']


class SupplierPaymentInfo(models.Model):
    """
    Store payment receiving information for suppliers.
    This allows suppliers to provide their payment details so that
    store owners know where to send payments.
    """
    supplier = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='supplier_payment_info',
        help_text="Supplier user account"
    )
    
    # E-wallet payment details
    gcash_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text="GCash mobile number for receiving payments"
    )
    gcash_account_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name registered with GCash account"
    )
    
    paymaya_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text="PayMaya mobile number for receiving payments"
    )
    paymaya_account_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name registered with PayMaya account"
    )
    
    # Bank account details
    bank_name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Name of the bank (e.g., BDO, BPI, Metrobank)"
    )
    bank_account_name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Account holder name as registered with the bank"
    )
    bank_account_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Bank account number"
    )
    
    # Additional information
    payment_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional instructions or notes for payment (e.g., branch, reference format)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payment Info - {self.supplier.username}"
    
    def has_gcash(self):
        """Check if supplier has GCash payment method available"""
        return bool(self.gcash_number)
    
    def has_paymaya(self):
        """Check if supplier has PayMaya payment method available"""
        return bool(self.paymaya_number)
    
    def has_bank_transfer(self):
        """Check if supplier has bank transfer details available"""
        return bool(self.bank_name and self.bank_account_number)
    
    def get_available_payment_methods(self):
        """Return list of available payment methods for this supplier"""
        methods = []
        if self.has_gcash():
            methods.append('gcash')
        if self.has_paymaya():
            methods.append('paymaya')
        if self.has_bank_transfer():
            methods.append('bank_transfer')
        return methods
    
    class Meta:
        verbose_name = "Supplier Payment Information"
        verbose_name_plural = "Supplier Payment Information"


class Notification(models.Model):
    """System notifications for users"""
    NOTIFICATION_TYPES = [
        ('order_placed', 'Order Placed'),
        ('order_confirmed', 'Order Confirmed'),
        ('order_processing', 'Order Processing'),
        ('order_completed', 'Order Completed'),
        ('order_cancelled', 'Order Cancelled'),
        ('delivery_shipped', 'Delivery Shipped'),
        ('delivery_out', 'Out for Delivery'),
        ('delivery_delivered', 'Delivery Delivered'),
        ('payment_paid', 'Payment Marked as Paid'),
        ('payment_verified', 'Payment Verified'),
        ('stock_low', 'Low Stock Alert'),
        ('stock_out', 'Out of Stock Alert'),
        ('new_message', 'New Message'),
        ('system', 'System Notification'),
    ]
    
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        help_text="User who will receive this notification"
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sent_notifications',
        help_text="User who triggered this notification (optional)"
    )
    notification_type = models.CharField(
        max_length=30, 
        choices=NOTIFICATION_TYPES,
        help_text="Type of notification"
    )
    title = models.CharField(
        max_length=200,
        help_text="Notification title"
    )
    message = models.TextField(
        help_text="Notification message body"
    )
    
    # Related objects
    related_order = models.ForeignKey(
        SupplierOrder, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notifications',
        help_text="Related order if applicable"
    )
    related_product = models.ForeignKey(
        SupplierProduct, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notifications',
        help_text="Related product if applicable"
    )
    
    # Status
    is_read = models.BooleanField(
        default=False,
        help_text="Has the user read this notification?"
    )
    read_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When was this notification read?"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]


class Message(models.Model):
    """Direct messages between users"""
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages',
        help_text="User who sent this message"
    )
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_messages',
        help_text="User who will receive this message"
    )
    
    # Message content
    subject = models.CharField(
        max_length=200,
        blank=True,
        help_text="Message subject (optional)"
    )
    body = models.TextField(
        help_text="Message content"
    )
    
    # Related order context
    related_order = models.ForeignKey(
        SupplierOrder, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='messages',
        help_text="Order this message is about"
    )
    
    # Status
    is_read = models.BooleanField(
        default=False,
        help_text="Has the recipient read this message?"
    )
    read_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When was this message read?"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"From {self.sender.username} to {self.recipient.username}: {self.subject or 'No subject'}"
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['sender', 'recipient', '-created_at']),
            models.Index(fields=['related_order', '-created_at']),
        ]


class Conversation(models.Model):
    """Conversation thread between two users"""
    user1 = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='conversations_as_user1'
    )
    user2 = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='conversations_as_user2'
    )
    related_order = models.ForeignKey(
        SupplierOrder, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='conversations'
    )
    last_message_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Conversation between {self.user1.username} and {self.user2.username}"
    
    def get_other_user(self, current_user):
        """Get the other user in the conversation"""
        return self.user2 if self.user1 == current_user else self.user1
    
    def get_messages(self):
        """Get all messages in this conversation"""
        return Message.objects.filter(
            models.Q(sender=self.user1, recipient=self.user2) |
            models.Q(sender=self.user2, recipient=self.user1)
        ).order_by('created_at')
    
    def get_unread_count(self, user):
        """Get unread message count for a specific user"""
        return Message.objects.filter(
            recipient=user,
            sender=self.get_other_user(user),
            is_read=False
        ).count()
    
    class Meta:
        ordering = ['-last_message_at']
        unique_together = ['user1', 'user2', 'related_order']
