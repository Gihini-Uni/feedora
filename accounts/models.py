from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    CREATOR    = 'creator'
    RESPONDENT = 'respondent'
    ROLE_CHOICES = [
        (CREATOR,    'Form Creator'),
        (RESPONDENT, 'Form Respondent'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.email


class Organization(models.Model):
    ORG_TYPES = [
        ('university', 'University'),
        ('school',     'School'),
        ('company',    'Company'),
        ('research',   'Research Institute'),
        ('other',      'Other'),
    ]
    user      = models.OneToOneField(User, on_delete=models.CASCADE)
    org_name  = models.CharField(max_length=200, blank=True)
    org_type  = models.CharField(max_length=50, choices=ORG_TYPES, blank=True)
    user_role = models.CharField(max_length=100, blank=True)
    country   = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.org_name} ({self.user.email})"


class EmailVerificationCode(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE)
    code       = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from django.utils import timezone
        return (timezone.now() - self.created_at).seconds > 600  # 10 minutes

    def __str__(self):
        return f"Code for {self.user.email}"
    

class CreatorProfile(models.Model):
    user         = models.OneToOneField(User, on_delete=models.CASCADE,
                                        related_name='creator_profile')
    display_name = models.CharField(max_length=100, blank=True)
    company      = models.CharField(max_length=100, blank=True)
    bio          = models.TextField(blank=True)
    website      = models.URLField(blank=True)
    avatar       = models.CharField(max_length=50, default='default')
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} — Creator"


class RespondentProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'), ('F', 'Female'),
        ('NB', 'Non-binary'), ('NS', 'Prefer not to say'),
    ]
    AGE_CHOICES = [
        ('under18', 'Under 18'), ('18-24', '18–24'),
        ('25-34', '25–34'), ('35-44', '35–44'), ('45+', '45+'),
    ]
    user         = models.OneToOneField(User, on_delete=models.CASCADE,
                                        related_name='respondent_profile')
    display_name = models.CharField(max_length=100, blank=True)
    company      = models.CharField(max_length=100, blank=True)
    gender       = models.CharField(max_length=5, choices=GENDER_CHOICES, blank=True)
    age_group    = models.CharField(max_length=10, choices=AGE_CHOICES, blank=True)
    avatar       = models.CharField(max_length=50, default='default')
    total_points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.email} — Respondent"
    