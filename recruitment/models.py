from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    COMPANY_SIZE_CHOICES = [
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-500', '201-500 employees'),
        ('500+', '500+ employees'),
    ]
    INDUSTRY_CHOICES = [
        ('IT', 'Information Technology'),
        ('Finance', 'Finance & Banking'),
        ('Healthcare', 'Healthcare'),
        ('Education', 'Education'),
        ('Manufacturing', 'Manufacturing'),
        ('Retail', 'Retail'),
        ('Other', 'Other'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company')
    company_name = models.CharField(max_length=200)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    company_size = models.CharField(max_length=20, choices=COMPANY_SIZE_CHOICES)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    hr_name = models.CharField(max_length=200)
    hr_phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class CandidateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    skills = models.TextField(blank=True, help_text="Comma separated skills")
    experience_years = models.CharField(max_length=10, blank=True)
    education = models.TextField(blank=True)
    resume_file = models.FileField(upload_to='candidate_resumes/', blank=True, null=True)
    raw_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    whatsapp_consent = models.BooleanField(
        default=False,
        help_text="Candidate agreed to receive WhatsApp notifications"
    )

    def get_skills_list(self):
        return [s.strip().lower() for s in self.skills.split(',') if s.strip()]

    def __str__(self):
        return self.full_name


class Job(models.Model):
    EXPERIENCE_CHOICES = [
        ('0-1', '0-1 years'),
        ('1-3', '1-3 years'),
        ('3-5', '3-5 years'),
        ('5+', '5+ years'),
    ]
    JOB_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
        ('internship', 'Internship'),
        ('contract', 'Contract'),
    ]
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE,
        related_name='jobs'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    required_skills = models.TextField(
        help_text="Comma separated skills"
    )
    experience_required = models.CharField(
        max_length=10, choices=EXPERIENCE_CHOICES
    )
    education_required = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    salary_range = models.CharField(max_length=100, blank=True)
    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPE_CHOICES,
        default='full_time'
    )
    openings = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def get_skills_list(self):
        return [
            skill.strip().lower()
            for skill in self.required_skills.split(',')
        ]

    def days_ago(self):
        from django.utils import timezone
        diff = timezone.now() - self.created_at
        days = diff.days
        if days == 0:
            return 'Today'
        elif days == 1:
            return 'Yesterday'
        elif days < 7:
            return f'{days} days ago'
        elif days < 30:
            weeks = days // 7
            return f'{weeks} week{"s" if weeks > 1 else ""} ago'
        else:
            months = days // 30
            return f'{months} month{"s" if months > 1 else ""} ago'

    def str(self):
        return f"{self.title} at {self.company.company_name}"


class Candidate(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='candidates')
    candidate_profile = models.ForeignKey(
        CandidateProfile, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='applications'
    )
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    linkedin_url = models.URLField(blank=True)
    resume_file = models.FileField(upload_to='resumes/')
    extracted_skills = models.TextField(blank=True)
    extracted_experience = models.TextField(blank=True)
    extracted_education = models.TextField(blank=True)
    raw_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def get_skills_list(self):
        return [s.strip().lower() for s in self.extracted_skills.split(',') if s.strip()]

    def __str__(self):
        return f"{self.full_name} - {self.job.title}"


class MatchScore(models.Model):
    candidate = models.OneToOneField(
        Candidate, on_delete=models.CASCADE, related_name='match_score'
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    skills_score = models.FloatField(default=0.0)
    experience_score = models.FloatField(default=0.0)
    education_score = models.FloatField(default=0.0)
    overall_score = models.FloatField(default=0.0)
    is_shortlisted = models.BooleanField(default=False)
    shortlisted_at = models.DateTimeField(null=True, blank=True)
    notification_sent = models.BooleanField(default=False)
    scored_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.candidate.full_name} - {self.overall_score}%"


class JobMatch(models.Model):
    candidate_profile = models.ForeignKey(
        CandidateProfile, on_delete=models.CASCADE, related_name='job_matches'
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    overall_score = models.FloatField(default=0.0)
    skills_score = models.FloatField(default=0.0)
    matched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['candidate_profile', 'job']

    def __str__(self):
        return f"{self.candidate_profile.full_name} - {self.job.title} - {self.overall_score}%"


import pyotp
from django.utils import timezone
from datetime import timedelta

class OTPVerification(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='otp_verification'
    )
    otp_secret = models.CharField(max_length=32, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    user_type = models.CharField(
        max_length=20,
        choices=[('hr', 'HR'), ('candidate', 'Candidate')],
        default='candidate'
    )

    def generate_otp(self):
        self.otp_secret = pyotp.random_base32()
        self.otp_created_at = timezone.now()
        self.is_verified = False
        self.save()
        totp = pyotp.TOTP(self.otp_secret, interval=300)
        return totp.now()

    def verify_otp(self, otp_entered):
        if not self.otp_secret or not self.otp_created_at:
            return False
        expiry = self.otp_created_at + timedelta(minutes=5)
        if timezone.now() > expiry:
            return False
        totp = pyotp.TOTP(self.otp_secret, interval=300)
        return totp.verify(otp_entered)

    def __str__(self):
        return f"OTP for {self.user.username}"

class InterviewSchedule(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ]
    candidate = models.OneToOneField(
        Candidate,
        on_delete=models.CASCADE,
        related_name='interview'
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE
    )
    interview_date = models.DateField()
    interview_time = models.TimeField()
    interview_mode = models.CharField(
        max_length=20,
        choices=[
            ('online', 'Online (Video Call)'),
            ('offline', 'In-Person'),
            ('phone', 'Phone Call'),
        ],
        default='online'
    )
    meeting_link = models.URLField(blank=True)
    interview_location = models.CharField(
        max_length=300, blank=True
    )
    additional_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Interview: {self.candidate.full_name} "
            f"for {self.job.title}"
        )

class CandidateBlacklist(models.Model):
    REASON_CHOICES = [
        ('rejected', 'Rejected by HR'),
        ('deleted', 'Removed by HR'),
        ('fraud', 'Fraudulent Application'),
        ('withdrawn', 'Candidate Withdrew'),
    ]
    email = models.EmailField()
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE,
        related_name='blacklisted_candidates'
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE
    )
    reason = models.CharField(
        max_length=20, choices=REASON_CHOICES,
        default='rejected'
    )
    notes = models.TextField(blank=True)
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['email', 'job']

    def str(self):
        return f"{self.email} blocked from {self.job.title}"


class OfferLetter(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Offer Sent'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]
    candidate = models.OneToOneField(
        Candidate,
        on_delete=models.CASCADE,
        related_name='offer_letter'
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE
    )
    designation = models.CharField(max_length=200)
    salary_package = models.CharField(max_length=100)
    joining_date = models.DateField()
    offer_letter_text = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='sent'
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(
        null=True, blank=True
    )

    def str(self):
        return (
            f"Offer to {self.candidate.full_name} "
            f"for {self.job.title}"
        )


class CandidateNotification(models.Model):
    TYPE_CHOICES = [
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview Scheduled'),
        ('offer', 'Offer Letter'),
        ('rejected', 'Rejected'),
        ('applied', 'Application Received'),
    ]
    candidate_email = models.EmailField()
    notification_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE,
        null=True, blank=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE,
        null=True, blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def str(self):
        return f"{self.notification_type} — {self.candidate_email}"


class InterviewQuestions(models.Model):
    candidate = models.OneToOneField(
        Candidate,
        on_delete=models.CASCADE,
        related_name='interview_questions'
    )
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE
    )
    questions_data = models.JSONField(default=list)
    generated_at = models.DateTimeField(
        auto_now_add=True
    )
    regenerated_count = models.IntegerField(default=0)

    def str(self):
        return (
            f"Questions for {self.candidate.full_name} "
            f"— {self.job.title}"
        )