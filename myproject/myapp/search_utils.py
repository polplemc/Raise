"""
Search and Filter Utilities
Provides advanced search and filtering capabilities
"""
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


class SearchFilter:
    """Base class for search and filter functionality"""
    
    def __init__(self, queryset, request):
        self.queryset = queryset
        self.request = request
        self.filters = {}
        self.search_query = request.GET.get('search', '').strip()
        self.sort_by = request.GET.get('sort', '')
        self.order = request.GET.get('order', 'desc')
        
    def apply_search(self, search_fields):
        """
        Apply search across multiple fields
        
        Args:
            search_fields: List of field names to search
        """
        if not self.search_query:
            return self.queryset
        
        query = Q()
        for field in search_fields:
            query |= Q(**{f"{field}__icontains": self.search_query})
        
        return self.queryset.filter(query)
    
    def apply_filters(self, filter_config):
        """
        Apply filters based on GET parameters
        
        Args:
            filter_config: Dict mapping GET param names to model field names
        """
        for param, field in filter_config.items():
            value = self.request.GET.get(param)
            if value:
                self.filters[field] = value
                self.queryset = self.queryset.filter(**{field: value})
        
        return self.queryset
    
    def apply_date_range(self, date_field='created_at'):
        """Apply date range filter"""
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            self.queryset = self.queryset.filter(**{f"{date_field}__gte": date_from})
        if date_to:
            self.queryset = self.queryset.filter(**{f"{date_field}__lte": date_to})
        
        return self.queryset
    
    def apply_sorting(self, sort_config):
        """
        Apply sorting
        
        Args:
            sort_config: Dict mapping sort keys to model field names
        """
        if self.sort_by and self.sort_by in sort_config:
            field = sort_config[self.sort_by]
            if self.order == 'asc':
                self.queryset = self.queryset.order_by(field)
            else:
                self.queryset = self.queryset.order_by(f'-{field}')
        
        return self.queryset
    
    def paginate(self, per_page=20):
        """
        Paginate results
        
        Args:
            per_page: Number of items per page
        """
        page = self.request.GET.get('page', 1)
        paginator = Paginator(self.queryset, per_page)
        
        try:
            items = paginator.page(page)
        except PageNotAnInteger:
            items = paginator.page(1)
        except EmptyPage:
            items = paginator.page(paginator.num_pages)
        
        return items
    
    def get_context(self):
        """Get context data for template"""
        return {
            'search_query': self.search_query,
            'sort_by': self.sort_by,
            'order': self.order,
            'filters': self.filters
        }


class InventorySearchFilter(SearchFilter):
    """Search and filter for inventory"""
    
    def apply(self):
        # Search across product name and supplier
        self.queryset = self.apply_search([
            'product__name',
            'product__supplier__first_name',
            'product__supplier__last_name'
        ])
        
        # Apply filters
        self.queryset = self.apply_filters({
            'status': 'status',  # Custom filter handled separately
            'supplier': 'product__supplier__id'
        })
        
        # Status filter (custom logic)
        status = self.request.GET.get('status')
        if status == 'in_stock':
            self.queryset = self.queryset.filter(quantity__gt=0)
        elif status == 'low_stock':
            self.queryset = self.queryset.filter(
                quantity__lte=models.F('low_stock_threshold'),
                quantity__gt=0
            )
        elif status == 'out_of_stock':
            self.queryset = self.queryset.filter(quantity=0)
        
        # Apply sorting
        self.queryset = self.apply_sorting({
            'name': 'product__name',
            'quantity': 'quantity',
            'date': 'last_restocked'
        })
        
        return self.queryset


class OrderSearchFilter(SearchFilter):
    """Search and filter for orders"""
    
    def apply(self):
        # Search across product name and order ID
        self.queryset = self.apply_search([
            'supplier_product__name',
            'id'
        ])
        
        # Apply filters
        self.queryset = self.apply_filters({
            'order_status': 'order_status',
            'delivery_status': 'delivery_status',
            'payment_status': 'payment_status',
            'payment_method': 'payment_method'
        })
        
        # Date range
        self.queryset = self.apply_date_range('created_at')
        
        # Apply sorting
        self.queryset = self.apply_sorting({
            'date': 'created_at',
            'amount': 'total_amount',
            'product': 'supplier_product__name'
        })
        
        return self.queryset


class ProductSearchFilter(SearchFilter):
    """Search and filter for products"""
    
    def apply(self):
        # Search across product name and description
        self.queryset = self.apply_search([
            'name',
            'description'
        ])
        
        # Apply filters
        self.queryset = self.apply_filters({
            'category': 'category',
            'status': 'status'  # Custom filter
        })
        
        # Price range filter
        price_min = self.request.GET.get('price_min')
        price_max = self.request.GET.get('price_max')
        
        if price_min:
            self.queryset = self.queryset.filter(unit_price__gte=price_min)
        if price_max:
            self.queryset = self.queryset.filter(unit_price__lte=price_max)
        
        # Stock status filter
        status = self.request.GET.get('status')
        if status == 'in_stock':
            self.queryset = self.queryset.filter(available_stock__gt=0)
        elif status == 'low_stock':
            self.queryset = self.queryset.filter(
                available_stock__lte=models.F('low_stock_threshold'),
                available_stock__gt=0
            )
        elif status == 'out_of_stock':
            self.queryset = self.queryset.filter(available_stock=0)
        
        # Apply sorting
        self.queryset = self.apply_sorting({
            'name': 'name',
            'price': 'unit_price',
            'stock': 'available_stock',
            'date': 'created_at'
        })
        
        return self.queryset


class StockOutSearchFilter(SearchFilter):
    """Search and filter for stock out records"""
    
    def apply(self):
        # Search across product name
        self.queryset = self.apply_search([
            'product__name',
            'remarks'
        ])
        
        # Apply filters
        self.queryset = self.apply_filters({
            'reason': 'reason',
            'payment_method': 'payment_method',
            'payment_status': 'payment_status',
            'processed_by': 'processed_by__id'
        })
        
        # Date range
        self.queryset = self.apply_date_range('created_at')
        
        # Apply sorting
        self.queryset = self.apply_sorting({
            'date': 'created_at',
            'product': 'product__name',
            'quantity': 'quantity'
        })
        
        return self.queryset


# Helper function to build filter form options
def get_filter_options(model, field_name, user=None):
    """
    Get distinct values for a field to populate filter dropdowns
    
    Args:
        model: Django model class
        field_name: Field name to get options from
        user: Optional user to filter by
    """
    queryset = model.objects.all()
    
    if user:
        # Apply user-specific filtering if needed
        if hasattr(model, 'owner'):
            queryset = queryset.filter(owner=user)
        elif hasattr(model, 'supplier'):
            queryset = queryset.filter(supplier=user)
    
    return queryset.values_list(field_name, flat=True).distinct().order_by(field_name)


# Advanced search with multiple criteria
def advanced_search(queryset, criteria):
    """
    Perform advanced search with multiple criteria
    
    Args:
        queryset: Base queryset
        criteria: Dict of search criteria
    
    Example:
        criteria = {
            'name__icontains': 'rice',
            'price__gte': 100,
            'price__lte': 500,
            'category': 'grains'
        }
    """
    query = Q()
    
    for key, value in criteria.items():
        if value:
            query &= Q(**{key: value})
    
    return queryset.filter(query)


# Full-text search simulation (for SQLite)
def full_text_search(queryset, search_fields, search_term):
    """
    Simulate full-text search across multiple fields
    
    Args:
        queryset: Base queryset
        search_fields: List of field names to search
        search_term: Search term
    """
    if not search_term:
        return queryset
    
    # Split search term into words
    words = search_term.split()
    
    query = Q()
    for word in words:
        word_query = Q()
        for field in search_fields:
            word_query |= Q(**{f"{field}__icontains": word})
        query &= word_query
    
    return queryset.filter(query)
