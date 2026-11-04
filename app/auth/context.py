"""
Trusted authentication context.

Only the backend creates this object, from a verified session. The future AI
assistant must never build one itself; tools receive it from the dispatcher.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    email_verified: bool
    source: str = "session"
