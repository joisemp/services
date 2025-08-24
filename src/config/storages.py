from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class StaticStorage(S3Boto3Storage):
    """
    StaticStorage is a custom storage class that inherits from S3Boto3Storage.
    It is used to manage static files in an S3 bucket.

    Attributes:
        location (str): The folder name in the S3 bucket where static files are stored.
        default_acl (str): The default access control list for the files, set to "public-read".
    """
    location = "static"
    default_acl = "public-read"

class MediaStorage(S3Boto3Storage):
    location = "media"
    default_acl = "private"

    def get_object_parameters(self, name):
        """
        Set public-read ACL for specific file paths or types.
        """
        params = super().get_object_parameters(name)

        # Make specific files public (e.g., images in `public/` folder)
        if name.startswith("media/public/"):
            params["ACL"] = "public-read"

        return params
    
    def _save(self, name, content):
        """
        Override the _save method to add logging and error handling
        """
        try:
            logger.info(f"Attempting to save file: {name}")
            saved_name = super()._save(name, content)
            logger.info(f"Successfully saved file: {saved_name}")
            return saved_name
        except Exception as e:
            logger.error(f"Failed to save file {name}: {str(e)}")
            raise e
    
    def exists(self, name):
        """
        Override exists method with logging
        """
        try:
            exists = super().exists(name)
            logger.debug(f"File exists check for {name}: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking if file exists {name}: {str(e)}")
            return False