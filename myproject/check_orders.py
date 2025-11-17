#!/usr/bin/env python
"""
Quick script to check SupplierOrder data in the database
Run with: python check_orders.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User
from myapp.models import SupplierOrder, SupplierProduct, Supplier

print("=" * 80)
print("SUPPLIER ORDER DIAGNOSTIC")
print("=" * 80)

# Check users
suppliers = User.objects.filter(profile__role='supplier')
owners = User.objects.filter(profile__role='owner')
print(f"\nUsers:")
print(f"  Suppliers: {suppliers.count()}")
print(f"  Store Owners: {owners.count()}")

# Check supplier products
print(f"\nSupplier Products:")
all_products = SupplierProduct.objects.all()
print(f"  Total: {all_products.count()}")

if all_products.exists():
    print("\n  Products by Supplier:")
    for supplier in suppliers:
        product_count = SupplierProduct.objects.filter(supplier=supplier).count()
        print(f"    {supplier.username} ({supplier.email}): {product_count} products")
        # Show first 3 products
        products = SupplierProduct.objects.filter(supplier=supplier)[:3]
        for p in products:
            print(f"      - {p.name} (₱{p.unit_price}/{p.unit}, Stock: {p.available_stock})")

# Check connections
print(f"\nSupplier Connections:")
connections = Supplier.objects.filter(is_active=True)
print(f"  Total Active Connections: {connections.count()}")
for conn in connections:
    print(f"    Owner: {conn.owner.username} <-> Supplier: {conn.supplier_profile.user.username if conn.supplier_profile else 'None'}")

# Check all orders
print(f"\nSupplier Orders:")
all_orders = SupplierOrder.objects.all()
print(f"  Total Orders in Database: {all_orders.count()}")

if all_orders.exists():
    print("\n  Order Details:")
    print("  " + "-" * 76)
    for order in all_orders:
        print(f"  Order #{order.id}")
        print(f"    Product: {order.supplier_product.name}")
        print(f"    Product.supplier: {order.supplier_product.supplier.username} (ID: {order.supplier_product.supplier.id})")
        print(f"    Store Owner: {order.store_owner.username} (ID: {order.store_owner.id})")
        print(f"    Quantity: {order.quantity} {order.supplier_product.unit}")
        print(f"    Total: ₱{order.total_amount}")
        print(f"    Status: {order.status}")
        print(f"    Created: {order.created_at}")
        print("  " + "-" * 76)
else:
    print("\n  ⚠️  No orders found in database!")
    print("  This means either:")
    print("    1. No owner has placed an order yet")
    print("    2. Orders are being created but not saved")
    print("    3. There's an error during order creation")

# Check orders by supplier
print("\n  Orders by Supplier:")
for supplier in suppliers:
    order_count = SupplierOrder.objects.filter(supplier_product__supplier=supplier).count()
    status = "✓" if order_count > 0 else "✗"
    print(f"    {status} {supplier.username}: {order_count} orders")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("  1. If no products exist, suppliers need to add products first")
print("  2. If no connections exist, owners need to connect with suppliers")
print("  3. If products and connections exist but no orders, try placing a test order")
print("=" * 80)
