from django.urls import path
from django.contrib.auth import views as auth_views
from . import views, owner_views, supplier_views, admin_views, staff_views, notification_views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('login/', views.login_page, name='login'),
    path('signup/', views.signup_page, name='signup'),
    path('signup/confirmation/', views.signup_confirmation, name='signup_confirmation'),
    path('logout/', views.logout_view, name='logout'),
    path('test-bootstrap/', views.test_bootstrap, name='test_bootstrap'),

    # System Admin Dashboard (custom dashboard for monitoring)
    path('sysadmin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('sysadmin/owners/', admin_views.admin_owners_list, name='admin_owners_list'),
    path('sysadmin/owners/create/', admin_views.admin_owner_create, name='admin_owner_create'),
    path('sysadmin/owners/<int:user_id>/', admin_views.admin_owner_detail, name='admin_owner_detail'),
    path('sysadmin/owners/<int:user_id>/edit/', admin_views.admin_owner_edit, name='admin_owner_edit'),
    path('sysadmin/owners/<int:user_id>/delete/', admin_views.admin_owner_delete, name='admin_owner_delete'),
    path('sysadmin/owners/<int:owner_id>/staff/create/', admin_views.admin_owner_staff_create, name='admin_owner_staff_create'),
    path('sysadmin/suppliers/', admin_views.admin_suppliers_list, name='admin_suppliers_list'),
    path('sysadmin/suppliers/create/', admin_views.admin_supplier_create, name='admin_supplier_create'),
    path('sysadmin/suppliers/<int:user_id>/', admin_views.admin_supplier_detail, name='admin_supplier_detail'),
    path('sysadmin/suppliers/<int:user_id>/edit/', admin_views.admin_supplier_edit, name='admin_supplier_edit'),
    path('sysadmin/suppliers/<int:user_id>/delete/', admin_views.admin_supplier_delete, name='admin_supplier_delete'),
    path('sysadmin/staff/', admin_views.admin_staff_list, name='admin_staff_list'),
    path('sysadmin/staff/create/<int:owner_id>/', admin_views.admin_staff_create, name='admin_staff_create'),
    path('sysadmin/staff/<int:user_id>/', admin_views.admin_staff_detail, name='admin_staff_detail'),
    path('sysadmin/staff/<int:user_id>/edit/', admin_views.admin_staff_edit, name='admin_staff_edit'),
    path('sysadmin/staff/<int:user_id>/delete/', admin_views.admin_staff_delete, name='admin_staff_delete'),
    path('sysadmin/products/', admin_views.admin_products_list, name='admin_products_list'),
    path('sysadmin/orders/', admin_views.admin_orders_list, name='admin_orders_list'),
    path('sysadmin/orders/<int:order_id>/', admin_views.admin_order_detail, name='admin_order_detail'),
    path('sysadmin/logs/', admin_views.admin_activity_logs, name='admin_activity_logs'),
    
    # User Approval Management
    path('sysadmin/pending-users/', admin_views.admin_pending_users, name='admin_pending_users'),
    path('sysadmin/pending-users/<int:user_id>/', admin_views.admin_user_approval_detail, name='admin_user_approval_detail'),
    path('sysadmin/approved-users/', admin_views.admin_approved_users, name='admin_approved_users'),
    
    # Owner Dashboard
    path('owner/dashboard/', owner_views.owner_dashboard, name='owner_dashboard'),
    path('owner/profile/', owner_views.owner_profile, name='owner_profile'),
    
    # Inventory
    path('owner/inventory/', owner_views.inventory_list, name='owner_inventory_list'),
    path('owner/inventory/<int:pk>/delete/', owner_views.inventory_delete, name='owner_inventory_delete'),
    
    # Suppliers (Management Only - Product ordering is done through Browse Products)
    path('owner/suppliers/', owner_views.supplier_list, name='owner_supplier_list'),
    path('owner/suppliers/add/', owner_views.supplier_add, name='owner_supplier_add'),
    path('owner/suppliers/<int:pk>/edit/', owner_views.supplier_edit, name='owner_supplier_edit'),
    path('owner/suppliers/<int:pk>/delete/', owner_views.supplier_delete, name='owner_supplier_delete'),
    
    # Stock Out Management
    path('owner/stock-out/', owner_views.stock_out_form, name='owner_stock_out_form'),
    path('owner/stock-out/report/', owner_views.stock_out_report, name='owner_stock_out_report'),
    
    # Supplier Search & Connection Requests
    path('owner/search-suppliers/', owner_views.search_suppliers, name='owner_search_suppliers'),
    path('owner/connection-request/send/<int:supplier_profile_id>/', owner_views.send_connection_request, name='owner_send_connection_request'),
    path('owner/connection-requests/', owner_views.view_connection_requests, name='owner_view_connection_requests'),
    
    # Browse Supplier Products & Place Orders
    path('owner/browse-products/', owner_views.browse_supplier_products, name='browse_supplier_products'),
    path('owner/supplier-product/<int:pk>/', owner_views.supplier_product_detail, name='supplier_product_detail'),
    path('owner/supplier-orders/', owner_views.owner_supplier_orders, name='owner_supplier_orders'),
    path('owner/supplier-orders/<int:pk>/', owner_views.owner_supplier_order_detail, name='owner_supplier_order_detail'),
    
    # Staff Management (Owner)
    path('owner/staff/', owner_views.staff_list, name='owner_staff_list'),
    path('owner/staff/add/', owner_views.staff_add, name='owner_staff_add'),
    path('owner/staff/<int:staff_id>/edit/', owner_views.staff_edit, name='owner_staff_edit'),
    path('owner/staff/<int:staff_id>/toggle-active/', owner_views.staff_toggle_active, name='owner_staff_toggle_active'),
    path('owner/staff/<int:staff_id>/reset-password/', owner_views.staff_reset_password, name='owner_staff_reset_password'),
    path('owner/staff/<int:staff_id>/delete/', owner_views.staff_delete, name='owner_staff_delete'),
    
    # Payment Verification (Owner)
    path('owner/order/<int:order_id>/update-payment-status/', owner_views.update_payment_status, name='owner_update_payment_status'),
    path('owner/payment-verification-report/', owner_views.owner_payment_verification_report, name='owner_payment_verification_report'),
    
    # Supplier Dashboard
    path('supplier/dashboard/', supplier_views.supplier_dashboard, name='supplier_dashboard'),
    path('supplier/profile/', supplier_views.supplier_profile, name='supplier_profile'),
    
    # Supplier Products
    path('supplier/products/', supplier_views.product_list, name='supplier_product_list'),
    path('supplier/products/add/', supplier_views.product_add, name='supplier_product_add'),
    path('supplier/products/<int:pk>/edit/', supplier_views.product_edit, name='supplier_product_edit'),
    path('supplier/products/<int:pk>/delete/', supplier_views.product_delete, name='supplier_product_delete'),
    
    # Supplier Orders
    path('supplier/orders/', supplier_views.order_list, name='supplier_order_list'),
    path('supplier/orders/<int:pk>/', supplier_views.order_detail, name='supplier_order_detail'),
    
    # Supplier Buyers
    path('supplier/buyers/', supplier_views.buyer_list, name='supplier_buyer_list'),
    path('supplier/buyers/<int:owner_id>/<int:supplier_id>/', supplier_views.buyer_detail, name='supplier_buyer_detail'),
    path('supplier/buyers/<int:owner_id>/<int:supplier_id>/delete/', supplier_views.buyer_delete, name='supplier_buyer_delete'),
    
    # Supplier Connection Requests
    path('supplier/connection-requests/', supplier_views.connection_requests, name='supplier_connection_requests'),
    path('supplier/connection-requests/<int:request_id>/accept/', supplier_views.accept_connection_request, name='supplier_accept_connection_request'),
    path('supplier/connection-requests/<int:request_id>/reject/', supplier_views.reject_connection_request, name='supplier_reject_connection_request'),
    
    # New Supplier Inventory Management
    path('supplier/inventory/', supplier_views.supplier_inventory_list, name='supplier_inventory_list'),
    path('supplier/inventory/add/', supplier_views.supplier_product_add, name='supplier_product_add'),
    path('supplier/inventory/<int:pk>/edit/', supplier_views.supplier_product_edit, name='supplier_product_edit'),
    path('supplier/inventory/<int:pk>/delete/', supplier_views.supplier_product_delete, name='supplier_product_delete'),
    path('supplier/inventory/<int:pk>/restock/', supplier_views.supplier_product_restock, name='supplier_product_restock'),
    
    # Supplier Order Management
    path('supplier/supplier-orders/', supplier_views.supplier_orders_list, name='supplier_orders_list'),
    path('supplier/supplier-orders/<int:pk>/', supplier_views.supplier_order_detail, name='supplier_order_detail'),
    path('supplier/supplier-orders/<int:pk>/update-status/', supplier_views.update_order_delivery_status, name='update_order_delivery_status'),
    
    # Supplier Reports
    path('supplier/reports/', supplier_views.supplier_reports, name='supplier_reports'),
    
    # Payment Verification (Supplier)
    path('supplier/order/<int:order_id>/verify-payment/', supplier_views.verify_payment, name='supplier_verify_payment'),
    path('supplier/payment-verification-report/', supplier_views.payment_verification_report, name='supplier_payment_verification_report'),
    
    # Supplier Payment Information
    path('supplier/payment-info/', supplier_views.supplier_payment_info, name='supplier_payment_info'),
    
    # Staff Dashboard & Views
    path('staff/dashboard/', staff_views.staff_dashboard, name='staff_dashboard'),
    path('staff/inventory/', staff_views.staff_inventory_list, name='staff_inventory_list'),
    path('staff/stock-out/', staff_views.staff_stock_out_form, name='staff_stock_out_form'),
    path('staff/stock-out/report/', staff_views.staff_stock_out_report, name='staff_stock_out_report'),
    path('staff/supplier-orders/', staff_views.staff_supplier_orders, name='staff_supplier_orders'),
    path('staff/supplier-orders/<int:pk>/', staff_views.staff_supplier_order_detail, name='staff_supplier_order_detail'),
    path('staff/profile/', staff_views.staff_profile, name='staff_profile'),
    
    # Notifications and Messages
    path('notifications/', notification_views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/', notification_views.notification_detail, name='notification_detail'),
    path('notifications/<int:pk>/read/', notification_views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', notification_views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:pk>/delete/', notification_views.delete_notification, name='delete_notification'),
    path('api/notifications/', notification_views.get_notifications_json, name='get_notifications_json'),
    path('api/messages/', notification_views.get_messages_json, name='get_messages_json'),
    
    path('messages/', notification_views.message_list, name='message_list'),
    path('messages/conversation/<int:pk>/', notification_views.conversation_detail, name='conversation_detail'),
    path('messages/conversation/<int:pk>/delete/', notification_views.delete_conversation, name='delete_conversation'),
    path('messages/start/<int:user_id>/', notification_views.start_conversation, name='start_conversation'),
    path('messages/order/<int:order_id>/', notification_views.send_message_to_order, name='send_message_to_order'),
]
