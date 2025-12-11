"""MikroTik certificate uploader"""
import ssl
import logging
from typing import Optional
from .base import DeviceUploader

try:
    import librouteros
    from librouteros.login import plain, token
    ROUTEROS_AVAILABLE = True
except ImportError:
    ROUTEROS_AVAILABLE = False

logger = logging.getLogger(__name__)

class MikroTikUploader(DeviceUploader):
    """Certificate uploader for MikroTik routers"""

    def __init__(self, host: str, username: str = "admin", password: str = "", port: int = 8728, ssl_port: int = 8729, **kwargs):
        """
        Initialize MikroTik uploader

        Args:
            host: Router IP address or hostname
            username: RouterOS username
            password: RouterOS password
            port: Plain API port (default 8728)
            ssl_port: SSL API port (default 8729)
        """
        super().__init__(host, username, password, **kwargs)
        self.port = port
        self.ssl_port = ssl_port
        self.api_connection = None

    def connect_api(self) -> bool:
        """Connect to RouterOS API with SSL fallback to plain connection"""
        if not ROUTEROS_AVAILABLE:
            logger.error("librouteros not available")
            return False

        # Try SSL first (port 8729)
        try:
            logger.info(f"Attempting SSL connection to MikroTik API at {self.host}:{self.ssl_port}")

            # Create SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            self.api_connection = librouteros.connect(
                username=self.username,
                password=self.password,
                host=self.host,
                port=self.ssl_port,
                ssl_wrapper=ssl_context.wrap_socket,
                login_method=plain
            )
            logger.info("Successfully connected to RouterOS API via SSL")
            return True
        except Exception as e:
            logger.warning(f"SSL connection failed: {e}")
            logger.info(f"Attempting plain connection to MikroTik API at {self.host}:{self.port}")

            # Try plain connection (port 8728)
            try:
                self.api_connection = librouteros.connect(
                    username=self.username,
                    password=self.password,
                    host=self.host,
                    port=self.port
                )
                logger.info("Successfully connected to RouterOS API via plain connection")
                return True
            except Exception as e2:
                logger.error(f"Failed to connect to RouterOS API (both SSL and plain): SSL error: {e}, Plain error: {e2}")
                return False

    def disconnect_api(self):
        """Disconnect from RouterOS API"""
        if self.api_connection:
            try:
                self.api_connection.close()
                logger.info("Disconnected from RouterOS API")
            except Exception as e:
                logger.warning(f"Error disconnecting from API: {e}")

    async def certificate_import(self, filename):
        """Import certificate or key file into RouterOS"""
        try:
            response_generator = self.api_connection.path('certificate')('import', **{
                'file-name': filename,
                'trusted': 'yes'
            })
            for response in response_generator:
                logger.debug(f"Import response: {response}")
        except Exception as e:
            logger.error(f"Error importing certificate: {e}")

    async def upload_certificate(self, cert_content: str, key_content: str, cert_name: str = "uploaded-cert") -> bool:
        """
        Upload certificate and key to MikroTik router via API

        Args:
            cert_content: PEM-encoded certificate content
            key_content: PEM-encoded private key content
            cert_name: Name to use for the certificate on the router

        Returns:
            True if upload succeeded, False otherwise
        """
        if not self.connect_api():
            return False
        try:
            cert_filename = f"{cert_name}.crt"
            key_filename = f"{cert_name}.key"

            # Clean up existing files
            try:
                self.api_connection.path('file').remove(cert_filename)
                self.api_connection.path('file').remove(key_filename)
            except:
                pass

            # Upload files
            logger.info(f"Uploading certificate as {cert_filename}")
            self.api_connection.path('file').add(name=cert_filename, contents=cert_content)

            logger.info(f"Uploading private key as {key_filename}")
            self.api_connection.path('file').add(name=key_filename, contents=key_content)

            # Import certificate
            logger.info(f"Importing certificate {cert_name}")
            await self.certificate_import(cert_filename)
            await self.certificate_import(key_filename)

            logger.info(f"Successfully uploaded certificate {cert_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload certificate via API: {e}")
            return False
        finally:
            self.disconnect_api()
