from rest_framework.throttling import SimpleRateThrottle

from common.observability import operation_event


class LoginIPThrottle(SimpleRateThrottle):
    scope = "login_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }

    def allow_request(self, request, view):
        allowed = super().allow_request(request, view)
        if not allowed:
            operation_event(
                "authentication.rate_limited",
                status="rejected",
                http_status=429,
            )
        return allowed
