from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from .models import (
    Job, Candidate, MatchScore, Company,
    CandidateProfile, JobMatch, OTPVerification,
    InterviewSchedule, CandidateBlacklist, OfferLetter, CandidateNotification,
    LoginAttempt
)
from .resume_parser import parse_resume, calculate_overall_score
from .forms import (
    HRRegistrationForm, CandidateRegistrationForm,
    JobForm, ResumeUploadForm
)
import os
import re
import requests
import urllib.parse

from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_control

from .offer_letter_generator import generate_offer_letter_pdf
from .question_generator import generate_questions
from .models import InterviewQuestions

# HELPER FUNCTIONS
def redirect_user_based_on_role(user):
    try:
        user.company
        return redirect('home')
    except Company.DoesNotExist:
        pass
    try:
        user.candidate_profile
        return redirect('candidate_dashboard')
    except CandidateProfile.DoesNotExist:
        return redirect('candidate_register')


def get_company(request):
    try:
        return request.user.company
    except Company.DoesNotExist:
        return None


def safe_calculate_score(candidate, job):
    """
    Single source of truth for score calculation.
    Uses ML model for overall, NLP for breakdown.
    Always uses update_or_create to avoid duplicates.
    """
    try:
        print(f"\n--- Scoring: {candidate.full_name} → {job.title} ---")
        print(f"  Raw text  : {len(candidate.raw_text or '')} chars")
        print(f"  Skills    : {(candidate.extracted_skills or '')[:60]}")

        # Step 1: NLP breakdown scores (always calculated)
        try:
            nlp_scores = calculate_overall_score(candidate, job)
            print(f"  NLP scores: {nlp_scores}")
        except Exception as e:
            print(f"  NLP error : {e}")
            # Manual fallback
            from .resume_parser import (
                calculate_skills_score,
                calculate_experience_score,
                calculate_education_score,
            )
            try:
                sk = calculate_skills_score(
                    candidate.get_skills_list(),
                    job.get_skills_list()
                )
            except Exception:
                sk = 0.0
            try:
                ex = calculate_experience_score(
                    candidate.extracted_experience or '',
                    job.experience_required or '0-1'
                )
            except Exception:
                ex = 30.0
            try:
                ed = calculate_education_score(
                    candidate.extracted_education or '',
                    job.education_required or ''
                )
            except Exception:
                ed = 0.0
            nlp_scores = {
                'skills_score': sk,
                'experience_score': ex,
                'education_score': ed,
                'overall_score': round(sk * 0.4 + ex * 0.25 + ed * 0.2, 2),
            }

        # Step 2: ML overall score
        ml_overall = nlp_scores['overall_score']
        api_success = False
        raw_text = (candidate.raw_text or '').strip()

        if raw_text and len(raw_text) > 50:
            try:
                extracted_skills_list = [
                    s.strip() for s in
                    (candidate.extracted_skills or '').split(',')
                    if s.strip()
                ]
                response = requests.post(
                    "http://127.0.0.1:8001/score_resume",
                    json={
                        "resume_text": raw_text,
                        "job_description": job.description or '',
                        "required_skills": job.get_skills_list(),
                        "extracted_skills": extracted_skills_list,
                        "experience_required": job.experience_required or 'any'
                    },
                    timeout=8
                )
                result = response.json()
                if result.get("status") == "success":
                    ml_overall = result["final_score"]
                    api_success = True
                    print(f"  ML overall: {ml_overall}% ✅")
                else:
                    print(f"  ML API error: {result.get('status')}")
            except requests.exceptions.ConnectionError:
                print("  FastAPI not running, using NLP")
            except Exception as e:
                print(f"  ML exception: {e}")
        else:
            print("  No raw text, using NLP only")

        source = "ML" if api_success else "NLP"
        print(f"  Source    : {source}, Final: {ml_overall}%")

        # Step 3: Save — ML overall + NLP breakdown
        score_obj, created = MatchScore.objects.update_or_create(
            candidate=candidate,
            defaults={
                'job': job,
                'skills_score': round(nlp_scores['skills_score'], 2),
                'experience_score': round(nlp_scores['experience_score'], 2),
                'education_score': round(nlp_scores['education_score'], 2),
                'overall_score': round(ml_overall, 2),
            }
        )
        action = "Created" if created else "Updated"
        print(f"  {action} → Overall:{score_obj.overall_score}% "
              f"Skills:{score_obj.skills_score}% "
              f"Exp:{score_obj.experience_score}% "
              f"Edu:{score_obj.education_score}%")
        return score_obj

    except Exception as e:
        import traceback
        print(f"  safe_calculate_score FAILED: {e}")
        traceback.print_exc()
        return None


def auto_calculate_score(candidate, job):
    """Called automatically in job_detail when score is missing."""
    return safe_calculate_score(candidate, job)


# EMAIL / NOTIFICATION HELPERS
def send_otp_email(user, otp_code, user_type):
    subject = 'HireIQ — Your OTP Verification Code'
    message = f'''
Dear {user.username},

Your OTP verification code for HireIQ is:

    ━━━━━━━━━━━━━━━━
         {otp_code}
    ━━━━━━━━━━━━━━━━

This code is valid for 5 minutes only.
Do not share this code with anyone.

Best regards,
HireIQ Team
    '''
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
              [user.email], fail_silently=False)


def send_rejection_notification(candidate, company):
    try:
        subject = f'Update on your application — {company.company_name}'
        message = f'''
Dear {candidate.full_name},

Thank you for applying for {candidate.job.title} at {company.company_name}.

After careful consideration, we will not be moving forward with your
application at this time. We encourage you to apply for future openings.

Best wishes,
{company.hr_name}
{company.company_name} | HireIQ Platform
        '''
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  [candidate.email], fail_silently=True)
    except Exception:
        pass


def generate_whatsapp_url(candidate, company):
    message = (
        f"Hello {candidate.full_name}! Congratulations! "
        f"You have been shortlisted for {candidate.job.title} "
        f"at {company.company_name}. "
        f"Our HR will contact you soon. - {company.hr_name}"
    )
    encoded = urllib.parse.quote(message)
    phone = candidate.phone.replace('+', '').replace(' ', '').replace('-', '')
    return f"https://wa.me/{phone}?text={encoded}"


def send_interview_notification(interview, company, action):
    from datetime import datetime
    candidate = interview.candidate

    if isinstance(interview.interview_date, str):
        try:
            interview_date = datetime.strptime(interview.interview_date, '%Y-%m-%d')
        except ValueError:
            interview_date = datetime.strptime(interview.interview_date, '%d-%m-%Y')
    else:
        interview_date = interview.interview_date

    if isinstance(interview.interview_time, str):
        try:
            interview_time = datetime.strptime(interview.interview_time, '%H:%M')
        except ValueError:
            interview_time = datetime.strptime(interview.interview_time, '%I:%M %p')
    else:
        interview_time = interview.interview_time

    date_str = interview_date.strftime('%B %d, %Y')
    time_str = interview_time.strftime('%I:%M %p')

    mode_display = {
        'online': 'Online (Video Call)',
        'offline': 'In-Person',
        'phone': 'Phone Call',
    }.get(interview.interview_mode, interview.interview_mode)

    action_word = 'Scheduled' if action == 'scheduled' else 'Rescheduled'

    location_info = ''
    if interview.interview_mode == 'online' and interview.meeting_link:
        location_info = f'  Meeting Link : {interview.meeting_link}'
    elif interview.interview_mode == 'offline' and interview.interview_location:
        location_info = f'  Location     : {interview.interview_location}'
    elif interview.interview_mode == 'phone':
        location_info = '  Mode         : Phone Call (HR will call you)'

    subject = f'📅 Interview {action_word} — {interview.job.title} at {company.company_name}'

    message = f'''
Dear {candidate.full_name},

Your interview has been {action_word.lower()} for {interview.job.title}
at {company.company_name}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERVIEW DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Position : {interview.job.title}
  Company  : {company.company_name}
  Date     : {date_str}
  Time     : {time_str}
  Mode     : {mode_display}
{location_info}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HR Contact: {company.hr_name} | {company.hr_phone}

Best regards,
{company.company_name} | HireIQ
    '''

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [candidate.email],
            fail_silently=False
        )
        print(f"Interview email sent to {candidate.email}")

        # Create dashboard notification
        create_candidate_notification(
            candidate_email=candidate.email,
            notification_type='interview',
            title=f'📅 Interview {action_word} — {interview.job.title}',
            message=(
                f'Your interview for {interview.job.title} at '
                f'{company.company_name} has been {action_word.lower()}. '
                f'Date: {date_str} | Time: {time_str} | '
                f'Mode: {mode_display}. '
                f'HR Contact: {company.hr_name} ({company.hr_phone}).'
            ),
            job=interview.job,
            company=company,
        )

        print(f"Interview notification created for {candidate.email}")

    except Exception as e:
        print(f"Interview email error: {e}")


def generate_interview_whatsapp_url(interview, company):
    from datetime import datetime
    import urllib.parse

    candidate = interview.candidate
    if isinstance(interview.interview_date, str):
        try:
            interview_date = datetime.strptime(interview.interview_date, '%Y-%m-%d')
        except ValueError:
            interview_date = datetime.strptime(interview.interview_date, '%d-%m-%Y')
    else:
        interview_date = interview.interview_date

    if isinstance(interview.interview_time, str):
        try:
            interview_time = datetime.strptime(interview.interview_time, '%H:%M')
        except ValueError:
            interview_time = datetime.strptime(interview.interview_time, '%I:%M %p')
    else:
        interview_time = interview.interview_time

    date_str = interview_date.strftime('%B %d, %Y')
    time_str = interview_time.strftime('%I:%M %p')

    if interview.interview_mode == 'online' and interview.meeting_link:
        mode_info = f'Link: {interview.meeting_link}'
    elif interview.interview_mode == 'offline':
        mode_info = f'Location: {interview.interview_location}'
    else:
        mode_info = 'Mode: Phone Call'

    message = (
        f"Dear {candidate.full_name}, your interview for "
        f"{interview.job.title} at {company.company_name} is scheduled! "
        f"Date: {date_str}, Time: {time_str}. {mode_info}. "
        f"Contact: {company.hr_name} ({company.hr_phone}). Good luck!"
    )

    encoded = urllib.parse.quote(message)
    phone = candidate.phone.replace('+', '').replace(' ', '').replace('-', '')
    return f"https://wa.me/{phone}?text={encoded}"


def match_new_job_with_candidates(job):
    """When a new job is posted, match against all candidate profiles."""
    from .resume_parser import calculate_skills_score, calculate_text_similarity
    profiles = CandidateProfile.objects.filter(
        resume_file__isnull=False
    ).exclude(resume_file='')
    matched = 0
    print(f"\nMatching new job '{job.title}' against {profiles.count()} profiles...")
    for profile in profiles:
        if JobMatch.objects.filter(candidate_profile=profile, job=job).exists():
            continue
        if not profile.raw_text:
            continue
        skills_score = calculate_skills_score(
            profile.get_skills_list(), job.get_skills_list()
        )
        if skills_score == 0:
            continue
        ml_score = 0
        api_success = False
        try:
            extracted_skills_list = [
                s.strip() for s in profile.skills.split(',') if s.strip()
            ]
            response = requests.post(
                "http://127.0.0.1:8001/score_resume",
                json={
                    "resume_text": profile.raw_text,
                    "job_description": job.description,
                    "required_skills": job.get_skills_list(),
                    "extracted_skills": extracted_skills_list,
                    "experience_required": job.experience_required
                },
                timeout=8
            )
            result = response.json()
            if result.get("status") == "success":
                ml_score = result["final_score"]
                api_success = True
        except Exception as e:
            print(f"  ML error for {profile.full_name}: {e}")
        if not api_success:
            text_score = calculate_text_similarity(profile.raw_text, job.description)
            ml_score = round(skills_score * 0.6 + text_score * 0.4, 2)
        if ml_score > 15 or skills_score > 20:
            JobMatch.objects.create(
                candidate_profile=profile,
                job=job,
                overall_score=round(ml_score, 2),
                skills_score=round(skills_score, 2),
            )
            matched += 1
            print(f"  ✅ {profile.full_name}: {round(ml_score, 2)}%")
    print(f"Matched {matched} candidates for '{job.title}'")

# AUTH VIEWS
@never_cache
def landing(request):
    if request.user.is_authenticated:
        return redirect_user_based_on_role(request.user)

    # Live platform stats
    total_companies = Company.objects.count()
    total_jobs = Job.objects.filter(is_active=True).count()
    total_candidates = CandidateProfile.objects.count()
    total_hired = MatchScore.objects.filter(
        is_shortlisted=True
    ).count()

    return render(request, 'recruitment/landing.html', {
        'total_companies': total_companies,
        'total_jobs': total_jobs,
        'total_candidates': total_candidates,
        'total_hired': total_hired,
    })

def hr_register(request):
    if request.user.is_authenticated:
        return redirect_user_based_on_role(request.user)
    if request.method == 'POST':
        form = HRRegistrationForm(request.POST)
        if form.is_valid():
            temp_username = form.cleaned_data['username']
            temp_email = form.cleaned_data['email']
            if User.objects.filter(username=temp_username).exists():
                messages.error(request, 'Username already exists.')
                return render(request, 'recruitment/hr_register.html', {'form': form})
            if User.objects.filter(email=temp_email).exists():
                messages.error(request, 'Email already registered.')
                return render(request, 'recruitment/hr_register.html', {'form': form})
            hr_phone = form.cleaned_data.get('hr_phone', '')
            if hr_phone:
                is_valid, result = validate_phone(hr_phone)
                if not is_valid:
                    messages.error(request, f'Phone: {result}')
                    return render(
                        request,
                        'recruitment/hr_register.html',
                        {'form': form}
                    )
            temp_user = User.objects.create_user(
                username=temp_username, email=temp_email,
                password=form.cleaned_data['password1'], is_active=False
            )


            otp_obj, _ = OTPVerification.objects.get_or_create(
                user=temp_user, defaults={'user_type': 'hr'}
            )
            otp_code = otp_obj.generate_otp()
            try:
                send_otp_email(temp_user, otp_code, 'hr')
                request.session['hr_register_data'] = request.POST.dict()
                request.session['otp_user_id'] = temp_user.id
                request.session['otp_user_type'] = 'hr'
                messages.success(request, f'OTP sent to {temp_email}. Valid for 5 minutes.')
                return redirect('verify_otp')
            except Exception as e:
                temp_user.delete()
                messages.error(request, 'Could not send OTP. Check email settings.')
        else:
            messages.error(request, 'Please fix the errors below.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = HRRegistrationForm()
    return render(request, 'recruitment/hr_register.html', {'form': form})


def candidate_register(request):
    if request.user.is_authenticated:
        try:
            request.user.company
            return redirect('home')
        except Company.DoesNotExist:
            pass
        try:
            request.user.candidate_profile
            return redirect('candidate_dashboard')
        except CandidateProfile.DoesNotExist:
            pass
    if request.method == 'POST':
        form = CandidateRegistrationForm(request.POST)
        if form.is_valid():
            temp_username = form.cleaned_data['username']
            temp_email = form.cleaned_data['email']
            if User.objects.filter(username=temp_username).exists():
                messages.error(request, 'Username already exists.')
                return render(request, 'recruitment/candidate_register.html', {'form': form})
            if User.objects.filter(email=temp_email).exists():
                messages.error(request, 'Email already registered.')
                return render(request, 'recruitment/candidate_register.html', {'form': form})
            request.session['candidate_register_data'] = request.POST.dict()

            phone = form.cleaned_data.get('phone', '')
            if phone:
                is_valid, result = validate_phone(phone)
                if not is_valid:
                    messages.error(request, f'Phone: {result}')
                    return render(
                        request,
                        'recruitment/candidate_register.html',
                        {'form': form}
                    )

            temp_user = User.objects.create_user(
                username=temp_username, email=temp_email,
                password=form.cleaned_data['password1'], is_active=False
            )
            otp_obj, _ = OTPVerification.objects.get_or_create(
                user=temp_user, defaults={'user_type': 'candidate'}
            )
            otp_code = otp_obj.generate_otp()
            try:
                send_otp_email(temp_user, otp_code, 'candidate')
                request.session['otp_user_id'] = temp_user.id
                request.session['otp_user_type'] = 'candidate'
                messages.success(request, f'OTP sent to {temp_email}. Valid for 5 minutes.')
                return redirect('verify_otp')
            except Exception as e:
                temp_user.delete()
                messages.error(request, 'Could not send OTP. Check your email address.')
        else:
            messages.error(request, 'Please fix the errors below.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CandidateRegistrationForm()
    return render(request, 'recruitment/candidate_register.html', {'form': form})


def verify_otp(request):
    user_id = request.session.get('otp_user_id')
    user_type = request.session.get('otp_user_type')
    if not user_id:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('landing')
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'resend':
            try:
                otp_obj = user.otp_verification
                otp_code = otp_obj.generate_otp()
                send_otp_email(user, otp_code, user_type)
                messages.success(request, 'New OTP sent!')
            except Exception:
                messages.error(request, 'Could not resend OTP.')
            return redirect('verify_otp')
        otp_entered = request.POST.get('otp_code', '').strip()
        try:
            otp_obj = user.otp_verification
        except OTPVerification.DoesNotExist:
            messages.error(request, 'OTP not found. Please register again.')
            user.delete()
            return redirect('landing')
        if otp_obj.verify_otp(otp_entered):
            user.is_active = True
            user.save()
            otp_obj.is_verified = True
            otp_obj.save()
            if user_type == 'hr':
                data = request.session.get('hr_register_data', {})
                Company.objects.create(
                    user=user,
                    hr_name=data.get('hr_name', ''),
                    hr_phone=data.get('hr_phone', ''),
                    company_name=data.get('company_name', ''),
                    industry=data.get('industry', 'IT'),
                    company_size=data.get('company_size', '1-10'),
                    website=data.get('website', ''),
                    description=data.get('description', ''),
                )
                login(request, user)
                for key in ['otp_user_id', 'otp_user_type', 'hr_register_data']:
                    request.session.pop(key, None)
                messages.success(request, 'Company account verified and ready!')
                return redirect('home')
            elif user_type == 'candidate':
                data = request.session.get('candidate_register_data', {})
                CandidateProfile.objects.create(
                    user=user,
                    full_name=data.get('full_name', ''),
                    phone=data.get('phone', ''),
                    linkedin_url=data.get('linkedin_url', ''),
                    github_url=data.get('github_url', ''),
                    whatsapp_consent=data.get('whatsapp_consent') == 'on',
                )
                login(request, user)
                for key in ['otp_user_id', 'otp_user_type', 'candidate_register_data']:
                    request.session.pop(key, None)
                messages.success(request, 'Account verified! Upload your resume to get matches.')
                return redirect('candidate_upload_resume')
        else:
            messages.error(request, 'Invalid or expired OTP. Try again or resend.')
    return render(request, 'recruitment/verify_otp.html', {
        'email': user.email, 'user_type': user_type,
    })


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect_user_based_on_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Get IP address
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '')
            .split(',')[0].strip() or
            request.META.get('REMOTE_ADDR', '')
        )

        # Check recent failed attempts — last 15 minutes
        from django.utils import timezone
        import datetime
        window = timezone.now() - datetime.timedelta(
            minutes=15
        )
        recent_failures = LoginAttempt.objects.filter(
            username=username,
            was_successful=False,
            attempt_time__gte=window
        ).count()

        if recent_failures >= 5:
            messages.error(
                request,
                '🔒 Account temporarily locked due to too '
                'many failed attempts. '
                'Please try again after 15 minutes or '
                'use Forgot Password.'
            )
            return render(
                request, 'recruitment/login.html'
            )

        user = authenticate(
            request, username=username, password=password
        )

        if user is not None:
            # Record successful attempt
            LoginAttempt.objects.create(
                username=username,
                ip_address=ip,
                was_successful=True
            )
            login(request, user)
            try:
                user.company
                messages.success(
                    request,
                    f'Welcome back, {user.company.hr_name}!'
                )
                return redirect('home')
            except Company.DoesNotExist:
                pass
            try:
                profile = user.candidate_profile
                messages.success(
                    request,
                    f'Welcome back, {profile.full_name}!'
                )
                return redirect('candidate_dashboard')
            except CandidateProfile.DoesNotExist:
                messages.info(
                    request,
                    'Please complete your registration.'
                )
                return redirect('candidate_register')
        else:
            # Record failed attempt
            LoginAttempt.objects.create(
                username=username,
                ip_address=ip,
                was_successful=False
            )
            remaining = max(0, 4 - recent_failures)
            messages.error(
                request,
                f'Invalid username or password. '
                f'{remaining} attempts remaining before '
                f'temporary lockout.'
            )

    return render(request, 'recruitment/login.html')


def logout_view(request):
    # Flush entire session data
    request.session.flush()
    logout(request)
    messages.info(request, 'You have been logged out.')

    response = redirect('landing')
    # Clear all cache on logout
    response['Cache-Control'] = (
        'no-store, no-cache, must-revalidate, '
        'max-age=0, private'
    )
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


# HR VIEWS
@never_cache
@login_required
def home(request):
    company = get_company(request)
    if not company:
        return redirect('candidate_dashboard')
    jobs = Job.objects.filter(company=company, is_active=True)
    total_jobs = jobs.count()
    total_resumes = Candidate.objects.filter(job__company=company).count()
    shortlisted = MatchScore.objects.filter(job__company=company, is_shortlisted=True).count()
    scores = MatchScore.objects.filter(job__company=company)
    avg_score = 0
    if scores.exists():
        avg_score = round(sum(s.overall_score for s in scores) / scores.count(), 2)
    all_candidates = Candidate.objects.filter(job__company=company)
    scored_ids = MatchScore.objects.filter(job__company=company).values_list('candidate_id', flat=True)
    unscored_count = all_candidates.exclude(id__in=scored_ids).count()
    recent_jobs = jobs.order_by('-created_at')[:5]
    context = {
        'company': company,
        'total_jobs': total_jobs,
        'total_resumes': total_resumes,
        'shortlisted': shortlisted,
        'avg_score': avg_score,
        'recent_jobs': recent_jobs,
        'unscored_count': unscored_count,
    }
    return render(request, 'recruitment/home.html', context)


@login_required
def job_list(request):
    company = get_company(request)
    if not company:
        return redirect('candidate_dashboard')
    jobs = Job.objects.filter(company=company, is_active=True).order_by('-created_at')
    for job in jobs:
        job.resume_count = job.candidates.count()
    return render(request, 'recruitment/job_list.html', {'jobs': jobs, 'company': company})


@never_cache
@login_required
def job_detail(request, job_id):
    company = get_company(request)
    job = get_object_or_404(Job, id=job_id, company=company)
    candidates = Candidate.objects.filter(job=job).order_by('-uploaded_at')
    search_query = request.GET.get('search', '')
    filter_status = request.GET.get('status', '')
    filter_score = request.GET.get('score', '')
    candidate_data = []
    for candidate in candidates:
        try:
            score = candidate.match_score
        except MatchScore.DoesNotExist:
            score = auto_calculate_score(candidate, job)
        candidate_data.append({'candidate': candidate, 'score': score})
    if search_query:
        candidate_data = [
            c for c in candidate_data
            if search_query.lower() in c['candidate'].full_name.lower() or
            search_query.lower() in (c['candidate'].extracted_skills or '').lower()
        ]
    if filter_status == 'shortlisted':
        candidate_data = [c for c in candidate_data if c['score'] and c['score'].is_shortlisted]
    elif filter_status == 'pending':
        candidate_data = [c for c in candidate_data if c['score'] and not c['score'].is_shortlisted]
    if filter_score == 'high':
        candidate_data = [c for c in candidate_data if c['score'] and c['score'].overall_score >= 70]
    elif filter_score == 'medium':
        candidate_data = [c for c in candidate_data if c['score'] and 50 <= c['score'].overall_score < 70]
    elif filter_score == 'low':
        candidate_data = [c for c in candidate_data if c['score'] and c['score'].overall_score < 50]
    candidate_data.sort(
        key=lambda x: x['score'].overall_score if x['score'] else 0,
        reverse=True
    )
    context = {
        'job': job,
        'candidate_data': candidate_data,
        'company': company,
        'search_query': search_query,
        'filter_status': filter_status,
        'filter_score': filter_score,
    }
    return render(request, 'recruitment/job_detail.html', context)


@login_required
def create_job(request):
    company = get_company(request)
    if not company:
        return redirect('candidate_dashboard')
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        required_skills = request.POST.get('required_skills')
        experience_required = request.POST.get('experience_required')
        education_required = request.POST.get('education_required')
        location = request.POST.get('location', '')
        salary_range = request.POST.get('salary_range', '')
        job_type = request.POST.get('job_type', 'full_time')
        openings = request.POST.get('openings', 1)

        if title and description and required_skills:
            job = Job.objects.create(
                company=company,
                title=title,
                description=description,
                required_skills=required_skills,
                experience_required=experience_required,
                education_required=education_required,
                location=location,
                salary_range=salary_range,
                job_type=job_type,
                openings=int(openings),
            )
            match_new_job_with_candidates(job)
            messages.success(
                request,
                f'Job "{job.title}" posted! '
                f'AI is matching candidates.'
            )
            return redirect('job_detail', job_id=job.id)
        else:
            messages.error(
                request, 'Please fill all required fields.'
            )
    return render(
        request,
        'recruitment/create_job.html',
        {'company': company}
    )

@login_required
def edit_job(request, job_id):
    company = get_company(request)
    job = get_object_or_404(Job, id=job_id, company=company)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job updated successfully!')
            return redirect('job_detail', job_id=job.id)
    else:
        form = JobForm(instance=job)
    return render(request, 'recruitment/edit_job.html', {'form': form, 'job': job})


@login_required
def upload_resume(request, job_id):
    company = get_company(request)
    job = get_object_or_404(Job, id=job_id, company=company)
    if request.method == 'POST':
        resume_file = request.FILES.get('resume_file')
        linkedin_url = request.POST.get('linkedin_url', '')
        if not resume_file:
            messages.error(request, 'Please upload a resume file.')
            return redirect('job_detail', job_id=job_id)
        ext = os.path.splitext(resume_file.name)[1].lower()
        if ext not in ['.pdf', '.docx']:
            messages.error(request, 'Only PDF and DOCX files allowed.')
            return redirect('job_detail', job_id=job_id)
        candidate = Candidate.objects.create(
            job=job, full_name='Processing...', email='',
            linkedin_url=linkedin_url, resume_file=resume_file,
        )
        parsed = parse_resume(candidate.resume_file.path)
        if parsed:
            candidate.full_name = parsed['full_name']
            candidate.email = parsed['email']
            candidate.phone = parsed['phone']
            candidate.extracted_skills = parsed['extracted_skills']
            candidate.extracted_experience = parsed['extracted_experience']
            candidate.extracted_education = parsed['extracted_education']
            candidate.raw_text = parsed['raw_text']
            candidate.save()
            # Use safe_calculate_score for proper ML + NLP scoring
            score_obj = safe_calculate_score(candidate, job)
            if score_obj:
                messages.success(
                    request,
                    f'Resume uploaded! Match score: {score_obj.overall_score}%'
                )
            else:
                messages.warning(request, 'Resume uploaded but score calculation failed.')
        else:
            messages.error(request, 'Could not parse resume. Try another file.')
            candidate.delete()
        return redirect('job_detail', job_id=job_id)
    return render(request, 'recruitment/upload_resume.html', {'job': job})


@never_cache
@login_required
def candidate_detail(request, candidate_id):
    company = get_company(request)
    candidate = get_object_or_404(
        Candidate, id=candidate_id, job__company=company
    )

    # Check if candidate is blacklisted
    is_blacklisted = CandidateBlacklist.objects.filter(
        email=candidate.email,
        job=candidate.job
    ).first()

    try:
        score = candidate.match_score
    except MatchScore.DoesNotExist:
        score = None

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'shortlist' and score and not is_blacklisted:
            score.is_shortlisted = True
            score.shortlisted_at = timezone.now()
            score.save()
            send_shortlist_notifications(candidate, company)
            messages.success(
                request,
                f'{candidate.full_name} shortlisted and notified!'
            )
        elif action == 'reject' and score:
            score.is_shortlisted = False
            score.save()
            send_rejection_notification(candidate, company)
            messages.info(
                request,
                f'{candidate.full_name} rejected and notified.'
            )
        return redirect(
            'candidate_detail',
            candidate_id=candidate_id
        )

    job_skills = candidate.job.get_skills_list()
    candidate_skills = candidate.get_skills_list()
    missing_skills = [
        s for s in job_skills
        if s not in candidate_skills
    ]

    context = {
        'candidate': candidate,
        'score': score,
        'skills_list': candidate_skills,
        'job_skills': job_skills,
        'missing_skills': missing_skills,
        'company': company,
        'whatsapp_url': generate_whatsapp_url(candidate, company),
        'is_blacklisted': is_blacklisted,
    }
    return render(
        request,
        'recruitment/candidate_detail.html',
        context
    )


@login_required
def recalculate_score(request, candidate_id):
    company = get_company(request)
    candidate = get_object_or_404(Candidate, id=candidate_id, job__company=company)
    result = safe_calculate_score(candidate, candidate.job)
    if result:
        messages.success(request, f'✅ Score: {result.overall_score}%')
    else:
        messages.error(request, 'Could not calculate score. Try re-uploading the resume.')
    return redirect('candidate_detail', candidate_id=candidate_id)


@login_required
def recalculate_all_scores(request, job_id):
    company = get_company(request)
    job = get_object_or_404(Job, id=job_id, company=company)
    candidates = Candidate.objects.filter(job=job)
    print(f"\n{'='*50}")
    print(f"Recalculating {candidates.count()} candidates for '{job.title}'")
    print(f"{'='*50}")
    updated = 0
    failed = 0
    for candidate in candidates:
        result = safe_calculate_score(candidate, job)
        if result:
            updated += 1
        else:
            failed += 1
    print(f"\nDone: {updated} updated, {failed} failed")
    if failed == 0:
        messages.success(request, f'✅ All {updated} scores recalculated!')
    else:
        messages.warning(request, f'Updated {updated}, {failed} failed (no resume text?).')
    return redirect('job_detail', job_id=job_id)


@login_required
def analytics(request):
    company = get_company(request)
    if not company:
        return redirect('candidate_dashboard')
    all_scores = MatchScore.objects.filter(job__company=company)
    score_90 = all_scores.filter(overall_score__gte=90).count()
    score_80 = all_scores.filter(overall_score__gte=80, overall_score__lt=90).count()
    score_70 = all_scores.filter(overall_score__gte=70, overall_score__lt=80).count()
    score_60 = all_scores.filter(overall_score__gte=60, overall_score__lt=70).count()
    score_below = all_scores.filter(overall_score__lt=60).count()
    jobs = Job.objects.filter(company=company)
    job_stats = []
    for job in jobs:
        candidates = Candidate.objects.filter(job=job)
        scores = MatchScore.objects.filter(job=job)
        avg = 0
        if scores.exists():
            avg = round(sum(s.overall_score for s in scores) / scores.count(), 2)
        job_stats.append({
            'job': job,
            'total_candidates': candidates.count(),
            'avg_score': avg,
            'shortlisted': scores.filter(is_shortlisted=True).count(),
        })
    context = {
        'company': company,
        'score_90': score_90, 'score_80': score_80,
        'score_70': score_70, 'score_60': score_60,
        'score_below': score_below,
        'job_stats': job_stats,
        'total_candidates': Candidate.objects.filter(job__company=company).count(),
        'total_shortlisted': all_scores.filter(is_shortlisted=True).count(),
    }
    return render(request, 'recruitment/analytics.html', context)


@login_required
def delete_job(request, job_id):
    company = get_company(request)
    job = get_object_or_404(Job, id=job_id, company=company)
    if request.method == 'POST':
        title = job.title
        job.delete()
        messages.success(request, f'Job "{title}" deleted!')
        return redirect('job_list')
    return render(request, 'recruitment/confirm_delete.html', {
        'object_type': 'Job', 'object_name': job.title,
        'cancel_url': 'job_list', 'cancel_id': None,
    })


@login_required
def delete_candidate(request, candidate_id):
    company = get_company(request)
    candidate = get_object_or_404(Candidate, id=candidate_id, job__company=company)
    job_id = candidate.job.id
    if request.method == 'POST':
        name = candidate.full_name
        if candidate.resume_file and os.path.exists(candidate.resume_file.path):
            os.remove(candidate.resume_file.path)
        candidate.delete()
        messages.success(request, f'Candidate "{name}" deleted!')
        return redirect('job_detail', job_id=job_id)
    return render(request, 'recruitment/confirm_delete.html', {
        'object_type': 'Candidate', 'object_name': candidate.full_name,
        'cancel_url': 'job_detail', 'cancel_id': job_id,
    })


@login_required
def delete_all_candidates(request, job_id):
    company = get_company(request)
    job = get_object_or_404(Job, id=job_id, company=company)
    if request.method == 'POST':
        for candidate in Candidate.objects.filter(job=job):
            if candidate.resume_file and os.path.exists(candidate.resume_file.path):
                os.remove(candidate.resume_file.path)
        Candidate.objects.filter(job=job).delete()
        messages.success(request, 'All candidates deleted!')
        return redirect('job_detail', job_id=job_id)
    return render(request, 'recruitment/confirm_delete.html', {
        'object_type': 'All Candidates',
        'object_name': f'all candidates for {job.title}',
        'cancel_url': 'job_detail', 'cancel_id': job_id,
    })


@login_required
def company_profile(request):
    company = get_company(request)
    if not company:
        return redirect('candidate_dashboard')
    if request.method == 'POST':
        company.company_name = request.POST.get('company_name', company.company_name)
        company.industry = request.POST.get('industry', company.industry)
        company.company_size = request.POST.get('company_size', company.company_size)
        company.website = request.POST.get('website', company.website)
        company.description = request.POST.get('description', company.description)
        company.hr_name = request.POST.get('hr_name', company.hr_name)
        company.hr_phone = request.POST.get('hr_phone', company.hr_phone)
        if request.FILES.get('logo'):
            company.logo = request.FILES['logo']
        company.save()
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        messages.success(request, 'Company profile updated!')
        return redirect('company_profile')
    return render(request, 'recruitment/company_profile.html', {'company': company})


@login_required
def export_candidate_pdf(request, candidate_id):
    company = get_company(request)
    candidate = get_object_or_404(Candidate, id=candidate_id, job__company=company)
    try:
        score = candidate.match_score
    except MatchScore.DoesNotExist:
        score = None
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{candidate.full_name}_report.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    p.setFillColorRGB(0.26, 0.38, 0.93)
    p.rect(0, height - 80, width, 80, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 22)
    p.drawString(40, height - 45, "HireIQ — Candidate Report")
    p.setFont("Helvetica", 12)
    p.drawString(40, height - 65, f"Generated for {company.company_name}")
    p.setFillColorRGB(0, 0, 0)
    y = height - 110
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "Candidate Information")
    y -= 25
    p.setFont("Helvetica", 11)
    p.drawString(40, y, f"Name:         {candidate.full_name}")
    y -= 18
    p.drawString(40, y, f"Email:          {candidate.email}")
    y -= 18
    p.drawString(40, y, f"Phone:         {candidate.phone}")
    y -= 18
    p.drawString(40, y, f"Applied For:  {candidate.job.title}")
    y -= 18
    p.drawString(40, y, f"Applied On:   {candidate.uploaded_at.strftime('%B %d, %Y')}")
    if candidate.linkedin_url:
        y -= 18
        p.drawString(40, y, f"LinkedIn:      {candidate.linkedin_url}")
    y -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "Match Scores")
    y -= 25
    p.setFont("Helvetica", 11)
    if score:
        p.drawString(40, y, f"Overall Score:       {score.overall_score}%")
        y -= 18
        p.drawString(40, y, f"Skills Score:          {score.skills_score}%")
        y -= 18
        p.drawString(40, y, f"Experience Score:  {score.experience_score}%")
        y -= 18
        p.drawString(40, y, f"Education Score:   {score.education_score}%")
        y -= 18
        p.drawString(40, y, f"Status:                  {'Shortlisted' if score.is_shortlisted else 'Pending'}")
    y -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "Extracted Skills")
    y -= 20
    p.setFont("Helvetica", 11)
    skills_text = ', '.join(candidate.get_skills_list()) or 'No skills extracted'
    p.drawString(40, y, skills_text[:90])
    y -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "Education")
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(40, y, (candidate.extracted_education or 'Not extracted')[:90])
    y -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "Experience")
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(40, y, (candidate.extracted_experience or 'Not extracted')[:90])
    p.setFillColorRGB(0.26, 0.38, 0.93)
    p.rect(0, 0, width, 30, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica", 9)
    p.drawString(40, 10, "Generated by HireIQ — AI Powered Recruitment Platform")
    p.showPage()
    p.save()
    return response


@login_required
def schedule_interview(request, candidate_id):
    company = get_company(request)
    candidate = get_object_or_404(Candidate, id=candidate_id, job__company=company)
    existing = None
    try:
        existing = candidate.interview
    except InterviewSchedule.DoesNotExist:
        pass
    if request.method == 'POST':
        interview_date = request.POST.get('interview_date')
        interview_time = request.POST.get('interview_time')
        interview_mode = request.POST.get('interview_mode')
        meeting_link = request.POST.get('meeting_link', '')
        interview_location = request.POST.get('interview_location', '')
        additional_notes = request.POST.get('additional_notes', '')
        if existing:
            existing.interview_date = interview_date
            existing.interview_time = interview_time
            existing.interview_mode = interview_mode
            existing.meeting_link = meeting_link
            existing.interview_location = interview_location
            existing.additional_notes = additional_notes
            existing.status = 'rescheduled'
            existing.save()
            interview = existing
            action = 'rescheduled'
        else:
            interview = InterviewSchedule.objects.create(
                candidate=candidate, job=candidate.job, company=company,
                interview_date=interview_date, interview_time=interview_time,
                interview_mode=interview_mode, meeting_link=meeting_link,
                interview_location=interview_location, additional_notes=additional_notes,
            )
            action = 'scheduled'
        send_interview_notification(interview, company, action)
        if (candidate.candidate_profile and
                candidate.candidate_profile.whatsapp_consent and candidate.phone):
            whatsapp_url = generate_interview_whatsapp_url(interview, company)
            messages.success(
                request,
                f'Interview {action}! Email sent. '
                f'<a href="{whatsapp_url}" target="_blank" class="btn btn-sm btn-success ms-2">'
                f'Send WhatsApp</a>'
            )
        else:
            messages.success(request, f'Interview {action}! Email sent to {candidate.email}')
        return redirect('candidate_detail', candidate_id=candidate_id)
    return render(request, 'recruitment/schedule_interview.html', {
        'candidate': candidate, 'company': company, 'existing': existing,
    })


# CANDIDATE VIEWS
@login_required
def candidate_dashboard(request):
    try:
        profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        return redirect('candidate_register')
    # Auto-match new jobs
    if profile.raw_text:
        from .resume_parser import calculate_skills_score, calculate_text_similarity
        already_matched_ids = JobMatch.objects.filter(
            candidate_profile=profile
        ).values_list('job_id', flat=True)
        new_jobs = Job.objects.filter(is_active=True).exclude(id__in=already_matched_ids)
        for job in new_jobs:
            skills_score = calculate_skills_score(
                profile.get_skills_list(), job.get_skills_list()
            )
            if skills_score == 0:
                continue
            ml_score = 0
            try:
                extracted_skills_list = [s.strip() for s in profile.skills.split(',') if s.strip()]
                response = requests.post(
                    "http://127.0.0.1:8001/score_resume",
                    json={
                        "resume_text": profile.raw_text,
                        "job_description": job.description,
                        "required_skills": job.get_skills_list(),
                        "extracted_skills": extracted_skills_list,
                        "experience_required": job.experience_required
                    },
                    timeout=5
                )
                result = response.json()
                if result.get("status") == "success":
                    ml_score = result["final_score"]
            except Exception:
                text_score = calculate_text_similarity(profile.raw_text, job.description)
                ml_score = round(skills_score * 0.6 + text_score * 0.4, 2)
            if ml_score > 15 or skills_score > 20:
                JobMatch.objects.get_or_create(
                    candidate_profile=profile, job=job,
                    defaults={'overall_score': round(ml_score, 2), 'skills_score': round(skills_score, 2)}
                )
    job_matches = JobMatch.objects.filter(candidate_profile=profile).order_by('-overall_score')
    applied_job_ids = list(
        Candidate.objects.filter(email=profile.user.email).values_list('job_id', flat=True)
    )
    context = {
        'profile': profile,
        'job_matches': job_matches,
        'applied_job_ids': applied_job_ids,
        'total_applied': len(applied_job_ids),
        'top_match': job_matches.first() if job_matches else None,
    }
    return render(request, 'recruitment/candidate_dashboard.html', context)


@login_required
def candidate_upload_resume(request):
    try:
        profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        return redirect('candidate_register')
    if request.method == 'POST':
        resume_file = request.FILES.get('resume_file')
        if resume_file:
            ext = os.path.splitext(resume_file.name)[1].lower()
            if ext not in ['.pdf', '.docx']:
                messages.error(request, 'Only PDF and DOCX allowed.')
                return redirect('candidate_upload_resume')
            if profile.resume_file and os.path.exists(profile.resume_file.path):
                os.remove(profile.resume_file.path)
            profile.resume_file = resume_file
            profile.save()
            parsed = parse_resume(profile.resume_file.path)
            if parsed:
                profile.skills = parsed['extracted_skills']
                profile.experience_years = parsed['extracted_experience']
                profile.education = parsed['extracted_education']
                profile.raw_text = parsed['raw_text']
                if parsed['full_name'] != 'Unknown':
                    profile.full_name = parsed['full_name']
                profile.save()
                JobMatch.objects.filter(candidate_profile=profile).delete()
                from .resume_parser import calculate_skills_score, calculate_text_similarity
                extracted_skills_list = [
                    s.strip() for s in parsed['extracted_skills'].split(',') if s.strip()
                ]
                matched_count = 0
                for job in Job.objects.filter(is_active=True):
                    skills_score = calculate_skills_score(
                        profile.get_skills_list(), job.get_skills_list()
                    )
                    if skills_score == 0:
                        continue
                    ml_score = 0
                    api_success = False
                    try:
                        response = requests.post(
                            "http://127.0.0.1:8001/score_resume",
                            json={
                                "resume_text": parsed['raw_text'],
                                "job_description": job.description,
                                "required_skills": job.get_skills_list(),
                                "extracted_skills": extracted_skills_list,
                                "experience_required": job.experience_required
                            },
                            timeout=8
                        )
                        result = response.json()
                        if result.get("status") == "success":
                            ml_score = result["final_score"]
                            api_success = True
                    except Exception:
                        pass
                    if not api_success:
                        text_score = calculate_text_similarity(parsed['raw_text'], job.description)
                        ml_score = round(skills_score * 0.6 + text_score * 0.4, 2)
                    if ml_score > 15 or skills_score > 20:
                        JobMatch.objects.create(
                            candidate_profile=profile, job=job,
                            overall_score=round(ml_score, 2),
                            skills_score=round(skills_score, 2),
                        )
                        matched_count += 1
                messages.success(request, f'Resume uploaded! Found {matched_count} job matches.')
                return redirect('candidate_dashboard')
            else:
                messages.error(request, 'Could not parse resume.')
    return render(request, 'recruitment/candidate_upload_resume.html', {'profile': profile})


@login_required
def candidate_job_list(request):
    try:
        profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        return redirect('candidate_register')

    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    selected_job_types = request.GET.getlist('job_type')
    selected_experience = request.GET.getlist('experience')
    selected_companies = request.GET.getlist('company')
    sort = request.GET.get('sort', 'match')

    # Base queryset
    all_jobs = Job.objects.filter(
        is_active=True
    ).select_related('company')

    # Apply search filter
    if search_query:
        from django.db.models import Q
        all_jobs = all_jobs.filter(
            Q(title__icontains=search_query) |
            Q(required_skills__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(company__company_name__icontains=search_query)
        )

    # Apply job type filter
    if selected_job_types:
        all_jobs = all_jobs.filter(
            job_type__in=selected_job_types
        )

    # Apply experience filter
    if selected_experience:
        all_jobs = all_jobs.filter(
            experience_required__in=selected_experience
        )

    # Apply company filter
    if selected_companies:
        all_jobs = all_jobs.filter(
            company_id__in=selected_companies
        )

    # Apply sort
    if sort == 'latest':
        all_jobs = all_jobs.order_by('-created_at')
    elif sort == 'company':
        all_jobs = all_jobs.order_by('company__company_name')

    # Build job data with match scores
    job_data = []
    blacklisted_job_ids = CandidateBlacklist.objects.filter(
        email=profile.user.email
    ).values_list('job_id', flat=True)

    applied_job_ids = Candidate.objects.filter(
        email=profile.user.email
    ).values_list('job_id', flat=True)

    for job in all_jobs:
        match = JobMatch.objects.filter(
            candidate_profile=profile, job=job
        ).first()
        job_data.append({
            'job': job,
            'match': match,
            'already_applied': job.id in applied_job_ids,
            'is_blacklisted': job.id in blacklisted_job_ids,
        })

    # Sort by match score if selected
    if sort == 'match':
        job_data.sort(
            key=lambda x: x['match'].overall_score
            if x['match'] else 0,
            reverse=True
        )

    # Get filter options for sidebar
    from .models import Company as CompanyModel
    all_companies = CompanyModel.objects.filter(
        jobs__is_active=True
    ).distinct()

    context = {
        'job_data': job_data,
        'profile': profile,
        'search_query': search_query,
        'selected_job_types': selected_job_types,
        'selected_experience': selected_experience,
        'selected_companies': selected_companies,
        'sort': sort,
        'all_companies': all_companies,
        'job_types': Job.JOB_TYPE_CHOICES,
        'experience_choices': Job.EXPERIENCE_CHOICES,
    }
    return render(
        request,
        'recruitment/candidate_job_list.html',
        context
    )


@login_required
def candidate_job_detail(request, job_id):
    try:
        profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        return redirect('candidate_register')
    job = get_object_or_404(Job, id=job_id, is_active=True)
    match = JobMatch.objects.filter(candidate_profile=profile, job=job).first()
    already_applied = Candidate.objects.filter(job=job, email=profile.user.email).exists()
    job_skills = job.get_skills_list() or []
    profile_skills = profile.get_skills_list() or []
    matched_skills = [s for s in job_skills if s in profile_skills]
    missing_skills = [s for s in job_skills if s not in profile_skills]
    score_improvement = {}
    if missing_skills and match:
        current_score = match.overall_score or 0
        total_skills = len(job_skills)
        if total_skills > 0:
            gain = round((1 / total_skills) * 40, 1)
            for skill in missing_skills:
                score_improvement[skill] = {
                    'gain': gain,
                    'new_score': round(min(current_score + gain, 100), 1)
                }
    context = {
        'job': job, 'match': match, 'already_applied': already_applied,
        'matched_skills': matched_skills, 'missing_skills': missing_skills,
        'score_improvement': score_improvement, 'profile': profile,
    }
    return render(request, 'recruitment/candidate_job_detail.html', context)


@login_required
def candidate_apply(request, job_id):
    try:
        profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        return redirect('candidate_register')

    job = get_object_or_404(Job, id=job_id, is_active=True)

    # Check blacklist first
    if CandidateBlacklist.objects.filter(
        email=profile.user.email, job=job
    ).exists():
        messages.error(
            request,
            'You are not eligible to apply for this position.'
        )
        return redirect('candidate_job_list')

    if Candidate.objects.filter(
        job=job, email=profile.user.email
    ).exists():
        messages.warning(
            request, 'You have already applied for this job!'
        )
        return redirect('candidate_job_list')

    if not profile.resume_file:
        messages.error(
            request,
            'Please upload your resume before applying!'
        )
        return redirect('candidate_upload_resume')

    candidate = Candidate.objects.create(
        job=job, candidate_profile=profile,
        full_name=profile.full_name,
        email=profile.user.email,
        phone=profile.phone,
        linkedin_url=profile.linkedin_url,
        resume_file=profile.resume_file,
        extracted_skills=profile.skills,
        extracted_experience=profile.experience_years,
        extracted_education=profile.education,
        raw_text=profile.raw_text,
    )
    score_obj = safe_calculate_score(candidate, job)
    overall = score_obj.overall_score if score_obj else 0

    # Create applied notification
    create_candidate_notification(
        candidate_email=profile.user.email,
        notification_type='applied',
        title=f'Application Submitted — {job.title}',
        message=(
            f'Your application for {job.title} at '
            f'{job.company.company_name} has been submitted '
            f'successfully. Your AI match score is {overall}%. '
            f'We will review your profile and get back to you.'
        ),
        job=job,
        company=job.company,
    )

    messages.success(
        request,
        f'Applied for {job.title}! Match score: {overall}%'
    )
    return redirect('candidate_job_list')


@login_required
def candidate_profile_edit(request):
    try:
        profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        return redirect('candidate_register')
    if request.method == 'POST':
        profile.full_name = request.POST.get('full_name', profile.full_name)
        profile.phone = request.POST.get('phone', profile.phone)
        profile.linkedin_url = request.POST.get('linkedin_url', profile.linkedin_url)
        profile.github_url = request.POST.get('github_url', profile.github_url)
        profile.portfolio_url = request.POST.get('portfolio_url', profile.portfolio_url)
        profile.save()
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        messages.success(request, 'Profile updated!')
        return redirect('candidate_dashboard')
    return render(request, 'recruitment/candidate_profile_edit.html', {'profile': profile})


@login_required
def application_tracker(request):
    try:
        profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        return redirect('candidate_register')
    applications = Candidate.objects.filter(
        email=profile.user.email
    ).select_related('job', 'job__company', 'match_score').order_by('-uploaded_at')
    app_data = []
    for app in applications:
        try:
            score = app.match_score
            if score.is_shortlisted:
                status, label, color, progress = 'shortlisted', 'Shortlisted', 'success', 75
            else:
                status, label, color, progress = 'review', 'Under Review', 'warning', 40
        except MatchScore.DoesNotExist:
            score = None
            status, label, color, progress = 'applied', 'Applied', 'primary', 20
        app_data.append({
            'application': app, 'score': score,
            'status': status, 'status_label': label,
            'status_color': color, 'progress': progress,
        })
    return render(request, 'recruitment/application_tracker.html', {
        'app_data': app_data, 'profile': profile,
        'total': len(app_data),
        'shortlisted': sum(1 for a in app_data if a['status'] == 'shortlisted'),
        'under_review': sum(1 for a in app_data if a['status'] == 'review'),
    })


@login_required
def notifications_page(request):
    try:
        profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        return redirect('candidate_register')

    notifications = CandidateNotification.objects.filter(
        candidate_email=profile.user.email
    ).order_by('-created_at')

    unread_count = notifications.filter(is_read=False).count()

    # Mark all as read when page is opened
    notifications.filter(is_read=False).update(is_read=True)

    return render(
        request,
        'recruitment/notifications_page.html',
        {
            'notifications': notifications,
            'unread_count': unread_count,
            'profile': profile,
        }
    )


@login_required
def mark_all_read(request):
    try:
        profile = request.user.candidate_profile
        CandidateNotification.objects.filter(
            candidate_email=profile.user.email,
            is_read=False
        ).update(is_read=True)
    except Exception:
        pass
    return redirect('notifications_page')


# NOTIFICATION HELPER
def create_candidate_notification(
    candidate_email, notification_type,
    title, message, job=None, company=None
    ):
    """Create a notification record for the candidate."""
    try:
        CandidateNotification.objects.create(
            candidate_email=candidate_email,
            notification_type=notification_type,
            title=title,
            message=message,
            job=job,
            company=company,
        )
    except Exception as e:
        print(f"Notification creation error: {e}")


# UPDATED SHORTLIST — now creates notification
def send_shortlist_notifications(candidate, company):
    """Send email + create dashboard notification."""
    try:
        subject = (
            f'🎉 Congratulations! Shortlisted '
            f'— {company.company_name}'
        )
        message = f'''
Dear {candidate.full_name},

Congratulations! You have been SHORTLISTED for
{candidate.job.title} at {company.company_name}!

Our HR team will contact you shortly with next steps
including interview scheduling.

HR Contact: {company.hr_name} | {company.hr_phone}

Best regards,
{company.company_name} | HireIQ Platform
        '''
        send_mail(
            subject, message,
            settings.DEFAULT_FROM_EMAIL,
            [candidate.email], fail_silently=True
        )

        # Create dashboard notification
        create_candidate_notification(
            candidate_email=candidate.email,
            notification_type='shortlisted',
            title=f'🎉 You are Shortlisted for {candidate.job.title}!',
            message=(
                f'Congratulations! {company.company_name} has '
                f'shortlisted you for the position of '
                f'{candidate.job.title}. '
                f'HR Contact: {company.hr_name} '
                f'({company.hr_phone}). '
                f'Our team will reach out soon!'
            ),
            job=candidate.job,
            company=company,
        )
        print(f"Shortlist notification created for {candidate.email}")
    except Exception as e:
        print(f"Shortlist notification error: {e}")


# BLACKLIST SYSTEM
@login_required
def reject_and_blacklist(request, candidate_id):
    company = get_company(request)
    candidate = get_object_or_404(
        Candidate, id=candidate_id, job__company=company
    )

    if request.method == 'POST':
        reason = request.POST.get('reason', 'rejected')
        notes = request.POST.get('notes', '')

        # Update match score — mark as not shortlisted
        try:
            score = candidate.match_score
            score.is_shortlisted = False
            score.save()
        except MatchScore.DoesNotExist:
            pass

        # Add to blacklist
        blacklist_entry, created = CandidateBlacklist.objects.get_or_create(
            email=candidate.email,
            job=candidate.job,
            defaults={
                'company': company,
                'reason': reason,
                'notes': notes,
            }
        )

        if not created:
            # Update existing entry
            blacklist_entry.reason = reason
            blacklist_entry.notes = notes
            blacklist_entry.save()

        # Send rejection email
        send_rejection_notification(candidate, company)

        # Create dashboard notification
        create_candidate_notification(
            candidate_email=candidate.email,
            notification_type='rejected',
            title=(
                f'Update on your application '
                f'— {candidate.job.title}'
            ),
            message=(
                f'Thank you for applying for '
                f'{candidate.job.title} at '
                f'{company.company_name}. After careful '
                f'review, we will not be moving forward '
                f'with your application at this time. '
                f'We encourage you to apply for future '
                f'openings that match your profile.'
            ),
            job=candidate.job,
            company=company,
        )

        messages.success(
            request,
            f'{candidate.full_name} has been rejected '
            f'and blocked from reapplying to this job.'
        )

        # Redirect to job detail NOT candidate detail
        return redirect('job_detail', job_id=candidate.job.id)

    return render(
        request,
        'recruitment/reject_blacklist.html',
        {'candidate': candidate, 'company': company}
    )


# OFFER LETTER
@login_required
def send_offer_letter(request, candidate_id):
    company = get_company(request)
    candidate = get_object_or_404(
        Candidate, id=candidate_id, job__company=company
    )
    existing_offer = None
    try:
        existing_offer = candidate.offer_letter
    except OfferLetter.DoesNotExist:
        pass

    if request.method == 'POST':
        designation = request.POST.get('designation')
        salary_package = request.POST.get('salary_package')
        joining_date = request.POST.get('joining_date')
        additional_notes = request.POST.get('notes', '')

        if existing_offer:
            existing_offer.designation = designation
            existing_offer.salary_package = salary_package
            existing_offer.joining_date = joining_date
            existing_offer.offer_letter_text = additional_notes
            existing_offer.status = 'sent'
            existing_offer.save()
            offer = existing_offer
        else:
            offer = OfferLetter.objects.create(
                candidate=candidate,
                job=candidate.job,
                company=company,
                designation=designation,
                salary_package=salary_package,
                joining_date=joining_date,
                offer_letter_text=additional_notes,
            )

        # Generate PDF
        pdf_buffer = generate_offer_letter_pdf(
            offer, candidate, company
        )

        # Send email with PDF attachment
        try:
            from django.core.mail import EmailMessage
            email = EmailMessage(
                subject=(
                    f'🎊 Official Offer Letter — '
                    f'{designation} at {company.company_name}'
                ),
                body=f'''
            Dear {candidate.full_name},
            
            Congratulations! Please find your official offer letter attached.
            
            Position  : {designation}
            Company   : {company.company_name}
            Package   : {salary_package}
            Joining   : {joining_date}
            
            Please review the offer letter carefully and respond within 7 days.
            
            Best regards,
            {company.hr_name}
            {company.company_name}
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[candidate.email],
            )
            email.attach(
                f'Offer_Letter_{candidate.full_name.replace(" ", "_")}.pdf',
                pdf_buffer.getvalue(),
                'application/pdf'
            )
            email.send()
            print(
                f"Offer letter PDF sent to {candidate.email}"
            )
        except Exception as e:
            print(f"Offer email error: {e}")

        # WhatsApp message
        whatsapp_url = None
        if (candidate.candidate_profile and
                candidate.candidate_profile.whatsapp_consent
                and candidate.phone):
            msg = (
                f"Dear {candidate.full_name}, "
                f"Congratulations! Your official offer letter "
                f"for {designation} at {company.company_name} "
                f"has been sent to your email {candidate.email}. "
                f"Package: {salary_package}. "
                f"Joining: {joining_date}. "
                f"Please check your email. - {company.hr_name}"
            )
            encoded = urllib.parse.quote(msg)
            phone = candidate.phone.replace(
                '+', ''
            ).replace(' ', '').replace('-', '')
            whatsapp_url = (
                f"https://wa.me/{phone}?text={encoded}"
            )

        # Dashboard notification
        create_candidate_notification(
            candidate_email=candidate.email,
            notification_type='offer',
            title=f'🎊 Official Offer Letter — {designation}!',
            message=(
                f'Congratulations! {company.company_name} has '
                f'sent your official offer letter for '
                f'{designation}. Package: {salary_package}. '
                f'Joining Date: {joining_date}. '
                f'Please check your email for the PDF offer '
                f'letter and respond within 7 days.'
            ),
            job=candidate.job,
            company=company,
        )

        from django.utils.safestring import mark_safe
        if whatsapp_url:
            messages.success(
                request,
                mark_safe(
                    f'✅ Official offer letter PDF sent to '
                    f'{candidate.email}! '
                    f'<a href="{whatsapp_url}" target="_blank" '
                    f'class="btn btn-sm btn-success ms-2">'
                    f'Send WhatsApp</a>'
                )
            )
        else:
            messages.success(
                request,
                f'✅ Official offer letter PDF sent to '
                f'{candidate.email}!'
            )
        return redirect(
            'candidate_detail',
            candidate_id=candidate_id
        )

    return render(
        request,
        'recruitment/send_offer_letter.html',
        {
            'candidate': candidate,
            'company': company,
            'existing_offer': existing_offer,
            'job': candidate.job,
        }
    )


@login_required
def download_offer_letter(request, candidate_id):
    """HR can download the offer letter PDF."""
    company = get_company(request)
    candidate = get_object_or_404(
        Candidate, id=candidate_id, job__company=company
    )
    try:
        offer = candidate.offer_letter
    except OfferLetter.DoesNotExist:
        messages.error(request, 'No offer letter found.')
        return redirect(
            'candidate_detail',
            candidate_id=candidate_id
        )

    pdf_buffer = generate_offer_letter_pdf(
        offer, candidate, company
    )

    response = HttpResponse(
        pdf_buffer.getvalue(),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="Offer_Letter_'
        f'{candidate.full_name.replace(" ", "_")}.pdf"'
    )
    return response


# MARK INTERVIEW COMPLETE
@login_required
def mark_interview_complete(request, candidate_id):
    company = get_company(request)
    candidate = get_object_or_404(
        Candidate, id=candidate_id, job__company=company
    )
    try:
        interview = candidate.interview
        interview.status = 'completed'
        interview.save()

        # Create notification
        create_candidate_notification(
            candidate_email=candidate.email,
            notification_type='interview',
            title=f'Interview Completed — {candidate.job.title}',
            message=(
                f'Your interview for {candidate.job.title} at '
                f'{company.company_name} has been marked as '
                f'completed. The HR team will get back to you '
                f'with the next steps soon.'
            ),
            job=candidate.job,
            company=company,
        )
        messages.success(
            request,
            f'Interview marked as completed! '
            f'You can now send an offer letter.'
        )
    except InterviewSchedule.DoesNotExist:
        messages.error(request, 'No interview found.')
    return redirect(
        'candidate_detail',
        candidate_id=candidate_id
    )

@login_required
def kanban_board(request, job_id):
    company = get_company(request)
    job = get_object_or_404(Job, id=job_id, company=company)
    candidates = Candidate.objects.filter(
        job=job
    ).select_related('match_score')

    # Organize candidates into pipeline stages
    pipeline = {
        'applied': [],
        'screening': [],
        'shortlisted': [],
        'interview': [],
        'offer': [],
        'hired': [],
    }

    for candidate in candidates:
        try:
            score = candidate.match_score
        except MatchScore.DoesNotExist:
            score = None

        card = {
            'candidate': candidate,
            'score': score,
        }

        # Determine stage
        try:
            offer = candidate.offer_letter
            if offer.status == 'accepted':
                pipeline['hired'].append(card)
            else:
                pipeline['offer'].append(card)
            continue
        except OfferLetter.DoesNotExist:
            pass

        try:
            interview = candidate.interview
            pipeline['interview'].append(card)
            continue
        except InterviewSchedule.DoesNotExist:
            pass

        if score and score.is_shortlisted:
            pipeline['shortlisted'].append(card)
        elif score and score.overall_score >= 50:
            pipeline['screening'].append(card)
        else:
            pipeline['applied'].append(card)

    # Sort each stage by score
    for stage in pipeline:
        pipeline[stage].sort(
            key=lambda x: x['score'].overall_score
            if x['score'] else 0,
            reverse=True
        )

    context = {
        'job': job,
        'company': company,
        'pipeline': pipeline,
        'total': candidates.count(),
    }
    return render(
        request,
        'recruitment/kanban_board.html',
        context
    )

@login_required
def generate_interview_questions(request, candidate_id):
    company = get_company(request)
    candidate = get_object_or_404(
        Candidate, id=candidate_id, job__company=company
    )
    job = candidate.job

    # Check if questions already exist
    existing = None
    try:
        existing = candidate.interview_questions
    except InterviewQuestions.DoesNotExist:
        pass

    if request.method == 'POST' or not existing:
        # Generate fresh questions
        questions = generate_questions(candidate, job)

        if existing:
            existing.questions_data = questions
            existing.regenerated_count += 1
            existing.save()
            iq = existing
        else:
            iq = InterviewQuestions.objects.create(
                candidate=candidate,
                job=job,
                questions_data=questions,
            )

        # Create notification for candidate
        create_candidate_notification(
            candidate_email=candidate.email,
            notification_type='interview',
            title=f'📝 Interview Prep Ready — {job.title}!',
            message=(
                f'Your personalized interview preparation '
                f'questions for {job.title} at '
                f'{company.company_name} are ready. '
                f'Review them to ace your interview!'
            ),
            job=job,
            company=company,
        )

        messages.success(
            request,
            f'✅ Generated {len(questions)} personalized '
            f'interview questions!'
        )

    return render(
        request,
        'recruitment/interview_questions.html',
        {
            'candidate': candidate,
            'company': company,
            'questions': (
                existing.questions_data
                if existing and request.method == 'GET'
                else questions
            ),
            'job': job,
            'regenerated': existing.regenerated_count
            if existing else 0,
        }
    )

@login_required
def candidate_interview_prep(request, job_id):
    """
    Candidate view — see their interview prep questions
    """
    try:
        profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        return redirect('candidate_register')

    job = get_object_or_404(Job, id=job_id)

    # Find their application
    candidate = Candidate.objects.filter(
        job=job, email=profile.user.email
    ).first()

    if not candidate:
        messages.error(
            request,
            'You have not applied for this job.'
        )
        return redirect('candidate_dashboard')

    questions = None
    try:
        iq = candidate.interview_questions
        questions = iq.questions_data
    except InterviewQuestions.DoesNotExist:
        # Generate for candidate too
        questions = generate_questions(candidate, job)

    return render(
        request,
        'recruitment/candidate_interview_prep.html',
        {
            'candidate': candidate,
            'job': job,
            'questions': questions,
            'profile': profile,
        }
    )

# Company Email verification
def is_free_email(email):
    """Check if email is from a free provider"""
    free_domains = [
        'gmail.com', 'yahoo.com', 'hotmail.com',
        'outlook.com', 'rediffmail.com', 'ymail.com',
        'live.com', 'aol.com', 'icloud.com',
        'protonmail.com', 'zoho.com',
    ]
    try:
        domain = email.split('@')[1].lower()
        return domain in free_domains
    except Exception:
        return True


def send_company_verification_otp(company, otp):
    """Send OTP to company official email"""
    subject = 'HireIQ — Verify Your Company Email'
    message = f'''
Dear {company.hr_name},

To complete verification of {company.company_name}
on HireIQ, please enter this OTP:

    ━━━━━━━━━━━━━━━━━━━━━━━━
           {otp}
    ━━━━━━━━━━━━━━━━━━━━━━━━

This OTP is valid for 10 minutes.

Once verified, your company will receive a
✅ Verified Badge visible to all candidates.

If you did not request this, please ignore.

Best regards,
HireIQ Team
    '''
    send_mail(
        subject, message,
        settings.DEFAULT_FROM_EMAIL,
        [company.company_email],
        fail_silently=False,
    )


@login_required
def verify_company_email(request):
    """
    Step 1 — HR enters company official email
    and optionally HR work email
    """
    company = get_company(request)
    if not company:
        return redirect('candidate_dashboard')

    if company.is_verified:
        messages.info(
            request,
            'Your company is already verified!'
        )
        return redirect('home')

    if request.method == 'POST':
        company_email = request.POST.get(
            'company_email', ''
        ).strip().lower()
        hr_official_email = request.POST.get(
            'hr_official_email', ''
        ).strip().lower()
        linkedin_url = request.POST.get(
            'linkedin_url', ''
        ).strip()
        website = request.POST.get(
            'website', company.website
        ).strip()

        # Validate company email
        if not company_email:
            messages.error(
                request,
                'Please enter your company official email.'
            )
            return render(
                request,
                'recruitment/verify_company_email.html',
                {'company': company}
            )

        # Check if company email is a free domain
        if is_free_email(company_email):
            messages.error(
                request,
                f'Please use your official company email '
                f'(e.g. hr@{company.company_name.lower().replace(" ", "")}.com). '
                f'Free email providers like Gmail are not '
                f'accepted for company verification.'
            )
            return render(
                request,
                'recruitment/verify_company_email.html',
                {'company': company}
            )

        # Save emails and URLs
        company.company_email = company_email
        company.hr_official_email = hr_official_email
        if linkedin_url:
            company.linkedin_url = linkedin_url
        if website:
            company.website = website
        company.verification_status = 'pending'

        # Check domain match
        domain_match = company.check_domain_match()
        company.domain_match = domain_match
        company.save()

        # Generate and send OTP to company email
        try:
            otp_obj = request.user.otp_verification
        except OTPVerification.DoesNotExist:
            otp_obj = OTPVerification.objects.create(
                user=request.user,
                user_type='company_email'
            )

        otp = otp_obj.generate_company_email_otp()
        print(f"TEST OTP: {otp}")
        try:
            send_company_verification_otp(company, otp)
            messages.success(
                request,
                f'Verification OTP sent to '
                f'{company_email}. '
                f'Please check your inbox.'
            )

            if domain_match:
                messages.success(
                    request,
                    '✅ Domain match confirmed — '
                    'your email domain matches your website!'
                )
            else:
                if website:
                    messages.warning(
                        request,
                        '⚠️ Email domain does not match '
                        'website domain. Verification will '
                        'still proceed but this may be '
                        'reviewed.'
                    )

            return redirect('confirm_company_email')

        except Exception as e:
            messages.error(
                request,
                f'Could not send OTP to {company_email}. '
                f'Please check the email address. '
                f'Error: {str(e)}'
            )

    context = {
        'company': company,
        'is_free_email_check': True,
    }
    return render(
        request,
        'recruitment/verify_company_email.html',
        context
    )


@login_required
def confirm_company_email(request):
    """
    Step 2 — HR enters OTP received on company email
    """
    company = get_company(request)
    if not company:
        return redirect('candidate_dashboard')

    if company.is_verified:
        messages.info(request, 'Already verified!')
        return redirect('home')

    if not company.company_email:
        return redirect('verify_company_email')

    if request.method == 'POST':
        action = request.POST.get('action')

        # Resend OTP
        if action == 'resend':
            try:
                otp_obj = request.user.otp_verification
                otp = otp_obj.generate_company_email_otp()
                send_company_verification_otp(company, otp)
                messages.success(
                    request,
                    f'New OTP sent to {company.company_email}!'
                )
            except Exception as e:
                messages.error(
                    request,
                    f'Could not resend OTP: {str(e)}'
                )
            return redirect('confirm_company_email')

        otp_entered = request.POST.get('otp', '').strip()

        try:
            otp_obj = request.user.otp_verification
        except OTPVerification.DoesNotExist:
            messages.error(
                request, 'Session expired. Please try again.'
            )
            return redirect('verify_company_email')

        valid, message = otp_obj.verify_company_email_otp(
            otp_entered
        )

        if valid:
            # Mark company as verified
            from django.utils import timezone

            company.verification_status = 'verified'
            company.verified_at = timezone.now()
            otp_obj.company_email_verified = True
            otp_obj.save()
            company.save()

            # Send confirmation email
            try:
                send_mail(
                    '🎉 Company Verified — HireIQ',
                    f'''
Dear {company.hr_name},

Congratulations! {company.company_name} has been
successfully verified on HireIQ!

Your company now shows a ✅ Verified Badge
visible to all candidates on the platform.

You can now:
✅ Post unlimited jobs
✅ Screen candidates with AI
✅ Schedule interviews
✅ Send offer letters

Login at: http://127.0.0.1:8000/login/

Best regards,
HireIQ Team
                    ''',
                    settings.DEFAULT_FROM_EMAIL,
                    [company.user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

            messages.success(
                request,
                f'🎉 Congratulations! '
                f'{company.company_name} is now '
                f'✅ Verified on HireIQ! '
                f'Your verified badge is now visible '
                f'to all candidates.'
            )
            return redirect('home')
        else:
            messages.error(request, f'OTP Error: {message}')

    context = {
        'company': company,
        'company_email': company.company_email,
        'domain_match': company.domain_match,
    }
    return render(
        request,
        'recruitment/confirm_company_email.html',
        context
    )

# ═══════════════════════════════════════════════════════
# FORGOT PASSWORD VIEWS
# ═══════════════════════════════════════════════════════

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, 'Please enter your email.')
            return render(
                request,
                'recruitment/forgot_password.html'
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists or not
            # for security
            messages.success(
                request,
                'If this email is registered, you will '
                'receive a password reset OTP shortly.'
            )
            return render(
                request,
                'recruitment/forgot_password.html'
            )

        # Generate reset OTP
        otp_obj, _ = OTPVerification.objects.get_or_create(
            user=user,
            defaults={'user_type': 'hr'}
        )
        otp_code = otp_obj.generate_otp()

        try:
            send_mail(
                'HireIQ — Password Reset OTP',
                f'''
Dear {user.username},

You requested a password reset for your HireIQ account.

Your OTP for password reset is:

    ━━━━━━━━━━━━━━━━
         {otp_code}
    ━━━━━━━━━━━━━━━━

This OTP is valid for 5 minutes only.

If you did not request this, please ignore this email.
Your password will not be changed.

Best regards,
HireIQ Team
                ''',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            request.session['reset_user_id'] = user.id
            messages.success(
                request,
                f'Password reset OTP sent to {email}!'
            )
            return redirect('reset_password_otp')
        except Exception as e:
            messages.error(
                request,
                'Could not send email. Please try again.'
            )

    return render(request, 'recruitment/forgot_password.html')


def reset_password_otp(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(
            request, 'Session expired. Please try again.'
        )
        return redirect('forgot_password')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'resend':
            otp_obj = user.otp_verification
            otp_code = otp_obj.generate_otp()
            send_mail(
                'HireIQ — Password Reset OTP (Resent)',
                f'Your new OTP is: {otp_code}\n'
                f'Valid for 5 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
            messages.success(request, 'New OTP sent!')
            return redirect('reset_password_otp')

        otp_entered = request.POST.get('otp', '').strip()
        try:
            otp_obj = user.otp_verification
        except OTPVerification.DoesNotExist:
            messages.error(request, 'OTP not found.')
            return redirect('forgot_password')

        if otp_obj.verify_otp(otp_entered):
            # OTP verified — allow password reset
            request.session['reset_otp_verified'] = True
            messages.success(
                request, 'OTP verified! Set your new password.'
            )
            return redirect('reset_password_new')
        else:
            messages.error(
                request, 'Invalid or expired OTP.'
            )

    return render(
        request,
        'recruitment/reset_password_otp.html',
        {'email': user.email}
    )


def reset_password_new(request):
    user_id = request.session.get('reset_user_id')
    verified = request.session.get('reset_otp_verified')

    if not user_id or not verified:
        messages.error(
            request,
            'Session expired. Please start again.'
        )
        return redirect('forgot_password')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        # Validate password
        errors = validate_password_strength(password1)
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(
                request,
                'recruitment/reset_password_new.html'
            )

        if password1 != password2:
            messages.error(
                request, 'Passwords do not match!'
            )
            return render(
                request,
                'recruitment/reset_password_new.html'
            )

        user.set_password(password1)
        user.save()

        # Clear session
        for key in ['reset_user_id', 'reset_otp_verified']:
            request.session.pop(key, None)

        # Send confirmation email
        try:
            send_mail(
                'HireIQ — Password Changed Successfully',
                f'''
Dear {user.username},

Your HireIQ password has been changed successfully.

If you did not make this change, please contact
support immediately.

Best regards,
HireIQ Team
                ''',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(
            request,
            '✅ Password changed successfully! '
            'Please login with your new password.'
        )
        return redirect('login')

    return render(
        request, 'recruitment/reset_password_new.html'
    )

def validate_password_strength(password):
    """Returns list of errors. Empty list means valid."""
    errors = []
    if len(password) < 8:
        errors.append(
            'Password must be at least 8 characters.'
        )
    if not re.search(r'[A-Z]', password):
        errors.append(
            'Password must contain at least one uppercase letter.'
        )
    if not re.search(r'[a-z]', password):
        errors.append(
            'Password must contain at least one lowercase letter.'
        )
    if not re.search(r'\d', password):
        errors.append(
            'Password must contain at least one number.'
        )
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append(
            'Password must contain at least one special character.'
        )
    return errors

def validate_phone(phone):
    """
    Validates Indian mobile numbers.
    Valid formats:
    +91 9876543210
    91 9876543210
    9876543210
    Must start with 6, 7, 8, or 9
    """
    # Remove spaces, dashes, plus
    cleaned = re.sub(r'[\s\-\+]', '', phone)

    # Remove country code if present
    if cleaned.startswith('91') and len(cleaned) == 12:
        cleaned = cleaned[2:]

    # Must be exactly 10 digits
    if not cleaned.isdigit():
        return False, 'Phone number must contain only digits.'
    if len(cleaned) != 10:
        return False, 'Phone number must be exactly 10 digits.'
    if cleaned[0] not in ['6', '7', '8', '9']:
        return False, (
            'Invalid Indian mobile number. '
            'Must start with 6, 7, 8, or 9.'
        )
    return True, cleaned