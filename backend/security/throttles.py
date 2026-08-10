from rest_framework.throttling import SimpleRateThrottle


class SiteAccessIPThrottle(SimpleRateThrottle):
    scope = "site_access_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
