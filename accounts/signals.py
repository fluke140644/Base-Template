"""
accounts/signals.py
————————————————————
• Auto-create UserProfile whenever a new User is created.
• Keep User.first_name / last_name in sync with UserProfile on save.
"""
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Ensure every User has exactly one UserProfile."""
    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'first_name': instance.first_name,
                'last_name': instance.last_name,
            },
        )


@receiver(post_save, sender=User)
def sync_user_names_to_profile(sender, instance, created, **kwargs):
    """Keep profile first/last name updated when User is saved."""
    if not created:
        profile = getattr(instance, 'profile', None)
        if profile:
            changed = False
            if instance.first_name and profile.first_name != instance.first_name:
                profile.first_name = instance.first_name
                changed = True
            if instance.last_name and profile.last_name != instance.last_name:
                profile.last_name = instance.last_name
                changed = True
            if changed:
                profile.save(update_fields=['first_name', 'last_name'])
