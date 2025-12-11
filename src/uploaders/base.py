"""Base class for certificate uploaders"""
from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DeviceUploader(ABC):
    """Abstract base class for device certificate uploaders"""

    def __init__(self, host: str, username: str = "admin", password: str = "", **kwargs):
        """
        Initialize the uploader

        Args:
            host: Device IP address or hostname
            username: Authentication username
            password: Authentication password
            **kwargs: Additional device-specific parameters
        """
        self.host = host
        self.username = username
        self.password = password
        self.kwargs = kwargs
        logger.info(f"Initialized {self.__class__.__name__} for {host}")

    @abstractmethod
    async def upload_certificate(self, cert_content: str, key_content: str, cert_name: str = "uploaded-cert") -> bool:
        """
        Upload certificate and key to the device

        Args:
            cert_content: PEM-encoded certificate content
            key_content: PEM-encoded private key content
            cert_name: Name to use for the certificate on the device

        Returns:
            True if upload succeeded, False otherwise
        """
        pass

    @classmethod
    def get_device_type(cls) -> str:
        """Return the device type identifier for this uploader"""
        return cls.__name__.replace('Uploader', '').lower()
