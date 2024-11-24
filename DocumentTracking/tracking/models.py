from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
from django.core.validators import RegexValidator

# Department Model
class Department(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="Name of the department")
    
    def __str__(self):
        return self.name

class Document(models.Model):
    # Document Information
    obligation_number = models.CharField(
    max_length=14,
    validators=[RegexValidator(regex=r'^\d{3}-\d{2}-\d{2}-\d{4}$', message='Serial number must be in the format 000-00-00-0000')], 
    help_text="Enter the obligation number in the format 000-00-00-0000.")
    payee = models.CharField(max_length=255, help_text="Payee of the document")
    description = models.TextField(blank=True, help_text="Brief description of the document")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    file_upload = models.FileField(upload_to='documents/', help_text="Upload the document file")
    
    # Metadata
    created_by = models.ForeignKey(User, related_name='created_documents', on_delete=models.SET_NULL, null=True, help_text="User who uploaded the document")
    
    # Initial Department
    initial_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='encoder_department', help_text="Department from which the document was encoded")
    
    # Forwarded Department
    forwarded_to = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='forwarded_documents', help_text="Department to which the document is forwarded")
    
    current_status = models.CharField(max_length=50)  # Set as default status
    created_at = models.DateTimeField(auto_now_add=True)


    def set_initial_status(self):
        """Set the initial status of the document."""
        self.current_status = 'In Process'
        self.save()

class DocumentStatus(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Process', 'In Process'),
        ('Returned', 'Returned'),
        ('Forwarded', 'Forwarded'),
        ('Released', 'Released'),   
    ]
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='statuses')
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    history = HistoricalRecords()  # This line enables version history for this model

class DocumentActivity(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} by {self.performed_by.username} on {self.timestamp}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)  # Example field

    def __str__(self):
        return f"{self.user.username} - {self.department}"