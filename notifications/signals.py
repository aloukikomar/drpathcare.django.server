from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Enquiry
from notifications.utils.push_service import send_expo_push_notification # Ensure this matches your util filename

User = get_user_model()

@receiver(post_save, sender=Enquiry)
def notify_staff_on_new_enquiry(sender, instance, created, **kwargs):
    """
    Triggers a push notification to all Admins and Verifiers 
    whenever a new Enquiry is created.
    """
    if created:
        # 1. Filter the relevant users
        # Adjust 'role' to match your actual User model field name
        staff_members = User.objects.filter(role__name__in=['Admin', 'Verifier'], is_active=True).values_list('id')

        # 2. Prepare the notification details
        title = "New Enquiry Alert 📋"
        message = f"Enquiry: {instance.name} is asking about: {instance.enquiry[:50]}..."
        
        # 3. Extra data for deep-linking in React Native
        extra_data = {
            "type": "NEW_ENQUIRY",
            "enquiry_id": instance.id,
            "mobile": instance.mobile
        }

        # 4. Loop and send
        # for staff in staff_members:
        send_expo_push_notification(
            user_ids=list(staff_members),
            title=title,
            body=message,
            extra_data=extra_data
        )