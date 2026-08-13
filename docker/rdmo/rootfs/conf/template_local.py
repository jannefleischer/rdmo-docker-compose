import os

from . import MIDDLEWARE  # if this import is not alreay present in the file

DEFAULT_URI_PREFIX = os.environ["DEFAULT_URI_PREFIX"]

VENDOR_CDN = False
MIDDLEWARE.append("allauth.account.middleware.AccountMiddleware")

"""
Debug mode, don't use this in production
"""
DEBUG = False

"""
A secret key for a particular Django installation. This is used to provide
cryptographic signing, and should be set to a unique, unpredictable value.
"""
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

"""
The list of URLs under which this application is available
"""
ALLOWED_HOSTS = [x.strip() for x in os.environ["ALLOWED_HOSTS"].split(",")]
# ALLOWED_HOSTS = ['localhost', 'ip6-localhost', '127.0.0.1', '[::1]', 'rdmo']

# enable settings below if rdmo docker compose is behind a reverse proxy
# to make sure rdmo's urls are correctly set (i.e. in sent mails etc.)
# USE_X_FORWARDED_HOST = True
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

"""
The root url of your application, only needed when its not '/'
"""
try:
    BASE_URL = os.environ["BASE_URL"]
except KeyError:
    pass

"""
Language code and time zone
"""
LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"

"""
The database connection to be used, see also:
http://rdmo.readthedocs.io/en/latest/configuration/databases.html
"""
# NOTE: using environment variables here that come from the docker
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ["POSTGRES_PORT"],
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': '',
#         'USER': '',
#         'PASSWORD': '',
#         'HOST': '',
#         'PORT': '',
#     }
# }

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': '',
#     }
# }

"""
E-Mail configuration, see also:
http://rdmo.readthedocs.io/en/latest/configuration/email.html
"""
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'localhost'
# EMAIL_PORT = '25'
# EMAIL_HOST_USER = ''
# EMAIL_HOST_PASSWORD = ''
# EMAIL_USE_TLS = False
# EMAIL_USE_SSL = False
# DEFAULT_FROM_EMAIL = ''

"""
Allauth configuration, see also:
http://rdmo.readthedocs.io/en/latest/configuration/authentication/allauth.html
"""

# BASE_DIR is not imported here: it is defined by config/settings/__init__.py
# before it includes this file, so it is already in scope
from rdmo.core.settings import AUTHENTICATION_BACKENDS, INSTALLED_APPS, SETTINGS_EXPORT

ACCOUNT = True
ACCOUNT_TERMS_OF_USE = True

# Self-registration with a local username and password. Off, because an open
# signup form on a public instance collects bot registrations. Note that this
# only governs *local* accounts: SOCIALACCOUNT_SIGNUP below is a separate gate,
# so users arriving through the identity provider still get an account created
# for them. Turn this back on if people without an account at the provider need
# to be able to register themselves.
ACCOUNT_SIGNUP = False

# Shows the 3rd party login parts of rdmo's ui. The OIDC section further down
# turns this on by itself once it is configured; set it to True by hand when
# enabling one of the classic providers listed below instead.
SOCIALACCOUNT = False

INSTALLED_APPS += [
    "allauth",
    "allauth.account",
    # The classic providers below get their credentials from a "social
    # application" in the django admin, see the administration chapter of the
    # rdmo docs. Uncommenting one of them also needs 'allauth.socialaccount'
    # and SOCIALACCOUNT = True above - the OIDC section further down adds both
    # on its own when it is switched on, and skips apps already listed here.
    #     'allauth.socialaccount',
    #     'allauth.socialaccount.providers.facebook',
    #     'allauth.socialaccount.providers.github',
    #     'allauth.socialaccount.providers.google',
    #     'allauth.socialaccount.providers.orcid',
    #     'allauth.socialaccount.providers.twitter',
]

AUTHENTICATION_BACKENDS.append("allauth.account.auth_backends.AuthenticationBackend")

"""
OpenID Connect (keycloak et al) via allauth's generic openid_connect provider,
see also:
https://docs.allauth.org/en/latest/socialaccount/providers/openid_connect.html

This is driven entirely from the environment: the provider is only wired up
when OIDC_CLIENT_ID, OIDC_CLIENT_SECRET and OIDC_SERVER_URL are all set (see
.env.defaults), so the stack still starts unchanged without them.

The redirect/callback url to register with the identity provider is

    https://<URL_HOSTNAME>/account/<OIDC_PROVIDER_ID>/login/callback/

Note the singular "account" and the *absent* "/oidc/" segment: rdmo mounts
allauth under /account/ (rdmo/core/urls/__init__.py) and sets
SOCIALACCOUNT_OPENID_CONNECT_URL_PREFIX = "" (rdmo/core/settings.py), so the
provider urls sit directly underneath it. Both differ from what the allauth
docs show, and a mismatch here is rejected by the provider as an invalid
redirect_uri.

Do NOT additionally create a "social application" in the django admin for this
provider: allauth blends db and settings apps, finds two, and fails the login
with MultipleObjectsReturned. The settings below fully replace that step.
"""

OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")
OIDC_SERVER_URL = os.environ.get("OIDC_SERVER_URL", "")
OIDC_PROVIDER_ID = os.environ.get("OIDC_PROVIDER_ID", "keycloak")
OIDC_PROVIDER_NAME = os.environ.get("OIDC_PROVIDER_NAME", "SSO")

OIDC_ENABLED = bool(OIDC_CLIENT_ID and OIDC_CLIENT_SECRET and OIDC_SERVER_URL)

if OIDC_ENABLED:
    SOCIALACCOUNT = True

    # rdmo's AccountAdapter, extended so that logging out of rdmo also ends the
    # session at the identity provider instead of only dropping the local one.
    # See config/oidc.py, which the image installs next to this file.
    ACCOUNT_ADAPTER = "config.oidc.OIDCLogoutAccountAdapter"

    # Theme app overriding the login button snippet, so that OIDC_CLIENT_LINKIMAGE
    # replaces the provider logo rdmo hardcodes. It has to come before
    # "rdmo.accounts" for its template to win, hence prepending.
    INSTALLED_APPS = ["rdmo_oidc_theme"] + INSTALLED_APPS

    # sh/install-rdmo-app.sh stages the configured image into the theme app's
    # static folder under its original name. Only advertise it to the template
    # once it is actually there, so a typo in the path degrades to rdmo's own
    # logo rather than to a broken image.
    _linkimage = os.path.basename(os.environ.get("OIDC_CLIENT_LINKIMAGE", ""))
    OIDC_CLIENT_LINKIMAGE_STATIC = ""
    if _linkimage and (BASE_DIR / "rdmo_oidc_theme" / "static" / "rdmo_oidc_theme" / _linkimage).exists():
        OIDC_CLIENT_LINKIMAGE_STATIC = f"rdmo_oidc_theme/{_linkimage}"

    # django-settings-export only passes through what is listed here
    SETTINGS_EXPORT = SETTINGS_EXPORT + ["OIDC_CLIENT_LINKIMAGE_STATIC"]

    # rdmo's own flag, read by rdmo.accounts.socialaccount.SocialAccountAdapter:
    # with it left at False, nobody who does not already have an rdmo account
    # can log in via the provider at all
    SOCIALACCOUNT_SIGNUP = True

    # False keeps the intermediate signup form, which is what carries rdmo's
    # terms-of-use consent field - only set this to True together with
    # ACCOUNT_TERMS_OF_USE = False above
    SOCIALACCOUNT_AUTO_SIGNUP = False

    # let an oidc identity attach to an existing local account with the same
    # address, instead of failing with "an account already exists with this
    # email". this trusts the provider's email verification, which is fine for
    # a realm you operate yourself - remove both lines if the realm allows
    # self-registration with unverified addresses.
    SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
    SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

    # guarded, so this stays correct if 'allauth.socialaccount' was already
    # uncommented above for one of the classic providers - a duplicate entry
    # makes django refuse to start with "Application labels aren't unique"
    for app in ("allauth.socialaccount", "allauth.socialaccount.providers.openid_connect"):
        if app not in INSTALLED_APPS:
            INSTALLED_APPS.append(app)

    SOCIALACCOUNT_PROVIDERS = {
        "openid_connect": {
            "APPS": [
                {
                    "provider_id": OIDC_PROVIDER_ID,
                    "name": OIDC_PROVIDER_NAME,
                    "client_id": OIDC_CLIENT_ID,
                    "secret": OIDC_CLIENT_SECRET,
                    # the plain issuer url is enough, allauth appends
                    # /.well-known/openid-configuration itself
                    "settings": {"server_url": OIDC_SERVER_URL},
                },
            ],
        },
    }

    # put users into rdmo groups on first login through the provider, e.g.
    # SOCIALACCOUNT_GROUPS = {OIDC_PROVIDER_ID: ["editor"]}

    # to make oidc the only way in, hide the local login form and signup:
    # LOGIN_FORM = False
    # ACCOUNT_SIGNUP = False

"""
LDAP, see also:
http://rdmo.readthedocs.io/en/latest/configuration/authentication/ldap.html
"""
# import ldap
# from django_auth_ldap.config import LDAPSearch
# from rdmo.core.settings import AUTHENTICATION_BACKENDS
#
# PROFILE_UPDATE = False
#
# AUTH_LDAP_SERVER_URI = "ldap://ldap.example.com"
# AUTH_LDAP_BIND_DN = "cn=admin,dc=ldap,dc=example,dc=com"
# AUTH_LDAP_BIND_PASSWORD = "admin"
# AUTH_LDAP_USER_SEARCH = LDAPSearch("dc=ldap,dc=example,dc=com", ldap.SCOPE_SUBTREE, "(uid=%(user)s)")
#
# AUTH_LDAP_USER_ATTR_MAP = {
#     "first_name": "givenName",
#     "last_name": "sn",
#     'email': 'mail'
# }
#
# AUTHENTICATION_BACKENDS.insert(
#     AUTHENTICATION_BACKENDS.index('django.contrib.auth.backends.ModelBackend'),
#     'django_auth_ldap.backend.LDAPBackend'
# )

"""
Shibboleth, see also:
http://rdmo.readthedocs.io/en/latest/configuration/authentication/shibboleth.html
"""
# from rdmo.core.settings import INSTALLED_APPS, AUTHENTICATION_BACKENDS, MIDDLEWARE_CLASSES
#
# SHIBBOLETH = True
# PROFILE_UPDATE = False
#
# INSTALLED_APPS += ['shibboleth']
#
# SHIBBOLETH_ATTRIBUTE_MAP = {
#     'uid': (True, 'username'),
#     'givenName': (True, 'first_name'),
#     'sn': (True, 'last_name'),
#     'mail': (True, 'email'),
# }
#
# AUTHENTICATION_BACKENDS.append('shibboleth.backends.ShibbolethRemoteUserBackend')
#
# LOGIN_URL = '/Shibboleth.sso/Login?target=/projects'
# LOGOUT_URL = '/Shibboleth.sso/Logout'

"""
Theme, see also:
http://rdmo.readthedocs.io/en/latest/configuration/themes.html
"""
# THEME_DIR = os.path.join(BASE_DIR, 'theme')

"""
Export Formats
"""
# from django.utils.translation import ugettext_lazy as _
# EXPORT_FORMATS = (
#     ('pdf', _('PDF')),
#     ('rtf', _('Rich Text Format')),
#     ('odt', _('Open Office')),
#     ('docx', _('Microsoft Office')),
#     ('html', _('HTML')),
#     ('markdown', _('Markdown')),
#     ('mediawiki', _('mediawiki')),
#     ('tex', _('LaTeX'))
# )

"""
Cache, see also:
http://rdmo.readthedocs.io/en/latest/configuration/cache.html
"""
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
#         'LOCATION': '127.0.0.1:11211',
#         'KEY_PREFIX': 'rdmo_default'
#     },
#     'api': {
#         'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
#         'LOCATION': '127.0.0.1:11211',
#         'KEY_PREFIX': 'rdmo_api'
#     },
# }

"""
LOGGING
"""
LOGGING_DIR = os.environ["LOGGING_DIR"]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
    },
    "formatters": {
        "default": {"format": "[%(asctime)s] %(levelname)s: %(message)s"},
        "name": {"format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s"},
        "console": {"format": "[%(asctime)s] %(message)s"},
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(filename)s %(lineno)d: %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "fullverbose": {
            "format": "%(asctime)s [%(levelname)s] %(pathname)s %(lineno)d: %(message)s"
        },
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "error_log": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": os.path.join(LOGGING_DIR, "rdmo_error.log"),
            "formatter": "default",
        },
        "rdmo_log": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": os.path.join(LOGGING_DIR, "rdmo.log"),
            "formatter": "fullverbose",
        },
        "console": {
            "level": "DEBUG",
            #'filters': ['require_debug_true'],
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.request": {
            # 'handlers': ['mail_admins', 'error_log'],
            # 'level': 'ERROR',
            # 'propagate': True
            "handlers": ["console"],
            "level": "ERROR",
        },
        "rdmo": {
            # 'handlers': ['rdmo_log'],
            # 'level': 'DEBUG',
            # 'propagate': False
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}
