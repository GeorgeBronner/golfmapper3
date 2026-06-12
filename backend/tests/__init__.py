import os

# Let the suite run without requiring the environment to be configured.
# Set before any app module is imported (Settings reads it at import time).
# 32+ bytes: PyJWT warns on HMAC keys shorter than the RFC 7518 minimum.
os.environ.setdefault("SECRET_KEY_AUTH", "test-secret-key-0123456789abcdef")
# Never report test runs to Sentry, even if the shell has a DSN configured.
os.environ["SENTRY_DSN"] = ""
