# Generated by Django 4.2.16 on 2024-11-29 15:14

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0008_alter_document_expense_class_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='phone_number',
            field=models.CharField(blank=True, help_text="Enter the phone number for notifications in the format '09123456789'.", max_length=11, null=True, validators=[django.core.validators.RegexValidator(message="Phone number must start with '09' and be 11 digits long.", regex='^09\\d{9}$')]),
        ),
    ]
