#!/bin/bash

set -euxo pipefail

echo $GCP_KEY | base64 -d >> gcp_creds.json
gcloud auth activate-service-account --key-file gcp_creds.json
gcloud config set project ds-internal-db-ally

# Build the documentation
uv run mkdocs build

# Upload built docs to a bucket
gcloud storage cp -r site/* gs://ragbits-documentation

# Invalidate cached content in the CDN
gcloud compute url-maps invalidate-cdn-cache ragbits-documentation-lb \
    --path "/*" --async