import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import SupplierOrder, SupplierProduct

# Get Order #2
order = SupplierOrder.objects.get(id=2)
product = order.supplier_product

print(f"\n=== BEFORE UPDATE ===")
print(f"Order #2:")
print(f"  order_status: {order.order_status}")
print(f"  delivery_status: {order.delivery_status}")
print(f"  inventory_updated: {order.inventory_updated}")
print(f"  quantity: {order.quantity}")
print(f"\nProduct: {product.name}")
print(f"  available_stock: {product.available_stock}")

# Simulate what happens when both statuses are set
print(f"\n=== SIMULATING STATUS UPDATE ===")
print(f"Setting order_status='completed' and delivery_status='delivered'")

# Check the condition
should_update = (
    'completed' == 'completed' and 
    'delivered' == 'delivered' and 
    not order.inventory_updated
)

print(f"\nCondition check:")
print(f"  order_status == 'completed': True")
print(f"  delivery_status == 'delivered': True")
print(f"  not inventory_updated: {not order.inventory_updated}")
print(f"  should_update_inventory: {should_update}")

if should_update:
    print(f"\n✓ Inventory update WOULD trigger")
    print(f"  Supplier stock would be: {product.available_stock} - {order.quantity} = {product.available_stock - order.quantity}")
else:
    print(f"\n✗ Inventory update would NOT trigger")
    print(f"  Reason: inventory_updated is already True")

print(f"\n=== TEST COMPLETE ===\n")
