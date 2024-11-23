from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, Department  # Adjust this import as needed for your project structure

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:  # This is triggered only when a new user is created
        # Create the profile for the user if it doesn't exist
        profile, created = Profile.objects.get_or_create(user=instance)
        
        # Print debug statement to ensure the signal is firing correctly
        print(f"Creating profile for user: {instance.username}")
        
        # Ensure department is being passed correctly
        department_id = instance.profile.department.id if instance.profile and instance.profile.department else None
        
        print(f"Department ID from profile: {department_id}")

        if department_id:
            try:
                department = Department.objects.get(id=department_id)
                profile.department = department  # Assign the department to the profile
                profile.save()
                print(f"Department {department.name} assigned to user.")
            except Department.DoesNotExist:
                print(f"Error: Department with ID {department_id} does not exist.")
        else:
            print("Error: No department assigned to user.")

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    """ Ensure the profile is saved when the user is saved """
    if hasattr(instance, 'profile'):
        print("Saving profile...")
        instance.profile.save()