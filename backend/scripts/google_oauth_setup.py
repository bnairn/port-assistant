#!/usr/bin/env python3
"""
Google OAuth 2.0 Setup Helper

This script helps you obtain a refresh token for Google Workspace APIs.

Prerequisites:
1. Go to https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Enable Gmail API and Google Calendar API
4. Create OAuth 2.0 credentials (Desktop app type)
5. Download the credentials and note your Client ID and Client Secret

This script will:
1. Generate an authorization URL
2. Wait for you to authorize the app
3. Exchange the authorization code for a refresh token
4. Display the refresh token to add to your .env file
"""

import sys
from urllib.parse import urlencode
import httpx

# Scopes needed for Gmail and Calendar access
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # For desktop/CLI apps


def main():
    print("=" * 70)
    print("Google OAuth 2.0 Setup Helper")
    print("=" * 70)
    print()

    # Get credentials from user
    print("Step 1: Enter your Google Cloud Console credentials")
    print("-" * 70)
    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()
    print()

    if not client_id or not client_secret:
        print("Error: Client ID and Secret are required!")
        sys.exit(1)

    # Generate authorization URL
    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"

    print("Step 2: Authorize the application")
    print("-" * 70)
    print("1. Open this URL in your browser:")
    print()
    print(auth_url)
    print()
    print("2. Sign in with your Google account")
    print("3. Grant the requested permissions")
    print("4. Copy the authorization code")
    print()

    auth_code = input("Enter the authorization code: ").strip()
    print()

    if not auth_code:
        print("Error: Authorization code is required!")
        sys.exit(1)

    # Exchange code for tokens
    print("Step 3: Exchanging code for refresh token...")
    print("-" * 70)

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    try:
        response = httpx.post(token_url, data=token_data)
        response.raise_for_status()
        tokens = response.json()

        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")

        if not refresh_token:
            print("Error: No refresh token received!")
            print("Response:", tokens)
            print()
            print("Note: If you don't see a refresh token, you may need to:")
            print("1. Revoke access at https://myaccount.google.com/permissions")
            print("2. Run this script again with prompt=consent")
            sys.exit(1)

        print("Success! ✅")
        print()
        print("=" * 70)
        print("Add these to your .env file:")
        print("=" * 70)
        print()
        print(f"GOOGLE_CLIENT_ID={client_id}")
        print(f"GOOGLE_CLIENT_SECRET={client_secret}")
        print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
        print()
        print("=" * 70)
        print()

        # Test the token
        print("Testing the credentials...")
        test_response = httpx.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if test_response.status_code == 200:
            profile = test_response.json()
            print(f"✅ Successfully connected to Gmail for: {profile.get('emailAddress')}")
        else:
            print("⚠️  Could not verify Gmail connection")
            print(f"Status: {test_response.status_code}")
            print(f"Response: {test_response.text}")

    except httpx.HTTPStatusError as e:
        print(f"Error: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
