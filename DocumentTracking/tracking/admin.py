from django.contrib import admin
from .models import Profile, Document, DocumentStatus, DocumentActivity

admin.site.register(Profile)

admin.site.register(Document)

@admin.register(DocumentStatus)
class DocumentStatusAdmin(admin.ModelAdmin):
    list_display = ('document', 'department', 'status', 'timestamp')
    list_filter = ('status', 'department')

@admin.register(DocumentActivity)
class DocumentActivityAdmin(admin.ModelAdmin):
    list_display = ('document', 'action', 'performed_by', 'timestamp')
    list_filter = ('action', 'performed_by')
