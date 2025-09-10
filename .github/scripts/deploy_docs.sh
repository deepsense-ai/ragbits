#!/bin/bash

set -euxo pipefail

# Determine if this is a nightly build or stable release
VERSION_TYPE=${1:-"stable"}

echo $GCP_KEY | base64 -d >> gcp_creds.json
gcloud auth activate-service-account --key-file gcp_creds.json
gcloud config set project ds-internal-db-ally

# Configure git for mike
git config user.name "ds-ragbits-robot"
git config user.email "ds-ragbits-robot@users.noreply.github.com"

# Build and deploy documentation with mike
case $VERSION_TYPE in
    "stable")
        echo "Deploying stable documentation..."
        uv run mike deploy --push --update-aliases stable latest
        uv run mike set-default stable
        ;;
    "nightly")
        echo "Deploying nightly documentation..."
        uv run mike deploy --push nightly
        ;;
    *)
        echo "Unknown version type: $VERSION_TYPE"
        echo "Using stable as default..."
        uv run mike deploy --push --update-aliases stable latest
        uv run mike set-default stable
        ;;
esac

# Upload built docs to a bucket
gcloud storage cp -r site/* gs://ragbits-documentation

# Invalidate cached content in the CDN
gcloud compute url-maps invalidate-cdn-cache ragbits-documentation-lb \
    --path "/*" --async

echo "Documentation deployed successfully for version: $VERSION_TYPE"
