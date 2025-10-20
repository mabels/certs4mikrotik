# Certs4MikroTik

Automated SSL/TLS certificate management and deployment for MikroTik routers using Kubernetes, cert-manager, and external-dns.

## Overview

This project automates the process of:
1. Creating DNS records for your MikroTik routers via external-dns
2. Requesting and managing SSL/TLS certificates via cert-manager and Let's Encrypt
3. Uploading certificates to MikroTik routers via their API (SSL or plain)

## Features

- ✅ **Automatic certificate management** - Uses cert-manager to automatically request and renew certificates
- ✅ **DNS automation** - Creates DNS records automatically via external-dns
- ✅ **SSL/TLS API support** - Connects via SSL (port 8729) with certificate verification disabled
- ✅ **Fallback to plain** - Falls back to plain API (port 8728) if SSL is unavailable
- ✅ **Kubernetes native** - Runs as a CronJob in your Kubernetes cluster
- ✅ **Multiple routers** - Manages certificates for multiple routers from a single configuration

## Prerequisites

- Kubernetes cluster
- cert-manager installed
- external-dns configured for your DNS provider
- Let's Encrypt issuer configured
- MikroTik routers with API access enabled (SSL recommended)

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd certs4mikrotik
```

### 2. Configure your routers

Edit `k8s/routers-config.yaml` to include your routers:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mikrotik-routers-config
  namespace: default
data:
  routers.json: |
    {
      routers: [
        {
          name: router1,
          host: 192.168.1.1,
          port: 8728,
          username: admin,
          cert_secret: router1-tls,
          password_secret: router1-credentials,
          cert_name: router1-cert
        }
      ]
    }
```

### 3. Create router credentials

For each router, create a Kubernetes secret with the admin password:

```bash
kubectl create secret generic router1-credentials \
  --from-literal=password='your-router-password'
```

### 4. Configure the Let's Encrypt issuer

Update `k8s/issuer.yaml` with your email address and deploy it:

```bash
kubectl apply -f k8s/issuer.yaml
```

### 5. Deploy the application

```bash
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/routers-config.yaml
kubectl apply -f k8s/upload-script.yaml
kubectl apply -f k8s/cronjob.yaml
```

## Configuration

### Router Configuration

Each router entry in the configuration requires:

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Router identifier (used for DNS) | `router1` |
| `host` | Router IP address | `192.168.1.1` |
| `port` | Plain API port | `8728` |
| `ssl_port` | SSL API port (optional, default: 8729) | `8729` |
| `username` | API username | `admin` |
| `cert_secret` | Kubernetes secret name for TLS cert | `router1-tls` |
| `password_secret` | Kubernetes secret name for password | `router1-credentials` |
| `cert_name` | Certificate name on the router | `router1-cert` |

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

## MikroTik Router Setup

### Enable API Access

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

### Create API User (Optional)

For better security, create a dedicated API user:
```
/user group add name=api-users policy=api,read,write,test
/user add name=certbot group=api-users password=strong-password
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
