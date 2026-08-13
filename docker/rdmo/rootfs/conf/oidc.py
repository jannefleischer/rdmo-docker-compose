"""
Docker glue for the rdmo-app: RP-initiated logout for the openid_connect
provider.

This file is shipped with the rdmo image and refreshed into
${RDMO_APP}/config/ on every container start (see sh/install-rdmo-app.sh).
Edit it in the rdmo-docker-compose repo under docker/rdmo/rootfs/conf/oidc.py,
not in the app checkout - changes there are overwritten on the next start.

Why this exists: on logout allauth only ends the local django session. The
session at the identity provider stays open, so the next "login" hands the
very same user straight back in without asking for anything - on a shared
machine that is indistinguishable from never having logged out. The OpenID
Connect RP-Initiated Logout spec closes this by sending the user on to the
provider's end_session_endpoint:
https://openid.net/specs/openid-connect-rpinitiated-1_0.html

Note that the spec's id_token_hint is deliberately not sent: allauth verifies
the id token and then stores only the decoded claims (see
openid_connect/views.py, _decode_id_token), discarding the original JWT, so it
is simply not available to us at logout time. The client is identified with
client_id instead, which the spec allows as well. The visible consequence is
that a provider may ask "do you really want to log out?" once, rather than
ending the session silently.
"""

import logging
from urllib.parse import urlencode

from django.conf import settings

import requests

from allauth.socialaccount.models import SocialAccount

from rdmo.accounts.account import AccountAdapter

logger = logging.getLogger(__name__)

# the discovery document is static in practice, so fetch it at most once per
# worker process instead of on every single logout
_openid_config_cache = {}


def _end_session_endpoint(server_url):
    """Return the provider's logout url from its discovery document."""
    if server_url not in _openid_config_cache:
        url = server_url
        if "/.well-known/" not in url:
            url = url.rstrip("/") + "/.well-known/openid-configuration"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        _openid_config_cache[server_url] = response.json()

    return _openid_config_cache[server_url].get("end_session_endpoint")


class OIDCLogoutAccountAdapter(AccountAdapter):
    """rdmo's AccountAdapter, extended to also end the session at the provider."""

    def get_logout_redirect_url(self, request):
        # allauth resolves this url *before* it flushes the session
        # (see allauth.account.views.LogoutView.post), so request.user is
        # still the user that is about to be logged out
        local_url = super().get_logout_redirect_url(request)

        provider_id = getattr(settings, "OIDC_PROVIDER_ID", "")
        server_url = getattr(settings, "OIDC_SERVER_URL", "")
        client_id = getattr(settings, "OIDC_CLIENT_ID", "")
        if not (provider_id and server_url and client_id):
            return local_url

        user = getattr(request, "user", None)
        # this hook also runs when nobody is logged in at all
        if user is None or not user.is_authenticated:
            return local_url

        # accounts that signed in with a local password have no session at the
        # provider to end, and must not be bounced through it
        if not SocialAccount.objects.filter(user=user, provider=provider_id).exists():
            return local_url

        try:
            end_session_url = _end_session_endpoint(server_url)
        except (requests.RequestException, ValueError):
            logger.exception(
                "could not read the oidc discovery document, ending the local "
                "session only - the provider session stays open"
            )
            return local_url

        if not end_session_url:
            logger.warning(
                "the oidc provider advertises no end_session_endpoint, ending "
                "the local session only - the provider session stays open"
            )
            return local_url

        params = {
            "client_id": client_id,
            # has to be registered with the provider as a valid post logout
            # redirect uri, otherwise it rejects the whole logout request
            "post_logout_redirect_uri": request.build_absolute_uri(local_url),
        }
        return f"{end_session_url}?{urlencode(params)}"
