class NoCacheMiddleware:
    """
    Prevents browser from caching authenticated pages.
    This stops the back button from showing logged-in
    pages after logout.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Add no-cache headers to all responses
        response['Cache-Control'] = (
            'no-store, no-cache, must-revalidate, '
            'max-age=0, private'
        )
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response