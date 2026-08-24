from functools import lru_cache

from authlib.integrations.base_client import OAuthError
from authlib.integrations.django_client import OAuth
from authlib.integrations.django_client.apps import DjangoOAuth2App
from authlib.oidc.core import CodeIDToken, ImplicitIDToken, UserInfo
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from joserfc import jwt
from joserfc.errors import InvalidKeyIdError
from joserfc.jwk import KeySet


class StrictHubOAuth2App(DjangoOAuth2App):
    """Pin Hub ID token verification to asymmetric RS256."""

    def parse_id_token(
        self,
        token,
        nonce,
        claims_options=None,
        claims_cls=None,
        leeway=30,
    ):
        if "id_token" not in token:
            return None

        claims_params = {"nonce": nonce, "client_id": self.client_id}
        if claims_cls is None:
            if "access_token" in token:
                claims_params["access_token"] = token["access_token"]
                claims_cls = CodeIDToken
            else:
                claims_cls = ImplicitIDToken

        metadata = self.load_server_metadata()
        if claims_options is None and "issuer" in metadata:
            claims_options = {"iss": {"values": [metadata["issuer"]]}}
        if "RS256" not in metadata.get("id_token_signing_alg_values_supported", []):
            raise OAuthError(description="Hub discovery does not advertise RS256")

        key_set = KeySet.import_key_set(self.fetch_jwk_set())
        try:
            decoded = jwt.decode(token["id_token"], key=key_set, algorithms=["RS256"])
        except InvalidKeyIdError:
            key_set = KeySet.import_key_set(self.fetch_jwk_set(force=True))
            decoded = jwt.decode(token["id_token"], key=key_set, algorithms=["RS256"])

        claims = claims_cls(decoded.claims, decoded.header, claims_options, claims_params)
        claims.validate(leeway=leeway)
        return UserInfo(claims)


@lru_cache(maxsize=8)
def _registered_hub_client(
    issuer: str,
    client_id: str,
    client_secret: str,
    state_max_age: int,
):
    oauth = OAuth()
    oauth.oauth2_client_cls = StrictHubOAuth2App
    oauth.register(
        name="hub",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=f"{issuer}/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid profile email",
            "code_challenge_method": "S256",
            "token_endpoint_auth_method": "client_secret_basic",
            "id_token_signed_response_alg": "RS256",
            "default_timeout": 10,
        },
    )
    client = oauth.create_client("hub")
    client.framework.expires_in = state_max_age
    return client


def get_hub_oidc_client():
    if not settings.HUB_OIDC_ENABLED:
        raise ImproperlyConfigured("El inicio de sesión del Hub no está habilitado.")
    return _registered_hub_client(
        settings.HUB_OIDC_ISSUER,
        settings.HUB_OIDC_CLIENT_ID,
        settings.HUB_OIDC_CLIENT_SECRET,
        settings.HUB_OIDC_STATE_MAX_AGE_SECONDS,
    )
