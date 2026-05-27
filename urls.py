from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/hr/', views.hr_register, name='hr_register'),
    path('register/candidate/', views.candidate_register, name='candidate_register'),

    # HR Dashboard
    path('dashboard/', views.home, name='home'),
    path('jobs/', views.job_list, name='job_list'),
    path('job/<int:job_id>/', views.job_detail, name='job_detail'),
    path('job/create/', views.create_job, name='create_job'),
    path('job/<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('job/<int:job_id>/upload/', views.upload_resume, name='upload_resume'),
    path('job/<int:job_id>/delete/', views.delete_job, name='delete_job'),
    path('job/<int:job_id>/delete-all-candidates/', views.delete_all_candidates, name='delete_all_candidates'),
    path('candidate/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    path('candidate/<int:candidate_id>/delete/', views.delete_candidate, name='delete_candidate'),
    path('analytics/', views.analytics, name='analytics'),

    # Candidate Portal
    path('candidate/dashboard/', views.candidate_dashboard, name='candidate_dashboard'),
    path('candidate/upload-resume/', views.candidate_upload_resume, name='candidate_upload_resume'),

    path('candidate/jobs/', views.candidate_job_list, name='candidate_job_list'),
    path('candidate/apply/<int:job_id>/', views.candidate_apply, name='candidate_apply'),
    path('candidate/job/<int:job_id>/', views.candidate_job_detail, name='candidate_job_detail'),
    path('candidate/profile/edit/', views.candidate_profile_edit, name='candidate_profile_edit'),
    path('company/profile/', views.company_profile, name='company_profile'),
    path('candidate/<int:candidate_id>/export-pdf/', views.export_candidate_pdf, name='export_candidate_pdf'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('candidate/applications/', views.application_tracker, name='application_tracker'),
    path('candidate/notifications/', views.notifications_page, name='notifications_page'),
    path('candidate/<int:candidate_id>/schedule-interview/', views.schedule_interview, name='schedule_interview'),
    path('job/<int:job_id>/recalculate-all/', views.recalculate_all_scores, name='recalculate_all_scores'),
    path('candidate/<int:candidate_id>/recalculate/', views.recalculate_score, name='recalculate_score'),

    # path('candidate/<int:candidate_id>/debug-score/', views.debug_score, name='debug_score'),

    path('candidate/<int:candidate_id>/reject-blacklist/', views.reject_and_blacklist, name='reject_and_blacklist'),
    path('candidate/<int:candidate_id>/offer-letter/', views.send_offer_letter, name='send_offer_letter'),
    path('candidate/<int:candidate_id>/mark-complete/', views.mark_interview_complete, name='mark_interview_complete'),
    path('candidate/<int:candidate_id>/reject-blacklist/', views.reject_and_blacklist, name='reject_and_blacklist'),
    path('candidate/<int:candidate_id>/offer-letter/', views.send_offer_letter, name='send_offer_letter'),
    path('candidate/<int:candidate_id>/mark-complete/', views.mark_interview_complete, name='mark_interview_complete'),
    path('candidate/notifications/mark-read/', views.mark_all_read, name='mark_all_read'),
    path('candidate/<int:candidate_id>/download-offer/', views.download_offer_letter, name='download_offer_letter'),
    path('job/<int:job_id>/kanban/', views.kanban_board, name='kanban_board'),
    path('candidate/<int:candidate_id>/generate-questions/', views.generate_interview_questions, name='generate_interview_questions'),
    path('candidate/interview-prep/<int:job_id>/', views.candidate_interview_prep, name='candidate_interview_prep'),
    path('company/verify-email/', views.verify_company_email, name='verify_company_email'),
    path('company/confirm-email/', views.confirm_company_email, name='confirm_company_email'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/otp/', views.reset_password_otp, name='reset_password_otp'),
    path('reset-password/new/', views.reset_password_new, name='reset_password_new'),

]

# ─── Run FastAPI: python -m uvicorn resume_api:app --reload --port 8001