from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
from django.core.validators import RegexValidator
from decimal import Decimal
from datetime import date

# Department Model
class Department(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="Name of the department")
    
    def __str__(self):
        return self.name

class AccountCode(models.Model):
    expense_class = models.CharField(max_length=45)
    account_codes = models.CharField(max_length=45)

    def __str__(self):
        return self.account_codes
    
class ResponseCenter(models.Model):
    centre_code = models.CharField(max_length=45)

    def __str__(self):
        return self.centre_code
    
class Document(models.Model):
    # Document Information
    obligation_number = models.CharField(
    max_length=14, unique=True,
    validators=[RegexValidator(regex=r'^\d{3}-\d{2}-\d{2}-\d{4}$', message='Number must be in the format 000-00-00-0000')], verbose_name="Obligation Request Number")  # Set a default value
    obr_date = models.DateField(default=date.today, verbose_name="Obligation Request Date")
    EXPENSE_CHOICES = [
    ('MOOE', 'MOOE'),
    ('PS', 'PS'),
    ('CO', 'CO'),
    ]
    expense_class = models.CharField(max_length=10, help_text="Expense Class", choices=EXPENSE_CHOICES, null=True, verbose_name="Expense Class")
    rc_code = models.ForeignKey(ResponseCenter, on_delete=models.SET_NULL, help_text="Responsibility Center", null=True, verbose_name="Responsibility Center")
    account_code = models.ForeignKey(AccountCode, on_delete=models.SET_NULL, help_text="Account Code", null=True, verbose_name="Account Code")
    payee = models.CharField(max_length=255, help_text="Payee of the Document")
    description = models.TextField(help_text="Description of the Document", error_messages="This field is required.", blank=False)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    file_upload = models.FileField(upload_to='documents/', help_text="Upload the document file")
        
    # Initial Department
    initial_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='encoder_department', help_text="Department from which the document was encoded")
    
    # Forwarded Department
    forwarded_to = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='forwarded_documents', help_text="Department to which the document is forwarded")
    
    current_status = models.CharField(max_length=50)  # Set as default status
    created_at = models.DateTimeField(auto_now_add=True)

    def set_initial_status(self):
        """Set the initial status of the document."""
        self.current_status = 'In Process'
        self.save()

    #New tables to accommodate the other system in treasury
    net_amount = models.DecimalField(max_digits=12, decimal_places=2,  default=Decimal('0.00'), verbose_name="Net Amount")
    six_prcnt = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    five_prcnt = models.DecimalField(max_digits=12, decimal_places=2,  default=Decimal('0.00'))
    three_prcnt = models.DecimalField(max_digits=12, decimal_places=2,  default=Decimal('0.00'))
    two_prcnt = models.DecimalField(max_digits=12, decimal_places=2,  default=Decimal('0.00'))
    one_five_prcnt = models.DecimalField(max_digits=12, decimal_places=2,  default=Decimal('0.00'))
    one_prcnt_frst = models.DecimalField(max_digits=12, decimal_places=2,  default=Decimal('0.00'))
    one_prcnt_scnd = models.DecimalField(max_digits=12, decimal_places=2,  default=Decimal('0.00'))
    dv_number = models.CharField(
        max_length=14,
        validators=[RegexValidator(regex=r'^\d{3}-\d{2}-\d{2}-\d{4}$', message='Number must be in the format 000-00-00-0000')], verbose_name="Disbursement Voucher Number")  
    dv_date = models.DateField(null=True, verbose_name="Disbursement Voucher Date")



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