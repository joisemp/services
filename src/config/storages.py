from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

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