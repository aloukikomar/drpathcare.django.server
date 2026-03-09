import requests
from django.conf import settings
from notifications.models import PushDevice

def send_expo_push_notification(user_ids, title, body, extra_data=None):
    """
    Sends push notifications to specific users via Expo.
    user_ids: List of User IDs
    """
    # 1. Fetch all active tokens for these specific users
    devices = PushDevice.objects.filter(
        user_id__in=user_ids, 
        is_active=True
    ).values_list('expo_push_token', flat=True)

    if not devices:
        return None

    # 2. Construct messages
    messages = []
    for token in devices:
        messages.append({
            "to": token,
            "title": title,
            "body": body,
            "data": extra_data or {},
            "sound": "default",
            "priority": "high"
        })

    # 3. Batch send to Expo
    try:
        response = requests.post(
            "https://exp.host/--/api/v2/push/send",
            json=messages,
            timeout=10
        )
        return response.json()
    except Exception as e:
        print(f"Push Notification Error: {e}")
        return None