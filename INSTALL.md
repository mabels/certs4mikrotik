# Installation Guide

## Prerequisites

1. **Kubernetes cluster** (tested on k3s, should work on any cluster)
2. **cert-manager** installed ([installation guide](https://cert-manager.io/docs/installation/))
3. **external-dns** configured for your DNS provider
4. **kubectl** configured to access your cluster

## Step-by-Step Installation

### 1. Install cert-manager (if not already installed)

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

Wait for cert-manager to be ready:
```bash
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=300s
```

### 2. Create Let's Encrypt Issuer or ClusterIssuer

You can use either a namespace-scoped **Issuer** or a cluster-wide **ClusterIssuer**.

#### Option A: Namespace-scoped Issuer (default)

Edit `k8s/issuer-example.yaml` and update:
- Your email address
- Your DNS provider credentials

Then apply:
```bash
kubectl apply -f k8s/issuer-example.yaml
```

#### Option B: Cluster-wide ClusterIssuer

Edit `k8s/clusterissuer-example.yaml` and update:
- Your email address
- Your DNS provider credentials

Then apply:
```bash
kubectl apply -f k8s/clusterissuer-example.yaml
```

If using a ClusterIssuer, you must also apply the ClusterRole permissions:
```bash
kubectl apply -f k8s/cluster-role-issuers.yaml
kubectl apply -f k8s/clusterrolebinding-issuers.yaml
```

### 3. Configure Your Routers

1. Copy the example configuration:
```bash
cp examples/routers-config-example.yaml k8s/routers-config.yaml
```

2. Edit `k8s/routers-config.yaml` with your router details:
   - Update IP addresses
   - Update router names (these will be used for DNS)
   - Customize secret names if needed

3. Apply the configuration:
```bash
kubectl apply -f k8s/routers-config.yaml
```

### 4. Create Router Password Secrets

For each router in your configuration, create a secret:

```bash
kubectl create secret generic office-router-credentials \
  --from-literal=password='your-strong-password'

kubectl create secret generic home-router-credentials \
  --from-literal=password='your-strong-password'
```

**Security Note:** Never commit these secrets to Git!

### 5. Deploy RBAC Resources

For namespace-scoped Issuer:
```bash
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/role-secret-reader.yaml
kubectl apply -f k8s/role-cert-manager.yaml
kubectl apply -f k8s/rolebinding-secrets.yaml
kubectl apply -f k8s/rolebinding-full.yaml
```

If using ClusterIssuer, also apply:
```bash
kubectl apply -f k8s/cluster-role-issuers.yaml
kubectl apply -f k8s/clusterrolebinding-issuers.yaml
```

### 6. Deploy the Upload Script

```bash
kubectl apply -f k8s/upload-script.yaml
```

### 7. Deploy the CronJob

```bash
kubectl apply -f k8s/cronjob.yaml
```

### 8. Verify Installation

Check that the CronJob was created:
```bash
kubectl get cronjob mikrotik-cert-upload
```

## Testing

### Manual Test Run

Create a test job from the CronJob:
```bash
kubectl create job --from=cronjob/mikrotik-cert-upload test-run-1
```

Watch the logs:
```bash
kubectl logs -f job/test-run-1
```

### Verify Certificates

Check cert-manager certificates:
```bash
kubectl get certificates
kubectl describe certificate office-router-cert
```

Check DNS records (if using external-dns):
```bash
kubectl get dnsendpoint
```

### Verify on Router

Log into your MikroTik router and check:
```
/certificate print
```

You should see your uploaded certificate.

## Troubleshooting

See the main README.md for troubleshooting tips.

## Updating

To update the script:
1. Pull the latest changes from the repository
2. Apply the updated ConfigMap:
   ```bash
   kubectl apply -f k8s/upload-script.yaml
   ```
3. The next CronJob run will use the updated script

## Uninstallation

To remove everything:
```bash
kubectl delete cronjob mikrotik-cert-upload
kubectl delete configmap upload-router-complete-script mikrotik-routers-config
kubectl delete serviceaccount mikrotik-cert-uploader
kubectl delete rolebinding mikrotik-cert-uploader-full mikrotik-cert-uploader-secrets
kubectl delete role cert-manager-controller secret-reader
kubectl delete certificates --all
kubectl delete dnsendpoints --all
kubectl delete secrets office-router-credentials home-router-credentials
```
