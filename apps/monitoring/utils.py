"""Utility functions for logging actions to the monitoring app."""
from apps.monitoring.models import Log


def log_action(action, user_email='', message='', request=None, level='info', extra_data=None):
    """Record an action in the system log."""
    try:
        ip = None
        endpoint = ''
        method = ''
        if request:
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded:
                ip = x_forwarded.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            endpoint = request.path
            method = request.method

        Log.objects.create(
            level=level,
            action=action,
            user_email=user_email,
            message=message,
            ip_address=ip,
            endpoint=endpoint,
            method=method,
            extra_data=extra_data or {},
        )
    except Exception:
        pass  # Fail silently to not break main flows
