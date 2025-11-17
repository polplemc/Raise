from django.core.management.base import BaseCommand
from django.utils import timezone
from myapp.models import SupplierOrder, StockMovement, Product, Supplier, Inventory, ActivityLog


class Command(BaseCommand):
    help = 'Fix inventory for orders that are already completed and delivered but inventory was not updated'

    def handle(self, *args, **options):
        # Find all orders that are completed AND delivered but don't have delivered_at timestamp
        orders_to_fix = SupplierOrder.objects.filter(
            order_status='completed',
            delivery_status='delivered',
            delivered_at__isnull=True  # These orders never had inventory updated
        )
        
        self.stdout.write(f"Found {orders_to_fix.count()} orders to fix")
        
        fixed_count = 0
        error_count = 0
        
        for order in orders_to_fix:
            self.stdout.write(f"\nProcessing Order #{order.id}:")
            self.stdout.write(f"  Product: {order.supplier_product.name}")
            self.stdout.write(f"  Quantity: {order.quantity} {order.supplier_product.unit}")
            self.stdout.write(f"  Supplier: {order.supplier_product.supplier.username}")
            self.stdout.write(f"  Owner: {order.store_owner.username}")
            
            try:
                # Set delivered timestamp
                order.delivered_at = timezone.now()
                
                # 1. Deduct from supplier's stock
                supplier_product = order.supplier_product
                if supplier_product.available_stock >= order.quantity:
                    previous_stock = supplier_product.available_stock
                    supplier_product.available_stock -= order.quantity
                    supplier_product.save()
                    
                    # Record stock movement
                    StockMovement.objects.create(
                        supplier_product=supplier_product,
                        movement_type='sale',
                        quantity=order.quantity,
                        previous_stock=previous_stock,
                        new_stock=supplier_product.available_stock,
                        notes=f'Order #{order.id} - Inventory fix for completed & delivered order',
                        created_by=order.supplier_product.supplier
                    )
                    
                    self.stdout.write(self.style.SUCCESS(f"  [OK] Supplier stock: {previous_stock} -> {supplier_product.available_stock} {supplier_product.unit}"))
                else:
                    self.stdout.write(self.style.WARNING(f"  [WARNING] Insufficient supplier stock! Has {supplier_product.available_stock}, needs {order.quantity}"))
                    # Still proceed with owner inventory update
                
                # 2. Update owner's inventory
                supplier_user = order.supplier_product.supplier
                supplier_profile = getattr(supplier_user, 'supplier_profile', None)
                
                # Find or create product
                old_product = Product.objects.filter(
                    name=order.supplier_product.name,
                    supplier__owner=order.store_owner
                ).first()
                
                if not old_product:
                    # Create supplier entry
                    supplier_entry, created = Supplier.objects.get_or_create(
                        owner=order.store_owner,
                        supplier_profile=supplier_profile,
                        defaults={
                            'name': supplier_profile.business_name if supplier_profile else supplier_user.username,
                            'contact_person': supplier_user.first_name or supplier_user.username,
                            'email': supplier_user.email,
                        }
                    )
                    
                    # Create product
                    old_product = Product.objects.create(
                        name=order.supplier_product.name,
                        description=order.supplier_product.description,
                        unit=order.supplier_product.unit,
                        price=order.supplier_product.unit_price,
                        supplier=supplier_entry
                    )
                    self.stdout.write(f"  → Created product for owner")
                
                # Update inventory
                inventory, inv_created = Inventory.objects.get_or_create(
                    owner=order.store_owner,
                    product=old_product,
                    defaults={'quantity': 0}
                )
                previous_owner_stock = inventory.quantity
                inventory.quantity += order.quantity
                inventory.last_restocked = timezone.now()
                inventory.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=order.store_owner,
                    action='inventory_updated',
                    description=f'Inventory fix: +{order.quantity} {order.supplier_product.unit} of {order.supplier_product.name} from Order #{order.id}',
                    ip_address='127.0.0.1'
                )
                
                self.stdout.write(self.style.SUCCESS(f"  [OK] Owner inventory: {previous_owner_stock} -> {inventory.quantity} {order.supplier_product.unit}"))
                
                # Save order with delivered_at timestamp
                order.save()
                
                fixed_count += 1
                self.stdout.write(self.style.SUCCESS(f"  [SUCCESS] Order #{order.id} fixed successfully!"))
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"  [ERROR] Error fixing Order #{order.id}: {str(e)}"))
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Fixed {fixed_count} orders"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"[ERROR] {error_count} errors"))
        self.stdout.write("="*50)
