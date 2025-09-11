#!/bin/bash

set -euxo pipefail

echo $GCP_KEY | base64 -d >> gcp_creds.json
gcloud auth activate-service-account --key-file gcp_creds.json
gcloud config set project ds-internal-db-ally

# Upload built docs to a bucket
gcloud storage rsync . gs://ragbits-documentation --recursive --delete-unmatched-destination-objects

# Invalidate cached content in the CDN
gcloud compute url-maps invalidate-cdn-cache ragbits-documentation-lb \
    --path "/*" --async

