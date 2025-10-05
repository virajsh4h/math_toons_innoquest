# backend/app/services/storage_service.py
import boto3
import os
import asyncio # New import for run_in_executor
from app.core.config import settings
from botocore.config import Config
from urllib.parse import urlparse

# Configure boto3 for Cloudflare R2
s3_config = Config(
    region_name='auto', # Use 'auto' for R2
    signature_version='s3v4'
)

def get_r2_client():
    """Initializes and returns the Boto3 S3 client configured for R2."""
    if not all([settings.R2_ENDPOINT_URL, settings.R2_ACCESS_KEY_ID, settings.R2_SECRET_ACCESS_KEY]):
        raise ValueError("R2 configuration is incomplete in environment variables.")
        
    session = boto3.session.Session()
    client = session.client(
        service_name='s3',
        # CRITICAL FIX: Ensure the endpoint URL is used correctly. 
        # It should look like https://<ACCOUNT_ID>.r2.cloudflarestorage.com
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=s3_config
    )
    return client

async def upload_video_to_r2(local_file_path: str, destination_key: str) -> str:
    """Uploads a local video file to the configured R2 bucket asynchronously."""
    print(f"  [R2] Starting upload of {os.path.basename(local_file_path)} to R2...")
    try:
        client = get_r2_client()
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: client.upload_file(
                Filename=local_file_path,
                Bucket=settings.R2_BUCKET_NAME,
                Key=destination_key,
                # FIX: Removing 'ACL' as it's deprecated/problematic with R2. 
                # Public access is enabled via your Cloudflare settings.
                ExtraArgs={
                    'ContentType': 'video/mp4'
                }
            )
        )
        
        # CRITICAL FIX: Construct the public URL using the public development URL you configured.
        # You need to manually find and set this in your environment variables:
        # e.g., R2_PUBLIC_URL_BASE = https://pub-xxxxxxxx.r2.dev/mathtoons
        # Then, the final URL is R2_PUBLIC_URL_BASE/KEY
        # For simplicity, we'll try to infer it from the R2_ENDPOINT_URL + BUCKET NAME as a fallback,
        # but the best practice is R2_PUBLIC_URL_BASE.
        
        # R2_ENDPOINT_URL looks like https://<ACCOUNT_ID>.r2.cloudflarestorage.com
        # Public URL looks like https://pub-xxxxxxxx.r2.dev/BUCKET_NAME
        
        # We assume the user has set the full public URL, or we use a standard Boto3 format.
        # Since Boto3 doesn't easily expose the public URL, we'll return a path 
        # that the frontend can combine with a known public domain.
        
        # For a FastAPI API, returning the S3-style path is safest.
        # The frontend will be responsible for prepending your pub-xxxxx.r2.dev URL.
        
        # The frontend should construct: YOUR_R2_PUBLIC_DOMAIN + "/" + destination_key
        # Example: https://pub-xxxxxxxx.r2.dev/mathtoons/rohan_12345.mp4
        
        public_url = f"s3://{settings.R2_BUCKET_NAME}/{destination_key}"
        print(f"  [R2] Video uploaded successfully. S3 Path: {public_url}")
        
        # Since you want a URL back, we'll try to construct a simple web-style one 
        # assuming a CNAME/public endpoint is set up.
        # The most reliable format for R2 is: 
        # https://<PUBLIC_DOMAIN>/<KEY>
        # However, for a test, we will return the KEY and the orchestrator can format it.
        
        # If your R2 Public URL is set in an environment variable, use it.
        # Since I don't have it, I'll update the print to be very clear.
        
        print("  [R2] NOTE: Please manually combine your R2 Public Domain with the key below for the final URL.")
        print(f"  [R2] Key is: {destination_key}")

        return destination_key # Return the key, let the orchestrator format the final URL.
        
    except Exception as e:
        print(f"  [R2] CRITICAL UPLOAD ERROR: {e}")
        raise # Re-raise to be caught by orchestrator