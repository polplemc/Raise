"""
Bulk Operations Utilities
Provides batch processing capabilities for orders, products, and stock
"""
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)


class BulkOperationError(Exception):
    """Custom exception for bulk operation errors"""
    pass


class BulkOrderOperations:
    """Bulk operations for orders"""
    
    @staticmethod
    @transaction.atomic
    def bulk_update_status(order_ids, new_status, user):
        """
        Update status for multiple orders
        
        Args:
            order_ids: List of order IDs
            new_status: New status to set
            user: User performing the operation
        
        Returns:
            Dict with success count and errors
        """
        from myapp.models import SupplierOrder, ActivityLog
        
        if not order_ids:
            raise BulkOperationError("No orders selected")
        
        success_count = 0
        errors = []
        
        orders = SupplierOrder.objects.filter(id__in=order_ids)
        
        for order in orders:
            try:
                old_status = order.order_status
                order.order_status = new_status
                order.save()
                
                # Handle automatic inventory deduction
                from .supplier_views import process_inventory_deduction
                process_inventory_deduction(order, user)
                
                # Log activity
                ActivityLog.objects.create(
                    user=user,
                    action=f"Bulk updated order #{order.id} status from {old_status} to {new_status}"
                )
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Order #{order.id}: {str(e)}")
                logger.error(f"Error updating order #{order.id}: {str(e)}")
        
        return {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }
    
    @staticmethod
    @transaction.atomic
    def bulk_update_delivery_status(order_ids, new_status, user):
        """Update delivery status for multiple orders"""
        from myapp.models import SupplierOrder, ActivityLog
        
        if not order_ids:
            raise BulkOperationError("No orders selected")
        
        success_count = 0
        errors = []
        
        orders = SupplierOrder.objects.filter(id__in=order_ids)
        
        for order in orders:
            try:
                old_status = order.delivery_status
                order.delivery_status = new_status
                order.save()
                
                # Handle automatic inventory deduction
                from .supplier_views import process_inventory_deduction
                process_inventory_deduction(order, user)
                
                ActivityLog.objects.create(
                    user=user,
                    action=f"Bulk updated order #{order.id} delivery status from {old_status} to {new_status}"
                )
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Order #{order.id}: {str(e)}")
                logger.error(f"Error updating order #{order.id}: {str(e)}")
        
        return {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }
    
    @staticmethod
    @transaction.atomic
    def bulk_cancel_orders(order_ids, user, reason="Bulk cancellation"):
        """Cancel multiple orders"""
        from myapp.models import SupplierOrder, ActivityLog
        
        if not order_ids:
            raise BulkOperationError("No orders selected")
        
        success_count = 0
        errors = []
        
        orders = SupplierOrder.objects.filter(id__in=order_ids)
        
        for order in orders:
            try:
                if order.order_status in ['completed', 'cancelled']:
                    errors.append(f"Order #{order.id}: Cannot cancel {order.order_status} order")
                    continue
                
                order.order_status = 'cancelled'
                order.save()
                
                ActivityLog.objects.create(
                    user=user,
                    action=f"Bulk cancelled order #{order.id}. Reason: {reason}"
                )
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Order #{order.id}: {str(e)}")
                logger.error(f"Error cancelling order #{order.id}: {str(e)}")
        
        return {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }
    
    @staticmethod
    @transaction.atomic
    def bulk_confirm_orders(order_ids, user):
        """Confirm multiple orders (supplier action)"""
        from myapp.models import SupplierOrder, ActivityLog
        
        if not order_ids:
            raise BulkOperationError("No orders selected")
        
        success_count = 0
        errors = []
        
        orders = SupplierOrder.objects.filter(id__in=order_ids)
        
        for order in orders:
            try:
                if order.order_status != 'pending':
                    errors.append(f"Order #{order.id}: Can only confirm pending orders")
                    continue
                
                order.order_status = 'confirmed'
                order.save()
                
                ActivityLog.objects.create(
                    user=user,
                    action=f"Bulk confirmed order #{order.id}"
                )
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Order #{order.id}: {str(e)}")
                logger.error(f"Error confirming order #{order.id}: {str(e)}")
        
        return {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }


class BulkProductOperations:
    """Bulk operations for products"""
    
    @staticmethod
    @transaction.atomic
    def bulk_update_price(product_ids, price_change, change_type='percentage', user=None):
        """
        Update prices for multiple products
        
        Args:
            product_ids: List of product IDs
            price_change: Amount or percentage to change
            change_type: 'percentage' or 'fixed'
            user: User performing the operation
        """
        from myapp.models import SupplierProduct, ActivityLog
        
        if not product_ids:
            raise BulkOperationError("No products selected")
        
        success_count = 0
        errors = []
        
        products = SupplierProduct.objects.filter(id__in=product_ids)
        
        for product in products:
            try:
                old_price = product.unit_price
                
                if change_type == 'percentage':
                    new_price = old_price * (1 + price_change / 100)
                else:  # fixed
                    new_price = old_price + price_change
                
                if new_price < 0:
                    errors.append(f"Product '{product.name}': Price cannot be negative")
                    continue
                
                product.unit_price = round(new_price, 2)
                product.save()
                
                if user:
                    ActivityLog.objects.create(
                        user=user,
                        action=f"Bulk updated price for '{product.name}' from ₱{old_price} to ₱{product.unit_price}"
                    )
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Product '{product.name}': {str(e)}")
                logger.error(f"Error updating product '{product.name}': {str(e)}")
        
        return {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }
    
    @staticmethod
    @transaction.atomic
    def bulk_restock(product_ids, quantity, user=None):
        """Add stock to multiple products"""
        from myapp.models import SupplierProduct, StockMovement, ActivityLog
        
        if not product_ids:
            raise BulkOperationError("No products selected")
        
        if quantity <= 0:
            raise BulkOperationError("Quantity must be positive")
        
        success_count = 0
        errors = []
        
        products = SupplierProduct.objects.filter(id__in=product_ids)
        
        for product in products:
            try:
                old_stock = product.available_stock
                product.available_stock += quantity
                product.save()
                
                # Create stock movement record
                StockMovement.objects.create(
                    supplier_product=product,
                    movement_type='in',
                    quantity=quantity,
                    reason='Bulk restock',
                    performed_by=user
                )
                
                if user:
                    ActivityLog.objects.create(
                        user=user,
                        action=f"Bulk restocked '{product.name}': {old_stock} → {product.available_stock}"
                    )
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Product '{product.name}': {str(e)}")
                logger.error(f"Error restocking product '{product.name}': {str(e)}")
        
        return {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }
    
    @staticmethod
    @transaction.atomic
    def bulk_activate_deactivate(product_ids, activate=True, user=None):
        """Activate or deactivate multiple products"""
        from myapp.models import SupplierProduct, ActivityLog
        
        if not product_ids:
            raise BulkOperationError("No products selected")
        
        success_count = 0
        errors = []
        
        products = SupplierProduct.objects.filter(id__in=product_ids)
        action_text = "activated" if activate else "deactivated"
        
        for product in products:
            try:
                # Assuming you have an is_active field
                # If not, you can add it to the model
                if hasattr(product, 'is_active'):
                    product.is_active = activate
                    product.save()
                    
                    if user:
                        ActivityLog.objects.create(
                            user=user,
                            action=f"Bulk {action_text} product '{product.name}'"
                        )
                    
                    success_count += 1
                else:
                    errors.append(f"Product '{product.name}': is_active field not found")
                
            except Exception as e:
                errors.append(f"Product '{product.name}': {str(e)}")
                logger.error(f"Error {action_text} product '{product.name}': {str(e)}")
        
        return {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }


class BulkStockOperations:
    """Bulk operations for stock/inventory"""
    
    @staticmethod
    @transaction.atomic
    def bulk_adjust_threshold(inventory_ids, threshold_value, user=None):
        """Adjust low stock threshold for multiple inventory items"""
        from myapp.models import Inventory, ActivityLog
        
        if not inventory_ids:
            raise BulkOperationError("No inventory items selected")
        
        if threshold_value < 0:
            raise BulkOperationError("Threshold must be non-negative")
        
        success_count = 0
        errors = []
        
        inventory_items = Inventory.objects.filter(id__in=inventory_ids)
        
        for item in inventory_items:
            try:
                old_threshold = item.low_stock_threshold
                item.low_stock_threshold = threshold_value
                item.save()
                
                if user:
                    ActivityLog.objects.create(
                        user=user,
                        action=f"Bulk updated threshold for '{item.product.name}': {old_threshold} → {threshold_value}"
                    )
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Inventory '{item.product.name}': {str(e)}")
                logger.error(f"Error updating inventory '{item.product.name}': {str(e)}")
        
        return {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }
    
    @staticmethod
    @transaction.atomic
    def bulk_stock_adjustment(inventory_ids, adjustment_type, quantity, reason, user=None):
        """
        Adjust stock for multiple inventory items
        
        Args:
            inventory_ids: List of inventory IDs
            adjustment_type: 'add' or 'subtract'
            quantity: Amount to adjust
            reason: Reason for adjustment
            user: User performing the operation
        """
        from myapp.models import Inventory, StockOut, ActivityLog
        
        if not inventory_ids:
            raise BulkOperationError("No inventory items selected")
        
        if quantity <= 0:
            raise BulkOperationError("Quantity must be positive")
        
        success_count = 0
        errors = []
        
        inventory_items = Inventory.objects.filter(id__in=inventory_ids)
        
        for item in inventory_items:
            try:
                old_quantity = item.quantity
                
                if adjustment_type == 'add':
                    item.quantity += quantity
                    item.last_restocked = timezone.now()
                else:  # subtract
                    if item.quantity < quantity:
                        errors.append(f"'{item.product.name}': Insufficient stock ({item.quantity} available)")
                        continue
                    
                    item.quantity -= quantity
                    
                    # Record stock out
                    StockOut.objects.create(
                        inventory=item,
                        product=item.product,
                        quantity=quantity,
                        reason='adjustment',
                        remarks=f"Bulk adjustment: {reason}",
                        processed_by=user
                    )
                
                item.save()
                
                if user:
                    ActivityLog.objects.create(
                        user=user,
                        action=f"Bulk adjusted stock for '{item.product.name}': {old_quantity} → {item.quantity}"
                    )
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"'{item.product.name}': {str(e)}")
                logger.error(f"Error adjusting stock for '{item.product.name}': {str(e)}")
        
        return {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }


# Helper function to format bulk operation results
def format_bulk_result(result, request=None):
    """
    Format bulk operation result for display
    
    Args:
        result: Dict with success_count, error_count, errors
        request: Django request object (for messages)
    
    Returns:
        Formatted message string
    """
    message = f"Successfully processed {result['success_count']} items."
    
    if result['error_count'] > 0:
        message += f" {result['error_count']} errors occurred."
        
        if request:
            for error in result['errors'][:5]:  # Show first 5 errors
                messages.warning(request, error)
            
            if len(result['errors']) > 5:
                messages.warning(request, f"... and {len(result['errors']) - 5} more errors")
    
    return message
