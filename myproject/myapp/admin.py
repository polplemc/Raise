from django.contrib import admin
from .models import UserProfile, Supplier, Product, Inventory, Order, OrderItem, ActivityLog, SupplierProfile, ConnectionRequest, StockOut

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'store_name', 'phone']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email', 'store_name']

@admin.register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'contact_person', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['business_name', 'contact_person', 'email', 'user__username']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'supplier_profile', 'contact_person', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'contact_person', 'email']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'supplier', 'price', 'unit', 'is_available']
    list_filter = ['is_available', 'supplier']
    search_fields = ['name', 'supplier__name']

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'owner', 'quantity', 'last_restocked', 'is_low_stock']
    list_filter = ['last_restocked']
    search_fields = ['product__name', 'owner__username']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'supplier', 'status', 'total_amount', 'ordered_at']
    list_filter = ['status', 'ordered_at']
    search_fields = ['owner__username', 'supplier__name']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price', 'subtotal']
    search_fields = ['product__name', 'order__id']

@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ['owner', 'supplier_profile', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['owner__username', 'supplier_profile__business_name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(StockOut)
class StockOutAdmin(admin.ModelAdmin):
    list_display = ['product', 'owner', 'quantity', 'reason', 'processed_by', 'created_at']
    list_filter = ['reason', 'created_at', 'owner']
    search_fields = ['product__name', 'owner__username', 'remarks']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'description', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'description']
    readonly_fields = ['timestamp']
