"""Reolink camera certificate uploader using reolink-aio library"""
import logging
from typing import Optional
from .base import DeviceUploader

try:
    from reolink_aio.api import Host
    REOLINK_AIO_AVAILABLE = True
except ImportError:
    REOLINK_AIO_AVAILABLE = False

logger = logging.getLogger(__name__)

class ReolinkUploader(DeviceUploader):
    """Certificate uploader for Reolink cameras using reolink-aio library"""

    def __init__(self, host: str, username: str = "admin", password: str = "", port: int = 443, relogin_delay: float = 5.0, **kwargs):
        """
        Initialize Reolink uploader

        Args:
            host: Camera IP address or hostname
            username: Camera username
            password: Camera password
            port: HTTPS port (default 443)
            relogin_delay: Seconds to wait before re-login after clearing certs (default 5.0)
            **kwargs: Additional parameters
        """
        super().__init__(host, username, password, **kwargs)
        self.port = port
        self.relogin_delay = relogin_delay
        self.reolink_host = None

    async def upload_certificate(self, cert_content: str, key_content: str, cert_name: str = "server") -> bool:
        """
        Upload certificate and key to Reolink camera

        This uses the reolink-aio library's certificate upload functionality,
        which handles the complete workflow:
        1. Login to get authentication token
        2. Clear existing certificates
        3. Re-login (required after clearing)
        4. Import new certificate
        5. Wait for processing
        6. Logout

        Args:
            cert_content: PEM-encoded certificate content
            key_content: PEM-encoded private key content
            cert_name: Name to use for the certificate on the camera

        Returns:
            True if upload succeeded, False otherwise
        """
        if not REOLINK_AIO_AVAILABLE:
            logger.error("reolink-aio library not available")
            return False

        try:
            # Initialize the Host object (represents a camera or NVR)
            logger.info(f"Connecting to Reolink camera at {self.host}:{self.port}")
            self.reolink_host = Host(
                host=self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                protocol="https"
            )

            # Login and get host data (initializes connection)
            logger.info("Logging in and retrieving camera information...")
            await self.reolink_host.get_host_data()

            logger.info(f"Connected to {self.reolink_host.nvr_name} (model: {self.reolink_host.model})")

            # Upload certificate using the complete workflow
            logger.info(f"Uploading certificate to {self.reolink_host.nvr_name}...")
            success = await self.reolink_host.upload_certificate(
                cert_content=cert_content,
                key_content=key_content,
                cert_name=cert_name,
                relogin_delay=self.relogin_delay
            )

            if success:
                logger.info(f"Successfully uploaded certificate to {self.reolink_host.nvr_name}")
                logger.warning("Note: Some Reolink models may require a reboot to activate the certificate")
            else:
                logger.error(f"Failed to upload certificate to {self.reolink_host.nvr_name}")

            return success

        except Exception as e:
            logger.error(f"Failed to upload certificate to Reolink camera {self.host}: {e}")
            return False
        finally:
            # Always try to logout
            if self.reolink_host:
                try:
                    await self.reolink_host.logout()
                    logger.info(f"Logged out from {self.host}")
                except Exception as e:
                    logger.warning(f"Error during logout from {self.host}: {e}")
