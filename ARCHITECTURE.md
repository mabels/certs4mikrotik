# Architecture

## Overview

This project uses a combination of Kubernetes resources to automate certificate management for MikroTik routers.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           CronJob: mikrotik-cert-upload            │    │
│  │         (Runs on schedule: 0 2 * * 0,3)            │    │
│  └─────────────────────┬──────────────────────────────┘    │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────────┐    │
│  │              Python Upload Script                   │    │
│  │  (upload-router-complete-script ConfigMap)         │    │
│  │                                                     │    │
│  │  1. Ensure DNS records (DNSEndpoint)               │    │
│  │  2. Ensure Certificates (cert-manager)             │    │
│  │  3. Fetch router passwords from Secrets            │    │
│  │  4. Fetch TLS certs from Secrets                   │    │
│  │  5. Connect to routers (SSL then plain fallback)   │    │
│  │  6. Upload and import certificates                 │    │
│  └────┬────────────────────┬────────────────┬─────────┘    │
│       │                    │                │               │
│       ▼                    ▼                ▼               │
│  ┌─────────┐      ┌──────────────┐   ┌─────────┐         │
│  │ Secrets │      │ cert-manager │   │ external│         │
│  │         │      │              │   │  -dns   │         │
│  │ Router  │      │ Certificates │   │         │         │
│  │Password │      │              │   │ DNS     │         │
│  │  & TLS  │      │   (Let's     │   │Endpoint │         │
│  │  Certs  │      │   Encrypt)   │   │         │         │
│  └─────────┘      └──────────────┘   └─────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ MikroTik API (SSL/Plain)
                            ▼
            ┌───────────────────────────────┐
            │     MikroTik Routers          │
            │                               │
            │  • Router 1 (192.168.128.2)  │
            │  • Router 2 (192.168.128.3)  │
            │  • ...                        │
            └───────────────────────────────┘
```

## Data Flow

### 1. CronJob Trigger
- Runs on a schedule (default: 2 AM on Sun/Wed)
- Creates a Job pod that runs the upload script

### 2. Resource Creation/Update
- Script ensures DNSEndpoint resources exist for each router
- Script ensures Certificate resources exist for each router
- cert-manager automatically requests certificates from Let's Encrypt
- external-dns automatically creates DNS records

### 3. Certificate Fetching
- Script reads router passwords from Kubernetes Secrets
- Script reads TLS certificates from Kubernetes Secrets (populated by cert-manager)

### 4. Router Connection
- **Primary:** Try SSL connection on port 8729
  - Creates SSL context with verification disabled
  - Allows connection despite self-signed certificates
- **Fallback:** Try plain connection on port 8728
  - If SSL fails, falls back to unencrypted API

### 5. Certificate Upload
- Upload certificate file to router
- Upload private key file to router
- Import certificate using MikroTik API
- Import private key using MikroTik API

## Security Model

### RBAC Permissions
The service account has minimal permissions:
- **Secrets:** Read access to fetch passwords and TLS certificates
- **Custom Resources:** Create/Update/Patch for Certificate and DNSEndpoint
- **ConfigMaps:** Read access for router configuration

### Network Security
- Firewall rules should restrict API access to Kubernetes cluster
- SSL API (port 8729) is preferred over plain (port 8728)
- Certificate verification is disabled for compatibility with self-signed certs

### Secret Management
- Router passwords stored in Kubernetes Secrets
- TLS certificates managed by cert-manager
- No secrets committed to Git (see .gitignore)

## File Structure

```
certs4mikrotik/
├── README.md              # Main documentation
├── INSTALL.md             # Installation guide
├── ARCHITECTURE.md        # This file
├── LICENSE                # MIT license
├── .gitignore            # Git ignore rules
├── requirements.txt       # Python dependencies
├── src/                   # Source code
│   └── upload-router-complete.py
├── k8s/                   # Kubernetes manifests
│   ├── cronjob.yaml
│   ├── upload-script.yaml
│   ├── routers-config.yaml
│   ├── service-account.yaml
│   ├── role-*.yaml
│   ├── rolebinding-*.yaml
│   └── issuer-example.yaml
└── examples/              # Example configurations
    ├── routers-config-example.yaml
    └── router-credentials-secret.yaml
```

## Key Technologies

- **Kubernetes**: Container orchestration platform
- **cert-manager**: X.509 certificate management for Kubernetes
- **external-dns**: Synchronizes exposed Kubernetes Services and Ingresses with DNS providers
- **Let's Encrypt**: Free, automated, and open Certificate Authority
- **librouteros**: Python library for MikroTik RouterOS API
- **Python 3.11**: Scripting language for the uploader

## Design Decisions

### Why Kubernetes?
- Native secret management
- Scheduled job execution (CronJob)
- Easy integration with cert-manager and external-dns
- Scalable to many routers

### Why SSL with Disabled Verification?
- MikroTik routers often use self-signed certificates
- Full certificate verification would require CA setup
- Disabled verification allows connection while maintaining encryption
- Fallback to plain ensures compatibility

### Why ConfigMap for Router Config?
- Easy to update without rebuilding images
- Version controlled
- No sensitive data (passwords in Secrets)

## Extending

### Adding New Routers
1. Update `k8s/routers-config.yaml`
2. Create password Secret for new router
3. Apply changes: `kubectl apply -f k8s/routers-config.yaml`
4. Next CronJob run will include new router

### Changing Schedule
Edit `k8s/cronjob.yaml` and modify the `schedule` field.

### Custom DNS Provider
Update `k8s/issuer-example.yaml` with your DNS provider configuration.
See [cert-manager DNS01 docs](https://cert-manager.io/docs/configuration/acme/dns01/).
