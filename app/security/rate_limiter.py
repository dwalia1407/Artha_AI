"""
Thread-safe sliding window rate limiter for authentication and sensitive endpoints.
"""

import threading
import time
from flask import current_app, request

from app.errors import RateLimited


class InMemoryRateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self._records = {}  # key -> list of float timestamps

    def check(self, key, max_attempts, window_seconds):
        """
        Check if an action with 'key' is allowed.
        Returns (allowed: bool, remaining: int, retry_after: int).
        """
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._records.get(key, [])
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self._records[key] = valid_timestamps

            count = len(valid_timestamps)
            if count >= max_attempts:
                oldest_in_window = valid_timestamps[0]
                retry_after = max(1, int(oldest_in_window + window_seconds - now))
                return False, 0, retry_after
            return True, max_attempts - count, 0

    def record_failure(self, key):
        """Record an attempt/failure for 'key'."""
        now = time.time()
        with self._lock:
            if key not in self._records:
                self._records[key] = []
            self._records[key].append(now)

    def reset(self, key):
        """Reset attempts for 'key'."""
        with self._lock:
            self._records.pop(key, None)

    def clear(self):
        """Clear all rate limiting state (for testing)."""
        with self._lock:
            self._records.clear()


limiter = InMemoryRateLimiter()


def get_client_ip():
    """Extract client IP, preferring X-Forwarded-For if behind a reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the list is the original client
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def check_auth_rate_limit(action, identifier=""):
    """
    Check rate limit for an action (e.g. 'login', 'register', 'verify_resend')
    by client IP and optional identifier (e.g. email).
    Raises RateLimited if either exceeds limits.
    """
    ip = get_client_ip()
    ident = (identifier or "").strip().lower()

    if action == "login":
        max_attempts = current_app.config.get("RATE_LIMIT_LOGIN_MAX_ATTEMPTS", 5)
        window = current_app.config.get("RATE_LIMIT_LOGIN_WINDOW_SECONDS", 900)
    elif action == "register":
        max_attempts = current_app.config.get("RATE_LIMIT_REGISTER_MAX_ATTEMPTS", 10)
        window = current_app.config.get("RATE_LIMIT_REGISTER_WINDOW_SECONDS", 3600)
    else:
        max_attempts = 5
        window = 900

    # Check IP limit
    ip_key = f"{action}:ip:{ip}"
    allowed, remaining, retry_after = limiter.check(ip_key, max_attempts, window)
    if not allowed:
        raise RateLimited(
            f"Too many {action} attempts from your IP address. Please try again in {retry_after} seconds.",
            retry_after=retry_after,
            details={"action": action, "retry_after": retry_after}
        )

    # Check identifier limit if provided
    if ident:
        ident_key = f"{action}:id:{ident}"
        allowed, remaining, retry_after = limiter.check(ident_key, max_attempts, window)
        if not allowed:
            raise RateLimited(
                f"Too many {action} attempts for this account. Please try again in {retry_after} seconds.",
                retry_after=retry_after,
                details={"action": action, "retry_after": retry_after}
            )


def record_auth_failure(action, identifier=""):
    """Record an authentication failure for both IP and identifier."""
    ip = get_client_ip()
    ident = (identifier or "").strip().lower()

    ip_key = f"{action}:ip:{ip}"
    limiter.record_failure(ip_key)

    if ident:
        ident_key = f"{action}:id:{ident}"
        limiter.record_failure(ident_key)


def reset_auth_failures(action, identifier=""):
    """Reset failures on successful authentication."""
    ip = get_client_ip()
    ident = (identifier or "").strip().lower()

    ip_key = f"{action}:ip:{ip}"
    limiter.reset(ip_key)

    if ident:
        ident_key = f"{action}:id:{ident}"
        limiter.reset(ident_key)

