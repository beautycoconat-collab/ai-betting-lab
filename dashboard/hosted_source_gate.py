"""Read-only, fail-closed review of provider permissions."""
from datetime import datetime, timezone


def approved(policy, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(policy, dict) or policy.get("status") != "approved":
        return False
    if not policy.get("license") or not policy.get("permission_url"):
        return False
    try:
        expires = policy["review_expires"]
        if isinstance(expires, str):
            expires = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        return (expires.tzinfo is not None and expires > now and
                type(policy.get("max_daily")) is int and policy["max_daily"] > 0 and
                type(policy.get("min_interval_seconds")) is int and
                policy["min_interval_seconds"] >= 0)
    except (KeyError, ValueError, TypeError, AttributeError):
        return False
