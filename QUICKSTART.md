# Quick Start Guide

Get up and running with Certs4MikroTik in 10 minutes!

## Prerequisites Check

Make sure you have:
- [ ] Kubernetes cluster running
- [ ] kubectl configured
- [ ] cert-manager installed
- [ ] external-dns configured
- [ ] MikroTik router with API enabled

## 5-Minute Setup

### 1. Clone and Configure (2 min)

```bash
cd ~/Software
git clone /path/to/certs4mikrotik
cd certs4mikrotik

# Copy and edit router configuration
cp examples/routers-config-example.yaml k8s/routers-config.yaml
nano k8s/routers-config.yaml  # Edit with your router IPs and names
```

### 2. Create Secrets (1 min)

```bash
# For each router, create a password secret
kubectl create secret generic office-router-credentials \
  --from-literal=password='YourRouterPassword'
```

### 3. Deploy Everything (2 min)

```bash
# Deploy all resources at once
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/role-secret-reader.yaml
kubectl apply -f k8s/role-cert-manager.yaml
kubectl apply -f k8s/rolebinding-secrets.yaml
kubectl apply -f k8s/rolebinding-full.yaml
kubectl apply -f k8s/routers-config.yaml
kubectl apply -f k8s/upload-script.yaml
kubectl apply -f k8s/cronjob.yaml
```

Or use a single command:
```bash
kubectl apply -f k8s/
```

### 4. Test It! (5 min)

```bash
# Create a test job
kubectl create job --from=cronjob/mikrotik-cert-upload test-now

# Watch the logs
kubectl logs -f job/test-now

# Check certificates were created
kubectl get certificates
kubectl get dnsendpoints

# Verify on your router
# Log into RouterOS and run: /certificate print
```

## That's It!

Your routers will now automatically get:
- ✅ DNS records created
- ✅ Let's Encrypt certificates requested
- ✅ Certificates uploaded every Sunday and Wednesday at 2 AM

## Troubleshooting

**Connection refused?**
- Check if API is enabled on router: `/ip service print`
- Enable SSL API: `/ip service set api-ssl disabled=no`

**Certificate not issued?**
- Check cert-manager: `kubectl describe certificate your-router-cert`
- Check DNS: `dig your-router.yourdomain.com`

**Job fails?**
- Check logs: `kubectl logs job/job-name`
- Verify secrets exist: `kubectl get secrets`

## Next Steps

- Read [INSTALL.md](INSTALL.md) for detailed installation
- Read [README.md](README.md) for full documentation
- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand how it works

## Need Help?

Open an issue on GitHub or check the troubleshooting section in README.md
