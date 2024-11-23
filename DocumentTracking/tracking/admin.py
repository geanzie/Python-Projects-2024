from django.contrib import admin
from .models import Profile, Document, DocumentStatus, DocumentActivity

admin.site.register(Profile)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('payee', 'created_by', 'initial_department', 'current_status', 'created_at')
    search_fields = ('payee', 'description', 'created_by__username')
    list_filter = ('current_status', 'initial_department')

@admin.register(DocumentStatus)
class DocumentStatusAdmin(admin.ModelAdmin):
    list_display = ('document', 'department', 'status', 'timestamp')
    list_filter = ('status', 'department')

@admin.register(DocumentActivity)
class DocumentActivityAdmin(admin.ModelAdmin):
    list_display = ('document', 'action', 'performed_by', 'timestamp')
    list_filter = ('action', 'performed_by')
