from django import forms
from django.contrib.auth.models import User
from .models import Document, Department, DocumentStatus
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.forms import widgets


class UserRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'department']

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 != password2:
            raise forms.ValidationError("Passwords do not match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user
    

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['obligation_number','obr_date','expense_class','payee', 'description', 'amount', 'file_upload']

    def __init__(self, *args, **kwargs):
        super(DocumentForm, self).__init__(*args, **kwargs)
        self.fields['obr_date'].widget = widgets.DateInput(attrs={'type': 'date'})
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Create Document'))

from datetime import date
#For accounting
class AccountingForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            'dv_number', 'dv_date', 'net_amount', 
            'six_prcnt', 'five_prcnt', 'three_prcnt', 
            'two_prcnt', 'one_five_prcnt', 
            'one_prcnt_frst', 'one_prcnt_scnd'
        ]
        # Make the percentage fields optional
        six_prcnt = forms.CharField(required=False)
        five_prcnt = forms.CharField(required=False)
        three_prcnt = forms.CharField(required=False)
        two_prcnt = forms.CharField(required=False)
        one_five_prcnt = forms.CharField(required=False)
        one_prcnt_frst = forms.CharField(required=False)
        one_prcnt_scnd = forms.CharField(required=False)
        widgets = {
            'dv_date': forms.DateInput(attrs={'type': 'date'}),
        }

class DocumentStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = DocumentStatus
        fields = ['status', 'department']
    
    status = forms.ChoiceField(
        choices=DocumentStatus.STATUS_CHOICES,
        widget=forms.Select(attrs={'onchange': 'toggleDepartmentDropdown()'})
    )
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=False)