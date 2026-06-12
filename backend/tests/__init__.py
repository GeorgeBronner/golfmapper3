import os

# Let the suite run without requiring the environment to be configured.
# Set before any app module is imported (Settings reads it at import time).
os.environ.setdefault("SECRET_KEY_AUTH", "test-secret-key")
