"""
Test script to check SupplierOrder creation and visibility
Run with: python manage.py shell < test_orders.py
"""

from myapp.models import SupplierOrder, SupplierProduct, User

print("\n=== SUPPLIER ORDER DIAGNOSTIC ===\n")

# Check all SupplierOrders
all_orders = SupplierOrder.objects.all()
print(f"Total SupplierOrders in database: {all_orders.count()}")

if all_orders.exists():
    print("\n--- Order Details ---")
    for order in all_orders:
        print(f"\nOrder #{order.id}:")
        print(f"  Product: {order.supplier_product.name}")
        print(f"  Supplier: {order.supplier_product.supplier.username}")
        print(f"  Store Owner: {order.store_owner.username}")
        print(f"  Quantity: {order.quantity}")
        print(f"  Unit Price: ₱{order.unit_price}")
        print(f"  Total Amount: ₱{order.total_amount}")
        print(f"  Status: {order.status}")
        print(f"  Created: {order.created_at}")
else:
    print("No orders found in database!")

# Check SupplierProducts
print("\n--- Supplier Products ---")
products = SupplierProduct.objects.all()
print(f"Total SupplierProducts: {products.count()}")

if products.exists():
    for product in products:
        print(f"\nProduct: {product.name}")
        print(f"  Supplier: {product.supplier.username}")
        print(f"  Price: ₱{product.unit_price}")
        print(f"  Stock: {product.available_stock}")
        
        # Check orders for this product
        product_orders = SupplierOrder.objects.filter(supplier_product=product)
        print(f"  Orders: {product_orders.count()}")

# Check Users
print("\n--- Users ---")
owners = User.objects.filter(profile__role='owner')
suppliers = User.objects.filter(profile__role='supplier')
print(f"Owners: {owners.count()}")
print(f"Suppliers: {suppliers.count()}")

print("\n=== END DIAGNOSTIC ===\n")
