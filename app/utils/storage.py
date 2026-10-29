import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


def allowed_file(filename):
    """Check if the filename has an allowed image extension."""
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'webp'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def upload_media_file(file_storage, folder_prefix='events'):
    """
    Upload a file either to Azure Blob Storage (if configured)
    or to the local uploads directory as a fallback.

    Returns the public URL / local URL path to be stored in the database.
    """
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_file(file_storage.filename):
        raise ValueError("File type not allowed. Please upload PNG, JPG, JPEG, WEBP, or GIF.")

    # Generate unique sanitized filename
    original_ext = file_storage.filename.rsplit('.', 1)[1].lower()
    safe_name = f"{folder_prefix}_{uuid.uuid4().hex[:12]}.{original_ext}"

    azure_conn_str = current_app.config.get('AZURE_STORAGE_CONNECTION_STRING')
    container_name = current_app.config.get('AZURE_STORAGE_CONTAINER_NAME', 'event-media')

    # 1. Try Azure Blob Storage if credentials provided
    if azure_conn_str and AZURE_AVAILABLE:
        try:
            blob_service_client = BlobServiceClient.from_connection_string(azure_conn_str)
            container_client = blob_service_client.get_container_client(container_name)
            
            # Ensure container exists
            try:
                container_client.create_container()
            except Exception:
                pass  # Container already exists

            blob_client = container_client.get_blob_client(safe_name)
            file_storage.seek(0)
            
            content_type = f"image/{original_ext if original_ext != 'jpg' else 'jpeg'}"
            content_settings = ContentSettings(content_type=content_type)
            
            blob_client.upload_blob(file_storage.read(), overwrite=True, content_settings=content_settings)
            return blob_client.url
        except Exception as e:
            current_app.logger.warning(f"Azure Blob upload failed ({e}). Falling back to local storage.")
            file_storage.seek(0)

    # 2. Local File System Fallback
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], folder_prefix)
    os.makedirs(upload_dir, exist_ok=True)
    destination_path = os.path.join(upload_dir, safe_name)
    
    file_storage.seek(0)
    file_storage.save(destination_path)
    
    # Return local web-accessible route
    return f"/uploads/{folder_prefix}/{safe_name}"
