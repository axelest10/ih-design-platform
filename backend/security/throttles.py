from rest_framework.throttling import SimpleRateThrottle


class _MagicLinkIPThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class MagicLinkRequestIPThrottle(_MagicLinkIPThrottle):
    scope = "magic_link_request_ip"


class MagicLinkEmailThrottle(SimpleRateThrottle):
    scope = "magic_link_request_email"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email") or "").strip().casefold()
        if not email:
            return None
        return self.cache_format % {"scope": self.scope, "ident": email}


class MagicLinkVerifyIPThrottle(_MagicLinkIPThrottle):
    scope = "magic_link_verify_ip"
