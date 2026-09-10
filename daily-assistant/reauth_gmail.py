#!/usr/bin/env python3
"""
Google OAuth Re-Authenticator wrapper.
Delegates to reauth_google.py to ensure both Gmail and Google Calendar scopes are requested.
"""
from reauth_google import main

if __name__ == "__main__":
    main()
