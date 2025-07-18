# How-To: Setup and Query Google Drive Source

This guide shows you how to set up and use Google Drive as a source in Ragbits, including downloading files and folders from Google Drive.

## Prerequisites Setup

### 1. Enable Google Drive API

First, you need to enable the Google Drive API in your Google Cloud project:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to **APIs & Services > Library**
4. Search for "Google Drive API"
5. Click on "Google Drive API" and click **Enable**

### 2. Create a Service Account

To authenticate with Google Drive programmatically, you'll need a service account:

1. In Google Cloud Console, go to **IAM & Admin > Service Accounts**
2. Click **Create Service Account**
3. Enter a name (e.g., "ragbits-google-drive")
4. Add a description (optional)
5. Click **Create and Continue**
6. Skip role assignment for now (click **Continue**)
7. Click **Done**

### 3. Generate Service Account Key

Now you need to create and download the JSON credentials file:

1. In the Service Accounts list, click on your newly created service account
2. Go to the **Keys** tab
3. Click **Add Key > Create new key**
4. Select **JSON** format
5. Click **Create**
6. The JSON file will be downloaded automatically
7. Save this file securely (e.g., as `service-account-key.json`)

!!! warning "Security Note"
    Keep your service account key file secure and never commit it to version control. Consider using environment variables or secure secret management.

### 4. Grant Access to Google Drive Files/Folders

Since the service account is not a regular user, you need to share the Google Drive files or folders with the service account:

1. Open the JSON key file and copy the `client_email` value (it looks like `your-service@project.iam.gserviceaccount.com`)
2. In Google Drive, right-click on the file or folder you want to access
3. Click **Share**
4. Paste the service account email and set permissions (Viewer is sufficient for reading)
5. Click **Send**

## Basic Usage

### Setting Up Credentials

```python
from ragbits.core.sources.google_drive import GoogleDriveSource

# Set the path to your service account key file
GoogleDriveSource.set_credentials_file_path("path/to/service-account-key.json")
```

### Example: Download Files from Google Drive

```python
import asyncio
from ragbits.core.sources.google_drive import GoogleDriveSource

async def download_google_drive_files():
    # Set credentials file path
    GoogleDriveSource.set_credentials_file_path("service-account-key.json")

    # Example 1: Download a single file by ID
    file_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"  # Example Google Sheets ID
    sources = await GoogleDriveSource.from_uri(file_id)

    for source in sources:
        if not source.is_folder:
            local_path = await source.fetch()
            print(f"Downloaded: {source.file_name} to {local_path}")

    # Example 2: Download all files from a folder (non-recursive)
    folder_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    sources = await GoogleDriveSource.from_uri(f"{folder_id}/*")

    for source in sources:
        if not source.is_folder:
            local_path = await source.fetch()
            print(f"Downloaded: {source.file_name} to {local_path}")

    # Example 3: Download all files recursively from a folder
    sources = await GoogleDriveSource.from_uri(f"{folder_id}/**")

    for source in sources:
        if not source.is_folder:
            try:
                local_path = await source.fetch()
                print(f"Downloaded: {source.file_name} to {local_path}")
            except Exception as e:
                print(f"Failed to download {source.file_name}: {e}")

# Run the example
asyncio.run(download_google_drive_files())
```

## URI Patterns

The Google Drive source supports several URI patterns:

| Pattern | Description | Example |
|---------|-------------|---------|
| `<file_id>` | Single file or folder by ID | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms` |
| `<folder_id>/*` | All files directly in folder | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/*` |
| `<folder_id>/<prefix>*` | Files in folder starting with prefix | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/report*` |
| `<folder_id>/**` | All files recursively in folder | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/**` |

## Environment Variables

You can also set up credentials using environment variables:

```bash
# Set the service account key as JSON string
export GOOGLE_DRIVE_CLIENTID_JSON='{"type": "service_account", "project_id": "...", ...}'

# Or set the path to the key file
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

## Advanced Example: Processing Documents

```python
import asyncio
from ragbits.core.sources.google_drive import GoogleDriveSource

async def process_drive_documents():
    """Example of processing documents from Google Drive."""

    # Set up credentials
    GoogleDriveSource.set_credentials_file_path("service-account-key.json")

    # Define the folder containing documents
    documents_folder_id = "your-folder-id-here"

    try:
        # Get all files from the folder recursively
        sources = await GoogleDriveSource.from_uri(f"{documents_folder_id}/**")

        processed_count = 0
        skipped_count = 0

        for source in sources:
            if source.is_folder:
                print(f"Skipping folder: {source.file_name}")
                continue

            # Filter by file type (example: only process text and document files)
            if source.mime_type in [
                'text/plain',
                'application/pdf',
                'application/vnd.google-apps.document',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]:
                try:
                    local_path = await source.fetch()
                    print(f" Processed: {source.file_name} (Type: {source.mime_type})")

                    # Here you could add your document processing logic
                    # For example: extract text, analyze content, etc.

                    processed_count += 1
                except Exception as e:
                    print(f" Failed to process {source.file_name}: {e}")
            else:
                print(f"  Skipped: {source.file_name} (Type: {source.mime_type})")
                skipped_count += 1

        print(f"\n Summary:")
        print(f"   Processed: {processed_count} files")
        print(f"   Skipped: {skipped_count} files")

    except Exception as e:
        print(f"Error accessing Google Drive: {e}")

# Run the example
asyncio.run(process_drive_documents())
```

## Impersonating Google Accounts

You can configure your Google service account to impersonate other users in your Google Workspace domain. This is useful when you need to access files or perform actions on behalf of specific users.

### Step 1: Enable Domain-Wide Delegation

1. **Sign in to the [Google Admin Console](https://admin.google.com/) as a Super Admin.**
2. Navigate to:
    **Security > Access and data control > API controls > MANAGE DOMAIN WIDE DELEGATION**
3. Add a new API client or edit an existing one, and include the following OAuth scopes:
     - `https://www.googleapis.com/auth/cloud-platform`
     - `https://www.googleapis.com/auth/drive`
4. Click **Authorize** or **Save** to apply the changes.

### Step 2: Impersonate a User in Your Code

After configuring domain-wide delegation, you can specify a target user to impersonate when using the `GoogleDriveSource` in your code.

```python
from ragbits.core.sources.google_drive import GoogleDriveSource

target_email = "johnDoe@yourdomain.com"
credentials_file = "service-account-key.json"

# Set the path to your service account key file
GoogleDriveSource.set_credentials_file_path(credentials_file)

# Set the email address of the user to impersonate
GoogleDriveSource.set_impersonation_target(target_email)
```

**Note:**
- The `target_email` must be a valid user in your Google Workspace domain.
- Ensure your service account has been granted domain-wide delegation as described above.

This setup allows your service account to act on behalf of the specified user, enabling access to their Google Drive files and resources as permitted by the assigned scopes.

## Troubleshooting

### Common Issues

1. **"Service account info was not in the expected format"**
    - Make sure you're using a service account key file, not OAuth2 client credentials
    - Verify the JSON file contains required fields: `client_email`, `private_key`, `token_uri`

2. **"File not found" or "Permission denied"**
    - Ensure the file/folder is shared with your service account email
    - Check that the file ID is correct
    - Verify the service account has at least "Viewer" permissions

3. **"Google Drive API not enabled"**
    - Enable the Google Drive API in Google Cloud Console
    - Wait a few minutes for the API to be fully activated

4. **"Quota exceeded"**
    - Google Drive API has usage limits
    - Implement rate limiting in your code
    - Consider upgrading your Google Cloud quotas if needed

5. **"Export size limit exceeded"**
    - Google Workspace files (Docs, Sheets, etc.) have a 9MB export limit
    - Large Google Workspace files may fail to download
    - Consider splitting large documents or using alternative export methods

### Getting File/Folder IDs

You can find Google Drive file or folder IDs in several ways:

1. **From the URL**: When viewing a file in Google Drive, the ID is in the URL:
   ```
   https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/view
                                   ^--- This is the file ID ---^
   ```

2. **Right-click method**: Right-click → "Get link" → Extract ID from the shareable link

3. **Programmatically**: Use the Google Drive API to search and list files

## Configuration Options

### Local Storage Directory

By default, downloaded files are stored in a temporary directory. You can customize this:

```python
import os

# Set custom download directory
os.environ["LOCAL_STORAGE_DIR"] = "/path/to/your/download/directory"
```

### Supported File Types

The Google Drive source automatically handles various file types:

- **Google Workspace files**: Automatically exported to common formats (Docs → DOCX, Sheets → XLSX, etc.)
- **Regular files**: Downloaded as-is
- **Large files**: Handled with resumable downloads for reliability

!!! warning "File Size Limitations"
    Google Workspace files (Google Docs, Sheets, Slides, etc.) have a **9MB export limit** when converting to standard formats (DOCX, XLSX, PPTX). Files larger than this limit may fail to download. For large documents, consider:

    - Breaking them into smaller documents
    - Using Google's native format instead of exporting
    - Accessing them directly through the Google Workspace APIs

## Best Practices

1. **Security**: Store service account keys securely and rotate them regularly
2. **Permissions**: Use the principle of least privilege - only grant necessary permissions
3. **Error Handling**: Always implement proper error handling for network and API failures
4. **Rate Limiting**: Respect Google Drive API quotas and implement appropriate delays
5. **Monitoring**: Log operations for debugging and monitoring purposes
