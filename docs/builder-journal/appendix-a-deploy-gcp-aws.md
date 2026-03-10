# Appendix A: Deploy to GCP and AWS

You've built a working Ragbits application locally. This appendix shows you how to package it as a Docker container and deploy it to either Google Cloud Platform or Amazon Web Services with a single script.

Both deployments use OpenTofu for infrastructure provisioning, Docker for containerization, and a WAF that restricts access to your IP address only.

## What You'll Deploy

- A containerized Ragbits chat application
- Secret management for your OpenAI API key (no keys in code or environment)
- A firewall that whitelists only your current IP address
- Infrastructure-as-code that you can tear down with one command

### Architecture by Cloud

| Component | GCP | AWS |
|-----------|-----|-----|
| Compute | Cloud Run v2 | App Runner |
| Container registry | Artifact Registry | ECR |
| Secrets | Secret Manager | Secrets Manager |
| Firewall | Cloud Armor + Global Load Balancer | WAF v2 |
| State storage | Cloud Storage | S3 |

## Prerequisites

Before starting, make sure you have:

- A working Ragbits application from any previous section
- [OpenTofu](https://opentofu.org/docs/intro/install/) (`tofu`) installed
- [Docker](https://docs.docker.com/get-docker/) installed and running
- An OpenAI API key

For your target cloud, you also need:

=== "GCP"

    - [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`) installed
    - A GCP project where you have permissions to create resources

=== "AWS"

    - [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) (`aws`) installed
    - Your 12-digit AWS account ID

## Step 1: Containerize the Application

Create a `Dockerfile` in your project root:

```dockerfile title="Dockerfile" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/dd51c31/Dockerfile"
```

This Dockerfile:

1. Starts from a slim Python 3.10 image with `uv` for fast dependency installation
2. Installs dependencies first (for Docker layer caching), then copies the rest of the code
3. Runs the Ragbits CLI on port 8080, the default for both Cloud Run and App Runner

Add a `.dockerignore` to keep the image lean:

```text title=".dockerignore" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/dd51c31/.dockerignore"
```

You can test the container locally before deploying:

```bash
docker build -t ragbits-chat .
docker run -p 8080:8080 -e OPENAI_API_KEY="your-key" ragbits-chat
```

Open http://localhost:8080 to verify it works.

## Step 2: Configure the Deployment

The deployment is driven by a single config file. Create `infrastructure/config.sh`:

```bash title="infrastructure/config.sh" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/dd51c31/infrastructure/config.sh"
```

Edit this file to set:

- `TARGET_CLOUD` — choose `"GCP"` or `"AWS"`
- `OPENAI_API_KEY` — your API key (never commit this to version control)
- Cloud-specific settings: project ID, region, account ID, and state bucket name

The script also auto-detects your public IPv4 address for firewall whitelisting.

## Step 3: Authenticate with Your Cloud Provider

=== "GCP"

    ```bash
    gcloud auth login --no-launch-browser
    gcloud auth application-default login --no-launch-browser
    ```

    If you encounter errors during deployment, they're usually caused by service APIs not being enabled for your project. Follow the instructions in the terminal to enable them.

=== "AWS"

    ```bash
    aws configure
    ```

    The region you set here must match `AWS_REGION` in `config.sh`.

## Step 4: Deploy

Run the deployment script:

```bash
bash infrastructure/deploy_infra.sh
```

This single script handles everything:

=== "GCP"

    1. Creates a Cloud Storage bucket for Terraform state
    2. Provisions Artifact Registry and Secret Manager
    3. Uploads your OpenAI API key to Secret Manager
    4. Builds and pushes the Docker image to Artifact Registry
    5. Deploys Cloud Run with a Global Load Balancer and Cloud Armor WAF

    The app needs about 5 minutes to be fully accessible after the script finishes due to Load Balancer propagation.

=== "AWS"

    1. Creates an S3 bucket for Terraform state
    2. Provisions ECR and Secrets Manager
    3. Uploads your OpenAI API key to Secrets Manager
    4. Builds and pushes the Docker image to ECR
    5. Deploys App Runner with WAF v2

    The app should be accessible immediately when the script finishes.

The script outputs the public URL of your application at the end.

!!! note "IP Whitelisting"
    The deployed app is only accessible from the IP address that ran the deployment script. If your IP changes, re-run the deploy script to update the firewall rules.

## Step 5: Clean Up

When you're done, tear down all resources to avoid charges:

```bash
bash infrastructure/destroy_infra.sh
```

This removes all provisioned resources including the state bucket. The destroy is complete and irreversible.

## Infrastructure Deep Dive

The OpenTofu configurations define all cloud resources declaratively. Here's what each cloud provisions:

=== "GCP"

    The GCP deployment creates a Cloud Run service behind a Global Load Balancer with Cloud Armor for IP-based access control. Cloud Run's ingress is set to `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`, so direct access is blocked — all traffic must pass through the WAF.

    ```hcl title="infrastructure/gcp/terraform/main.tf" linenums="1"
    --8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/dd51c31/infrastructure/gcp/terraform/main.tf"
    ```

=== "AWS"

    The AWS deployment uses App Runner for zero-config container hosting, with a WAF v2 Web ACL attached directly to the service. An IAM instance role grants the service permission to read the API key from Secrets Manager at runtime.

    ```hcl title="infrastructure/aws/terraform/main.tf" linenums="1"
    --8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/dd51c31/infrastructure/aws/terraform/main.tf"
    ```

## The Complete Deployment Setup

[View full source on GitHub](https://github.com/deepsense-ai/ragbits-example/tree/dd51c31/infrastructure)

```dockerfile title="Dockerfile" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/dd51c31/Dockerfile"
```

```bash title="infrastructure/config.sh" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/dd51c31/infrastructure/config.sh"
```

```bash title="infrastructure/deploy_infra.sh" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/dd51c31/infrastructure/deploy_infra.sh"
```

```bash title="infrastructure/destroy_infra.sh" linenums="1"
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/dd51c31/infrastructure/destroy_infra.sh"
```

## What You've Learned

1. How to containerize a Ragbits application with Docker
2. How to configure cloud-agnostic deployment with a shared config file
3. How to deploy to GCP (Cloud Run + Cloud Armor) or AWS (App Runner + WAF)
4. How to manage secrets securely with cloud-native secret managers
5. How to restrict access with IP-based firewall rules
6. How to tear down all resources cleanly

## Reference

| Component | Service | Purpose |
|-----------|---------|---------|
| `Dockerfile` | Docker | Container image definition |
| `config.sh` | Shell | Shared deployment configuration |
| `deploy_infra.sh` | Shell | One-command deploy orchestrator |
| `destroy_infra.sh` | Shell | One-command teardown orchestrator |
| Cloud Run / App Runner | GCP / AWS | Serverless container hosting |
| Cloud Armor / WAF v2 | GCP / AWS | IP-based access control |
| Secret Manager / Secrets Manager | GCP / AWS | Secure API key storage |
| Artifact Registry / ECR | GCP / AWS | Docker image registry |
| OpenTofu | IaC | Declarative infrastructure provisioning |
