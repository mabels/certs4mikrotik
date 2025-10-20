# Certs4MikroTik - Project Information

## Repository Details

**Location:** `~/Software/certs4mikrotik`  
**Git Status:** Initialized with 3 commits  
**License:** MIT  
**Language:** Python 3.11  

## What This Project Does

Automates the complete lifecycle of SSL/TLS certificates for MikroTik routers:

1. **DNS Management** - Automatically creates DNS A records via external-dns
2. **Certificate Issuance** - Requests and renews Let's Encrypt certificates via cert-manager
3. **Certificate Deployment** - Uploads certificates to MikroTik routers via API
4. **Scheduled Updates** - Runs automatically via Kubernetes CronJob

## Key Innovation

**SSL API with Certificate Verification Disabled**
- Connects to MikroTik's SSL API (port 8729) by default
- Disables certificate verification to work with self-signed certs
- Falls back to plain API (port 8728) if SSL fails
- Maintains encryption while ensuring compatibility

## Repository Structure

```
certs4mikrotik/
├── Documentation
│   ├── README.md           - Main documentation
│   ├── QUICKSTART.md       - 5-minute setup guide
│   ├── INSTALL.md          - Detailed installation
│   ├── ARCHITECTURE.md     - System design and flow
│   └── PROJECT_INFO.md     - This file
│
├── Source Code
│   └── src/
│       └── upload-router-complete.py   - Main Python script
│
├── Kubernetes Manifests
│   └── k8s/
│       ├── cronjob.yaml               - Scheduled job
│       ├── upload-script.yaml         - Script ConfigMap
│       ├── routers-config.yaml        - Router configuration
│       ├── service-account.yaml       - RBAC service account
│       ├── role-*.yaml               - RBAC roles
│       ├── rolebinding-*.yaml        - RBAC bindings
│       └── issuer-example.yaml       - Let's Encrypt config
│
├── Examples
│   └── examples/
│       ├── routers-config-example.yaml    - Router config template
│       └── router-password-example.yaml   - Password secret template
│
└── Configuration
    ├── requirements.txt    - Python dependencies
    ├── .gitignore         - Git ignore rules
    └── LICENSE            - MIT license
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | Kubernetes | Job scheduling and secret management |
| Certificate Management | cert-manager | Automated Let's Encrypt certificates |
| DNS Management | external-dns | Automatic DNS record creation |
| API Library | librouteros | MikroTik RouterOS API client |
| Runtime | Python 3.11 | Script execution environment |
| Container Image | python:3.11-slim | Minimal Python container |

## Current Deployment

**Your Production Setup:**
- Namespace: `default`
- Schedule: `0 2 * * 0,3` (2 AM on Sundays and Wednesdays)
- Routers: 2 (mam-hh-gwx86, mam-hh-gwax3)
- Domain: `.adviser.com`
- Issuer: `letsencrypt-prod`

## Making It Public

To share this repository publicly on GitHub:

```bash
cd ~/Software/certs4mikrotik

# Create repository on GitHub, then:
git remote add origin https://github.com/yourusername/certs4mikrotik.git
git branch -M main
git push -u origin main
```

Or use the GitHub CLI:
```bash
gh repo create certs4mikrotik --public --source=. --push
```

## Files NOT in Repository

For security, these are excluded via .gitignore:
- `*-credentials.yaml` - Router passwords
- `*-secret.yaml` - Any secrets
- `secrets/` directory - Secret storage

## Recent Changes

### Latest Update (Current)
- **Added SSL support** with certificate verification disabled
- **Added fallback** to plain API for compatibility
- **Fixed connection issues** caused by disabled plain API

### Initial Implementation
- Kubernetes CronJob for scheduled execution
- Integration with cert-manager and external-dns
- Multi-router configuration support

## Maintenance

**Updating Router Configuration:**
1. Edit `k8s/routers-config.yaml`
2. Apply: `kubectl apply -f k8s/routers-config.yaml`
3. Next CronJob run will use new config

**Updating the Script:**
1. Edit `src/upload-router-complete.py`
2. Update ConfigMap: `kubectl create configmap upload-router-complete-script --from-file=upload-router-complete.py=src/upload-router-complete.py -o yaml --dry-run=client | kubectl apply -f -`
3. Next CronJob run will use new script

**Manual Execution:**
```bash
kubectl create job --from=cronjob/mikrotik-cert-upload manual-test-1760939091
```

## Support & Contribution

This is a personal/internal project that has been organized for public sharing. 

**To contribute:**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Author & License

Created for automated certificate management in Kubernetes environments.  
By Meno Abels

Developed with the assistance of Claude Code.

Licensed under Apache 2.0 - free to use, modify, and distribute.

---

**Project Status:** ✅ Production Ready  
**Last Updated:** October 2025  
**Version:** 1.0.0  
