from .models import DocumentStatus, Profile

def department_notifications(request):
    if not request.user.is_authenticated:
        return {}
    
    user_department = getattr(request.user.profile, 'department', None)
    if not user_department:
        return {'forwarded_documents_count': 0}

    # Count documents with the status 'Forwarded' for the user's department
    forwarded_documents_count = DocumentStatus.objects.filter(
        department=user_department,
        status='Forwarded',
        document__forwarded_to=user_department
    ).count()

    return {'forwarded_documents_count': forwarded_documents_count}

# tracking/context_processors.py
def notification_context(request):
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_department = request.user.profile.department
        inactive_documents = DocumentStatus.get_inactive_documents(user_department)
        return {'inactive_documents': inactive_documents}
    return {}

def user_department(request):
    if request.user.is_authenticated:
        try:
            return {'user_department': request.user.profile.department.name}
        except AttributeError:
            return {'user_department': None}
    return {'user_department': None}
