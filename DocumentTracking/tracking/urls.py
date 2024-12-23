from django.urls import path
from . import views 
from .views import (
    DashboardView,
    DocumentListView,
    DocumentCreateView,
    DocumentUpdateView,
    DocumentActivityView,
    UserLoginView,
    UserLogoutView,
    DocumentReceivedView,
    DocumentDetailView,
    DocumentSearchView,
    UserProfileView,
    DocumentHistoryView,
    UserRegistrationView, 
    DocumentEditView,
    DocumentUpdateStatusView,
    CheckDocumentStatusUpdates,
    DashboardStatusListView,
    UpdateDVFieldsView,
    UpdateObligationRequestView,
    VoucherListView,
    ResponsibilityCenterListView,
)

urlpatterns = [
    path('accounts/login/', UserLoginView.as_view(), name='login'),  # User login
    path('', DashboardView.as_view(), name='dashboard'),  # Dashboard
    path('register/', UserRegistrationView.as_view(), name='register'),  # User registration
    path('logout/', UserLogoutView.as_view(), name='logout'),  # User logout
    path('documents/', DocumentListView.as_view(), name='document_list'),  # List of documents
    path('documents/create/', DocumentCreateView.as_view(), name='document_create'),  # Create document
    path('documents/<int:pk>/update/', DocumentUpdateView.as_view(), name='document_update'),  # Update document
    path('documents/<int:pk>/receive/', DocumentReceivedView.as_view(), name='document_received'),  # Receive document
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='document_detail'),  # Document detail
    path('documents/search/', DocumentSearchView.as_view(), name='document_search'),  # Document search
    path('profile/', UserProfileView.as_view(), name='user_profile'),  # User profile
    path('documents/<int:pk>/history/', DocumentHistoryView.as_view(), name='document_history'),  # Document history
    path('activity/', DocumentActivityView.as_view(), name='document_activity'),  # Document activity log

    path('documents/<int:pk>/update-dv-fields/', UpdateDVFieldsView.as_view(), name='update_dv_fields'),
    path('dashboard/status-list/', DashboardStatusListView.as_view(), name='dashboard_status_list'),
    path('document-activities/<str:obligation_number>/', views.document_activity_detail, name='document_activity_detail'),
    path('documents/edit/<int:pk>/', DocumentEditView.as_view(), name='document_edit'),
    path('documents/update-status/<int:pk>/', DocumentUpdateStatusView.as_view(), name='document_update_status'),
    path('documents/check_status_updates/', CheckDocumentStatusUpdates.as_view(), name='check_document_status_updates'),
    path('documents/<str:status>/', DocumentListView.as_view(), name='view_documents_with_status'),  # New pattern
    path('documents/<int:pk>/update_ob_fields/', UpdateObligationRequestView.as_view(), name='update_ob_fields'),
     path('vouchers/', VoucherListView.as_view(), name='voucher_list'),
    path('vouchers/<int:pk>/responsibility-centers/', ResponsibilityCenterListView.as_view(), name='responsibility_center_list'),
]