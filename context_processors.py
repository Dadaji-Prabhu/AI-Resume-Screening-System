def user_type(request):
    is_hr = False
    is_candidate = False
    company = None
    candidate_profile = None
    notifications = []
    notification_count = 0

    if request.user.is_authenticated:
        try:
            company = request.user.company
            is_hr = True
        except Exception:
            is_hr = False

        try:
            candidate_profile = request.user.candidate_profile
            is_candidate = True
            from .models import CandidateNotification
            unread = CandidateNotification.objects.filter(
                candidate_email=request.user.email,
                is_read=False
            ).order_by('-created_at')[:5]
            notifications = list(unread)
            notification_count = CandidateNotification.objects.filter(
                candidate_email=request.user.email,
                is_read=False
            ).count()
        except Exception:
            is_candidate = False

    return {
        'is_hr': is_hr,
        'is_candidate': is_candidate,
        'user_company': company,
        'user_candidate_profile': candidate_profile,
        'notifications': notifications,
        'notification_count': notification_count,
    }