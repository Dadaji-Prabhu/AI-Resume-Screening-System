from django.contrib import admin
from .models import Job, Candidate, MatchScore

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'experience_required', 'created_at', 'is_active']
    list_filter = ['experience_required', 'is_active']
    search_fields = ['title', 'required_skills']

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'job', 'uploaded_at']
    list_filter = ['job']
    search_fields = ['full_name', 'email']

@admin.register(MatchScore)
class MatchScoreAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'job', 'overall_score', 'skills_score', 'is_shortlisted']
    list_filter = ['is_shortlisted', 'job']
    ordering = ['-overall_score']