#!/bin/sh
kubectl create configmap upload-router-complete-script --from-file=upload-router-complete.py=../src/upload-router-complete.py --dry-run=client -o yaml | kubectl apply -f -
