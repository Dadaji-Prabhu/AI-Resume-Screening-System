from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Company, CandidateProfile


class HRRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    hr_name = forms.CharField(max_length=200, label="Your Full Name")
    hr_phone = forms.CharField(max_length=20, label="Your Phone Number")
    company_name = forms.CharField(max_length=200)
    industry = forms.ChoiceField(choices=Company.INDUSTRY_CHOICES)
    company_size = forms.ChoiceField(choices=Company.COMPANY_SIZE_CHOICES)
    website = forms.URLField(required=False, label="Company Website (optional)")
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Company Description (optional)"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Company.objects.create(
                user=user,
                hr_name=self.cleaned_data['hr_name'],
                hr_phone=self.cleaned_data['hr_phone'],
                company_name=self.cleaned_data['company_name'],
                industry=self.cleaned_data['industry'],
                company_size=self.cleaned_data['company_size'],
                website=self.cleaned_data.get('website', ''),
                description=self.cleaned_data.get('description', ''),
            )
        return user


class CandidateRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    full_name = forms.CharField(max_length=200)
    phone = forms.CharField(max_length=20)
    linkedin_url = forms.URLField(required=False, label="LinkedIn Profile URL (optional)")
    github_url = forms.URLField(required=False, label="GitHub URL (optional)")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            CandidateProfile.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name'],
                phone=self.cleaned_data['phone'],
                linkedin_url=self.cleaned_data.get('linkedin_url', ''),
                github_url=self.cleaned_data.get('github_url', ''),
            )
        return user


class JobForm(forms.ModelForm):
    class Meta:
        model = __import__('recruitment.models', fromlist=['Job']).Job
        fields = [
            'title', 'description', 'required_skills',
            'experience_required', 'education_required',
            'location', 'salary_range'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class ResumeUploadForm(forms.Form):
    resume_file = forms.FileField(
        label="Upload Resume (PDF or DOCX)",
        help_text="Maximum file size: 5MB"
    )
    linkedin_url = forms.URLField(
        required=False,
        label="LinkedIn Profile URL (optional)"
    )