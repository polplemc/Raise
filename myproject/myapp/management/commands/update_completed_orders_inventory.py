from django.core.management.base import BaseCommand
from django.utils import timezone
from myapp.models import SupplierOrder, Product, Inventory, Supplier, StockMovement, ActivityLog


class Command(BaseCommand):
    help = 'Update inventory for all completed and delivered orders that have not been processed yet'

    def handle(self, *args, **options):
        # Find all orders that are completed AND delivered but inventory not updated
        orders = SupplierOrder.objects.filter(
            order_status='completed',
            delivery_status='delivered',
            inventory_updated=False
        ).select_related('supplier_product', 'store_owner', 'supplier_product__supplier')
        
        total_orders = orders.count()
        self.stdout.write(f"Found {total_orders} orders to process...")
        
        success_count = 0
        error_count = 0
        
        for order in orders:
            try:
                # Set delivered timestamp if not set
                if not order.delivered_at:
                    order.delivered_at = timezone.now()
                
                # Deduct from supplier's stock
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
                        notes=f'Order #{order.id} - Inventory sync (completed & delivered)',
                        created_by=order.supplier_product.supplier
                    )
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'  [OK] Supplier stock updated for Order #{order.id}: -{order.quantity} {supplier_product.unit}'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'  [WARNING] Order #{order.id}: Insufficient supplier stock ({supplier_product.available_stock} < {order.quantity})'
                    ))
                
                # Update owner's inventory
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
                
                # Update inventory
                inventory, inv_created = Inventory.objects.get_or_create(
                    owner=order.store_owner,
                    product=old_product,
                    defaults={'quantity': 0}
                )
                inventory.quantity += order.quantity
                inventory.last_restocked = timezone.now()
                inventory.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=order.store_owner,
                    action='inventory_updated',
                    description=f'Inventory sync: +{order.quantity} {order.supplier_product.unit} of {order.supplier_product.name} from Order #{order.id}',
                    ip_address='127.0.0.1'
                )
                
                # Mark as updated
                order.inventory_updated = True
                order.save()
                
                success_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  [OK] Owner inventory updated for Order #{order.id}: +{order.quantity} {order.supplier_product.unit}'
                ))
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(
                    f'  [ERROR] Error processing Order #{order.id}: {str(e)}'
                ))
        
        self.stdout.write(self.style.SUCCESS(
            f'\n[DONE] Completed! Successfully processed {success_count}/{total_orders} orders.'
        ))
        if error_count > 0:
            self.stdout.write(self.style.WARNING(
                f'[WARNING] {error_count} orders had errors.'
            ))
