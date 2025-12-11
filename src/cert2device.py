#!/usr/bin/env python3
import argparse
import logging
import asyncio
import os
import sys
import json
import base64
import ssl
from typing import Optional

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False

# Import uploaders
from certs4devices.uploaders import MikroTikUploader, ReolinkUploader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Legacy class for backwards compatibility (now uses MikroTikUploader from uploaders module)
class MikroTikCertUploader:
    def __init__(self, host: str, username: str = "admin", password: str = "", port: int = 8728, ssl_port: int = 8729):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.ssl_port = ssl_port
        self.api_connection = None

    def connect_api(self) -> bool:
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
        if self.api_connection:
            try:
                self.api_connection.close()
                logger.info("Disconnected from RouterOS API")
            except Exception as e:
                logger.warning(f"Error disconnecting from API: {e}")

    async def certificate_import(self, filename):
        try:
            response_generator = self.api_connection.path('certificate')('import', **{
                'file-name': filename,
                'trusted': 'yes'
            })
            for response in response_generator:
                logger.debug(f"Import response: {response}")
        except Exception as e:
            logger.error(f"Error importing certificate: {e}")

    async def upload_via_api(self, cert_content: str, key_content: str, cert_name: str = "uploaded-cert") -> bool:
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

class K8sResourceManager:
    def __init__(self, namespace: str = "default"):
        if not K8S_AVAILABLE:
            raise Exception("kubernetes python client not available")
        
        # Load in-cluster config
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration")
        except:
            # Fallback to kubeconfig for local testing
            config.load_kube_config()
            logger.info("Loaded kubeconfig configuration")
        
        self.v1 = client.CoreV1Api()
        self.custom_api = client.CustomObjectsApi()
        self.namespace = namespace
    
    def get_secret(self, secret_name: str) -> dict:
        """Fetch a secret from Kubernetes"""
        try:
            logger.info(f"Fetching secret: {secret_name} from namespace: {self.namespace}")
            secret = self.v1.read_namespaced_secret(secret_name, self.namespace)
            return secret.data
        except Exception as e:
            logger.error(f"Failed to fetch secret {secret_name}: {e}")
            raise
    
    def get_tls_cert(self, secret_name: str) -> tuple[str, str]:
        """Fetch TLS certificate and key from a Kubernetes secret"""
        secret_data = self.get_secret(secret_name)
        
        # Decode base64 encoded cert and key
        cert_b64 = secret_data.get('tls.crt')
        key_b64 = secret_data.get('tls.key')
        
        if not cert_b64 or not key_b64:
            raise Exception(f"Secret {secret_name} doesn't contain tls.crt or tls.key")
        
        cert = base64.b64decode(cert_b64).decode('utf-8')
        key = base64.b64decode(key_b64).decode('utf-8')
        
        return cert, key
    
    def get_password(self, secret_name: str, key: str = 'password') -> str:
        """Fetch password from a Kubernetes secret"""
        secret_data = self.get_secret(secret_name)
        
        password_b64 = secret_data.get(key)
        if not password_b64:
            raise Exception(f"Secret {secret_name} doesn't contain key: {key}")
        
        password = base64.b64decode(password_b64).decode('utf-8')
        return password
    
    def ensure_certificate(self, router_config: dict, issuer_name: str = "letsencrypt-prod", issuer_kind: str = "Issuer", domain_suffix: str = ".adviser.com") -> bool:
        """Create or update cert-manager Certificate resource"""
        router_name = router_config['name']
        cert_name = router_config['cert_name']
        secret_name = router_config['cert_secret']
        dns_name = f"{router_name}{domain_suffix}"

        certificate = {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Certificate",
            "metadata": {
                "name": cert_name,
                "namespace": self.namespace
            },
            "spec": {
                "secretName": secret_name,
                "issuerRef": {
                    "group": "cert-manager.io",
                    "kind": issuer_kind,
                    "name": issuer_name
                },
                "dnsNames": [dns_name]
            }
        }
        
        try:
            # Try to get existing certificate
            try:
                existing = self.custom_api.get_namespaced_custom_object(
                    group="cert-manager.io",
                    version="v1",
                    namespace=self.namespace,
                    plural="certificates",
                    name=cert_name
                )
                logger.info(f"Certificate {cert_name} already exists, updating...")
                
                # Update existing certificate
                self.custom_api.patch_namespaced_custom_object(
                    group="cert-manager.io",
                    version="v1",
                    namespace=self.namespace,
                    plural="certificates",
                    name=cert_name,
                    body=certificate
                )
                logger.info(f"✅ Updated Certificate: {cert_name}")
                return True
                
            except ApiException as e:
                if e.status == 404:
                    # Certificate doesn't exist, create it
                    logger.info(f"Creating new Certificate: {cert_name}")
                    self.custom_api.create_namespaced_custom_object(
                        group="cert-manager.io",
                        version="v1",
                        namespace=self.namespace,
                        plural="certificates",
                        body=certificate
                    )
                    logger.info(f"✅ Created Certificate: {cert_name}")
                    return True
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"Failed to ensure Certificate {cert_name}: {e}")
            return False
    
    def ensure_dns_endpoint(self, router_config: dict, domain_suffix: str = ".adviser.com") -> bool:
        """Create or update external-dns DNSEndpoint resource"""
        router_name = router_config['name']
        host = router_config['host']
        dns_endpoint_name = f"{router_name}-dns"
        dns_name = f"{router_name}{domain_suffix}"
        
        dns_endpoint = {
            "apiVersion": "externaldns.k8s.io/v1alpha1",
            "kind": "DNSEndpoint",
            "metadata": {
                "name": dns_endpoint_name,
                "namespace": self.namespace
            },
            "spec": {
                "endpoints": [
                    {
                        "dnsName": dns_name,
                        "recordType": "A",
                        "targets": [host]
                    }
                ]
            }
        }
        
        try:
            # Try to get existing DNSEndpoint
            try:
                existing = self.custom_api.get_namespaced_custom_object(
                    group="externaldns.k8s.io",
                    version="v1alpha1",
                    namespace=self.namespace,
                    plural="dnsendpoints",
                    name=dns_endpoint_name
                )
                logger.info(f"DNSEndpoint {dns_endpoint_name} already exists, updating...")
                
                # Update existing DNSEndpoint
                self.custom_api.patch_namespaced_custom_object(
                    group="externaldns.k8s.io",
                    version="v1alpha1",
                    namespace=self.namespace,
                    plural="dnsendpoints",
                    name=dns_endpoint_name,
                    body=dns_endpoint
                )
                logger.info(f"✅ Updated DNSEndpoint: {dns_endpoint_name}")
                return True
                
            except ApiException as e:
                if e.status == 404:
                    # DNSEndpoint doesn't exist, create it
                    logger.info(f"Creating new DNSEndpoint: {dns_endpoint_name}")
                    self.custom_api.create_namespaced_custom_object(
                        group="externaldns.k8s.io",
                        version="v1alpha1",
                        namespace=self.namespace,
                        plural="dnsendpoints",
                        body=dns_endpoint
                    )
                    logger.info(f"✅ Created DNSEndpoint: {dns_endpoint_name}")
                    return True
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"Failed to ensure DNSEndpoint {dns_endpoint_name}: {e}")
            return False

async def process_device(device_config: dict, k8s_manager: K8sResourceManager, ensure_resources: bool = True, issuer_name: str = "letsencrypt-prod", issuer_kind: str = "Issuer", domain_suffix: str = ".adviser.com") -> bool:
    """Process a single device (router/camera) from configuration"""
    device_name = device_config['name']
    device_type = device_config['device_type']

    print(f"\n{'='*60}")
    print(f"Processing: {device_name}")
    print(f"Device Type: {device_type}")
    print(f"Host: {device_config['host']}")
    print(f"Certificate Secret: {device_config['cert_secret']}")
    print(f"Password Secret: {device_config['password_secret']}")
    print(f"{'='*60}\n")

    try:
        # Step 1: Ensure Kubernetes resources exist
        if ensure_resources:
            logger.info("Ensuring Kubernetes resources...")
            cert_ok = k8s_manager.ensure_certificate(device_config, issuer_name, issuer_kind, domain_suffix)
            dns_ok = k8s_manager.ensure_dns_endpoint(device_config, domain_suffix)

            if not cert_ok or not dns_ok:
                logger.warning("Some resources failed to create/update, but continuing...")

        # Step 2: Fetch password from Kubernetes secret
        logger.info(f"Fetching password from secret: {device_config['password_secret']}")
        password = k8s_manager.get_password(device_config['password_secret'])

        # Step 3: Fetch TLS certificate from Kubernetes secret
        logger.info(f"Fetching TLS certificate from secret: {device_config['cert_secret']}")
        cert_content, key_content = k8s_manager.get_tls_cert(device_config['cert_secret'])

        # Step 4: Create appropriate uploader based on device type
        if device_type.lower() == 'mikrotik':
            ssl_port = int(device_config.get('ssl_port', 8729))
            port = int(device_config.get('port', 8728))
            uploader = MikroTikUploader(
                host=device_config['host'],
                username=device_config['username'],
                password=password,
                port=port,
                ssl_port=ssl_port
            )
        elif device_type.lower() == 'reolink':
            uploader = ReolinkUploader(
                host=device_config['host'],
                username=device_config['username'],
                password=password,
                port=int(device_config.get('https_port', 443)),
                relogin_delay=float(device_config.get('relogin_delay', 5.0))
            )
        else:
            logger.error(f"Unsupported device type: {device_type}")
            print(f"❌ Unsupported device type: {device_type}\n")
            return False

        # Step 5: Upload certificate to device
        # For Reolink devices, always use "server" as the device cert name
        # For other devices, use the configured cert_name
        device_cert_name = "server" if device_type.lower() == 'reolink' else device_config['cert_name']
        success = await uploader.upload_certificate(
            cert_content,
            key_content,
            device_cert_name
        )

        if success:
            print(f"✅ Successfully uploaded certificate to {device_name}\n")
        else:
            print(f"❌ Failed to upload certificate to {device_name}\n")

        return success
    except Exception as e:
        logger.error(f"Failed to process {device_type} device {device_name}: {e}")
        print(f"❌ Failed to process {device_name}: {e}\n")
        return False

async def main():
    parser = argparse.ArgumentParser(description='Upload SSL certificates to network devices (routers/cameras)')
    parser.add_argument('--config', required=True, help='Path to devices config JSON file')
    parser.add_argument('--namespace', default='default', help='Kubernetes namespace')
    parser.add_argument('--ensure-resources', action='store_true', default=True, help='Create/update Certificate and DNSEndpoint resources')
    parser.add_argument('--skip-resources', action='store_true', help='Skip creating/updating Certificate and DNSEndpoint resources')
    parser.add_argument('--issuer', default='letsencrypt-prod', help='cert-manager Issuer name')
    parser.add_argument('--issuer-kind', default='Issuer', choices=['Issuer', 'ClusterIssuer'], help='cert-manager Issuer kind (Issuer or ClusterIssuer)')
    parser.add_argument('--domain-suffix', default='.adviser.com', help='Domain suffix for DNS names')
    parser.add_argument('--verbose', '-v', action='store_true')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if kubernetes client is available
    if not K8S_AVAILABLE:
        logger.error("kubernetes python client not available. Install with: pip install kubernetes")
        sys.exit(1)

    # Load device configuration
    try:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        sys.exit(1)

    devices = config_data.get('devices', [])

    if not devices:
        logger.error("No devices found in configuration")
        sys.exit(1)

    # Initialize Kubernetes resource manager
    try:
        k8s_manager = K8sResourceManager(namespace=args.namespace)
    except Exception as e:
        logger.error(f"Failed to initialize Kubernetes client: {e}")
        sys.exit(1)

    ensure_resources = args.ensure_resources and not args.skip_resources

    print(f"\n{'='*60}")
    print(f"Starting certificate upload for {len(devices)} device(s)")
    print(f"Kubernetes namespace: {args.namespace}")
    print(f"Issuer: {args.issuer}")
    print(f"Issuer kind: {args.issuer_kind}")
    print(f"Domain suffix: {args.domain_suffix}")
    print(f"Auto-create resources: {ensure_resources}")
    print(f"{'='*60}\n")

    # Process each device
    results = []
    for device in devices:
        success = await process_device(
            device,
            k8s_manager,
            ensure_resources=ensure_resources,
            issuer_name=args.issuer,
            issuer_kind=args.issuer_kind,
            domain_suffix=args.domain_suffix
        )
        results.append((device['name'], success))

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for device_name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{device_name}: {status}")

    print(f"{'='*60}\n")

    # Exit with error if any failed
    if not all(success for _, success in results):
        sys.exit(1)

    logger.info("All certificate uploads completed successfully!")

def cli_main():
    """Entry point for the CLI command"""
    asyncio.run(main())

if __name__ == '__main__':
    cli_main()
