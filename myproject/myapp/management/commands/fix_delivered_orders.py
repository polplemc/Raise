"""
Management command to fix delivered orders that didn't update inventory
Run with: python manage.py fix_delivered_orders
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from myapp.models import SupplierOrder, Product, Inventory, Supplier, ActivityLog, StockMovement


class Command(BaseCommand):
    help = 'Fix delivered orders that did not update owner inventory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--order-id',
            type=int,
            help='Specific order ID to fix (optional)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Fix all delivered orders',
        )

    def handle(self, *args, **options):
        order_id = options.get('order_id')
        fix_all = options.get('all')

        if order_id:
            # Fix specific order
            orders = SupplierOrder.objects.filter(id=order_id, status='delivered')
            if not orders.exists():
                self.stdout.write(self.style.ERROR(f'Order #{order_id} not found or not delivered'))
                return
        elif fix_all:
            # Fix all delivered orders
            orders = SupplierOrder.objects.filter(status='delivered')
        else:
            self.stdout.write(self.style.ERROR('Please specify --order-id or --all'))
            return

        self.stdout.write(f'Processing {orders.count()} order(s)...\n')

        for order in orders:
            self.stdout.write(f'Checking Order #{order.id}: {order.supplier_product.name}')
            
            try:
                # Get supplier info
                supplier_user = order.supplier_product.supplier
                supplier_profile = getattr(supplier_user, 'supplier_profile', None)
                
                # Check if product already exists in owner's inventory
                old_product = Product.objects.filter(
                    name=order.supplier_product.name,
                    supplier__owner=order.store_owner
                ).first()
                
                if not old_product:
                    self.stdout.write('  → Creating Product entry...')
                    
                    # Get or create supplier entry for this owner
                    supplier_entry, created = Supplier.objects.get_or_create(
                        owner=order.store_owner,
                        supplier_profile=supplier_profile,
                        defaults={
                            'name': supplier_profile.business_name if supplier_profile else supplier_user.username,
                            'contact_person': supplier_user.first_name or supplier_user.username,
                            'email': supplier_user.email,
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'  → Created Supplier entry: {supplier_entry.name}')
                    
                    # Create product entry
                    old_product = Product.objects.create(
                        name=order.supplier_product.name,
                        description=order.supplier_product.description,
                        unit=order.supplier_product.unit,
                        price=order.supplier_product.unit_price,
                        supplier=supplier_entry
                    )
                    self.stdout.write(f'  → Created Product: {old_product.name}')
                else:
                    self.stdout.write(f'  → Product exists: {old_product.name}')
                
                # Check if inventory already updated
                inventory, created = Inventory.objects.get_or_create(
                    owner=order.store_owner,
                    product=old_product,
                    defaults={'quantity': 0}
                )
                
                if created or inventory.quantity == 0:
                    # Update inventory
                    old_quantity = inventory.quantity
                    inventory.quantity += order.quantity
                    inventory.last_restocked = order.delivered_at or timezone.now()
                    inventory.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Updated inventory: {old_quantity} → {inventory.quantity} {order.supplier_product.unit}'
                    ))
                    
                    # Log activity for owner
                    ActivityLog.objects.create(
                        user=order.store_owner,
                        action='inventory_updated',
                        description=f'Inventory updated (manual fix): +{order.quantity} {order.supplier_product.unit} of {order.supplier_product.name} from Order #{order.id}',
                        ip_address='127.0.0.1'
                    )
                    self.stdout.write('  ✓ Activity log created')
                    
                    # Deduct supplier stock if not already done
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
                            notes=f'Order #{order.id} delivered (manual fix)',
                            created_by=supplier_user
                        )
                        self.stdout.write('  ✓ Supplier stock deducted')
                    
                    self.stdout.write(self.style.SUCCESS(f'✓ Order #{order.id} fixed successfully!\n'))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠ Inventory already has stock ({inventory.quantity}), skipping...\n'
                    ))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error fixing Order #{order.id}: {str(e)}\n'))

        self.stdout.write(self.style.SUCCESS('\n✓ Process complete!'))
