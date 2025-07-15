import os
import json
from google.auth import exceptions
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import Resource as GoogleAPIResource
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


def test_impersonation(target_email: str, credentials_file: str = "clientid.json"):
    """Test service account impersonation with better error handling."""

    # Scopes that the service account is delegated for in the Google Workspace Admin Console.
    SCOPES = [
        "https://www.googleapis.com/auth/cloud-platform",  # General Cloud access (if needed)
        "https://www.googleapis.com/auth/admin.directory.user",  # Example: For Admin SDK Directory API
        "https://www.googleapis.com/auth/drive",  # Example: For Google Drive API
        "https://www.googleapis.com/auth/gmail.send",  # Example: For sending emails
    ]

    try:
        print(f"Attempting to impersonate: {target_email}")
        print(f"Using credentials file: {credentials_file}")

        # Check if credentials file exists
        if not os.path.exists(credentials_file):
            print(f"Error: Credentials file '{credentials_file}' not found")
            return None

        # Try to load and inspect the credentials file
        with open(credentials_file, "r") as f:
            cred_info = json.load(f)
            print(f"Credentials file type: {cred_info.get('type', 'unknown')}")
            if "client_email" in cred_info:
                print(f"Service account email: {cred_info['client_email']}")

        print("Using service account credentials for impersonation...")
        credentials = service_account.Credentials.from_service_account_file(
            filename=credentials_file, scopes=SCOPES, subject=target_email
        )

        print("Refreshing credentials...")
        credentials.refresh(Request())

        print("✅ Impersonation successful!")
        print(f"Access token acquired for: {target_email}")

        # Test with a simple API call
        print("Testing with Drive API...")
        drive_service = build("drive", "v3", credentials=credentials)
        about = drive_service.about().get(fields="user").execute()
        print(f"✅ Successfully authenticated as: {about['user']['emailAddress']}")

        return credentials

    except exceptions.RefreshError as e:
        print(f"❌ Impersonation failed: {e}")
        if "Gaia id not found" in str(e):
            print(f"💡 The email '{target_email}' doesn't exist in your Google Workspace domain.")
            print("   Please verify the email address or try a different user.")
        elif "unauthorized_client" in str(e):
            print("💡 Domain-wide delegation might not be properly configured.")
            print("   Check Google Workspace Admin Console settings.")
        return None

    except FileNotFoundError:
        print(f"❌ Credentials file '{credentials_file}' not found")
        return None

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


if __name__ == "__main__":
    # Test impersonation
    target_email = "dsai.rag@team.deepsense.ai"  # Change this to a valid email in your domain

    credentials = test_impersonation(target_email)

    if credentials:
        print("\n🎉 Impersonation test completed successfully!")
    else:
        print("\n❌ Impersonation test failed. Please check the suggestions above.")
