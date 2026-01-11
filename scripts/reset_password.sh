#!/bin/bash
cd "$(dirname "$0")/../backend"
uv run python ../scripts/reset_user_password.py
