# Certs4MikroTik

Automated SSL/TLS certificate management and deployment for MikroTik routers and Reolink cameras using Kubernetes, cert-manager, and external-dns.

## Overview

This project automates the process of:
1. Creating DNS records for your devices via external-dns
2. Requesting and managing SSL/TLS certificates via cert-manager and Let's Encrypt
3. Uploading certificates to devices:
   - **MikroTik routers** via RouterOS API (SSL or plain)
   - **Reolink cameras** via HTTP API

## Features

- ✅ **Automatic certificate management** - Uses cert-manager to automatically request and renew certificates
- ✅ **DNS automation** - Creates DNS records automatically via external-dns
- ✅ **Multi-device support** - Supports both MikroTik routers and Reolink cameras
- ✅ **SSL/TLS API support** - Connects via SSL (port 8729) with certificate verification disabled for MikroTik
- ✅ **Fallback to plain** - Falls back to plain API (port 8728) if SSL is unavailable for MikroTik
- ✅ **Kubernetes native** - Runs as a CronJob in your Kubernetes cluster
- ✅ **Multiple devices** - Manages certificates for multiple devices from a single configuration

## Prerequisites

- Kubernetes cluster
- cert-manager installed
- external-dns configured for your DNS provider
- Let's Encrypt Issuer or ClusterIssuer configured
- **For MikroTik:** Routers with API access enabled (SSL recommended)
- **For Reolink:** Cameras with admin credentials

## Installation

> **Note:** This package currently depends on a forked version of `reolink-aio` that includes certificate upload support. Once [PR #145](https://github.com/starkillerOG/reolink_aio/pull/145) is merged upstream, the package will be published to PyPI.

### Install from GitHub (Current)

```bash
# Install with forked reolink-aio dependency
pip install git+https://github.com/mabels/certs4mikrotik.git@main
```

### Install from PyPI (After upstream PR is merged)

```bash
pip install certs4mikrotik
```

### 2. Configure your devices

Edit `k8s/certs2mikrotik-config.yaml` to include your devices (see `k8s/certs2mikrotik-config.example.yaml`):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: certs4mikrotik-config
  namespace: default
data:
  certs4mikrotik.json: |
    {
      "devices": [
        {
          "name": "office-router",
          "device_type": "mikrotik",
          "host": "192.168.1.1",
          "port": "8728",
          "ssl_port": "8729",
          "username": "admin",
          "cert_secret": "office-router-tls",
          "password_secret": "office-router-credentials",
          "cert_name": "office-router-cert"
        },
        {
          "name": "front-door-camera",
          "device_type": "reolink",
          "host": "192.168.1.100",
          "https_port": "443",
          "username": "admin",
          "cert_secret": "front-door-camera-tls",
          "password_secret": "front-door-camera-credentials",
          "cert_name": "front-door-camera-cert"
        }
      ]
    }
```

### 3. Create device credentials

For each device, create a Kubernetes secret with the admin password:

```bash
# MikroTik router
kubectl create secret generic office-router-credentials \
  --from-literal=password='your-router-password'

# Reolink camera
kubectl create secret generic front-door-camera-credentials \
  --from-literal=password='your-camera-password'
```

### 4. Configure the Let's Encrypt Issuer or ClusterIssuer

**Option A:** Namespace-scoped Issuer (default):
```bash
kubectl apply -f k8s/issuer-example.yaml
```

**Option B:** Cluster-wide ClusterIssuer:
```bash
kubectl apply -f k8s/clusterissuer-example.yaml
kubectl apply -f k8s/cluster-role-issuers.yaml
kubectl apply -f k8s/clusterrolebinding-issuers.yaml
```

Update the YAML file with your email address and DNS provider credentials before applying.

### 5. Deploy the application

```bash
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/routers-config.yaml
kubectl apply -f k8s/cronjob.yaml
```

## Configuration

### Device Configuration

Each device entry in the configuration requires:

#### Common Fields (All Devices)

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Device identifier (used for DNS) | `office-router` |
| `device_type` | Device type: `mikrotik` or `reolink` | `mikrotik` |
| `host` | Device IP address | `192.168.1.1` |
| `username` | API/admin username | `admin` |
| `cert_secret` | Kubernetes secret name for TLS cert | `office-router-tls` |
| `password_secret` | Kubernetes secret name for password | `office-router-credentials` |
| `cert_name` | Kubernetes Certificate resource name | `office-router-cert` |

#### MikroTik-Specific Fields

| Field | Description | Example |
|-------|-------------|---------|
| `port` | Plain API port | `8728` |
| `ssl_port` | SSL API port (optional, default: 8729) | `8729` |

#### Reolink-Specific Fields

| Field | Description | Example |
|-------|-------------|---------|
| `https_port` | HTTPS port (optional, default: 443) | `443` |
| `relogin_delay` | Seconds to wait for re-login after cert clear (optional, default: 5.0) | `5.0` |

### CronJob Schedule

The default schedule runs at 2 AM on Sundays and Wednesdays:

```yaml
schedule: 0 2 * * 0,3
```

Modify this in `k8s/cronjob.yaml` to fit your needs.

## How It Works

1. **CronJob triggers** on the scheduled time
2. **DNS records created/updated** via DNSEndpoint resources
3. **Certificates requested** via cert-manager Certificate resources
4. **Script connects** to each router:
   - First tries SSL connection (port 8729) with cert verification disabled
   - Falls back to plain connection (port 8728) if SSL fails
5. **Certificates uploaded** to the router via API
6. **Certificates imported** and marked as trusted on the router

## Device Setup

### MikroTik Router Setup

#### Enable API Access

For SSL API (recommended):
```
/ip service
set api-ssl disabled=no
```

For plain API (less secure):
```
/ip service
set api disabled=no
```

#### Create API User (Optional)

For better security, create a dedicated API user:
```
/user group add name=api-users policy=api,read,write,test
/user add name=certbot group=api-users password=strong-password
```

### Reolink Camera Setup

#### Requirements

- Camera must be accessible via HTTPS (port 443 by default)
- Admin credentials required
- **Important:** Cameras only support RSA certificates (not EC/ECDSA)

#### Certificate Limitations

- Some models (e.g., E1 Pro) may require a reboot after certificate upload to activate
- The certificate is stored with the name "server" internally on the device
- Verify your Let's Encrypt Issuer uses RSA key algorithm:
  ```yaml
  spec:
    acme:
      privateKeySecretRef:
        name: letsencrypt-prod
      solvers:
      - http01:
          ingress:
            class: nginx
  ```

#### Testing

After certificate upload, test HTTPS access:
```bash
# Should show the new certificate
openssl s_client -connect camera-ip:443 -showcerts
```

## Usage

### Using Issuer vs ClusterIssuer

By default, the script uses namespace-scoped Issuers. To use a ClusterIssuer, pass the `--issuer-kind` flag:

```bash
# Using default Issuer
cert2mikrotik --config devices.json --issuer letsencrypt-prod

# Using ClusterIssuer
cert2mikrotik --config devices.json --issuer letsencrypt-prod --issuer-kind ClusterIssuer
```

### Command-line Options

```
--config            Path to devices config JSON file (required)
--namespace         Kubernetes namespace (default: default)
--issuer            cert-manager Issuer name (default: letsencrypt-prod)
--issuer-kind       Issuer kind: Issuer or ClusterIssuer (default: Issuer)
--domain-suffix     Domain suffix for DNS names (default: .adviser.com)
--ensure-resources  Create/update Certificate and DNSEndpoint resources (default: true)
--skip-resources    Skip creating/updating Certificate and DNSEndpoint resources
--verbose, -v       Enable verbose logging
```

## Manual Testing

You can manually trigger a job run:

```bash
kubectl create job --from=cronjob/mikrotik-cert-upload manual-test
kubectl logs -f job/manual-test
```

## Troubleshooting

### Connection Issues

Check if the API port is accessible:
```bash
# Test SSL API
openssl s_client -connect <router-ip>:8729

# Test plain API
telnet <router-ip> 8728
```

### View Job Logs

```bash
# List recent jobs
kubectl get jobs

# View logs
kubectl logs job/<job-name>
```

### Certificate Issues

Check cert-manager certificate status:
```bash
kubectl get certificates
kubectl describe certificate <cert-name>
```

## Security Considerations

1. **Use SSL API** - Always prefer SSL API (port 8729) over plain API (port 8728)
2. **Restrict API access** - Use firewall rules to limit API access to the Kubernetes cluster
3. **Use strong passwords** - Store router passwords securely in Kubernetes secrets
4. **Certificate verification** - The script disables cert verification for compatibility; consider using proper CA-signed certificates for production
5. **RBAC** - The service account has minimal permissions required for operation

## License

Apache License 2.0 - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

This project was developed with the assistance of Claude Code, an AI-powered coding assistant by Anthropic.

## Author

Created for automated MikroTik certificate management in Kubernetes environments.


**Author:** Meno Abels
