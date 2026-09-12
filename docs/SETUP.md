# Environment Setup & Deployment Guide

This guide covers everything from zero to a fully running production or development environment for the Web Telegram Shop.

## Table of Contents
1. [Server Requirements & Recommendations](#1-server-requirements--recommendations)
2. [System Dependencies & Swap Setup]()
3. [Run Profiles Explained](#3-run-profiles-explained)
4. [Step-by-Step Installation](#4-step-by-step-installation)
5. [Continuous Deployment (CD)](#5-continuous-deployment-cd-optional)

## 1. Server Requirements & Recommendations

For a reliable production deployment, we recommend decoupling the application server from the database and storage to ensure scalability.

**Application Server (Recommended Starting Specs):**
- **Cloud Provider:** Azure (Standard B2ls v2) or equivalent (DigitalOcean, AWS, Hetzner)
- **OS:** Ubuntu 24.04 LTS
- **CPU & RAM:** 2 vCPUs, 4 GiB RAM
- **Storage:** 30 GB SSD
- **Swap:** 2 GiB (Crucial for preventing Out-Of-Memory errors during build/runtime)

**Database Server:**
- Azure Database for PostgreSQL (Burstable B1ms, 1 vCore, 2 GiB RAM, 32 GiB storage) or a managed DB on your preferred provider.

**Object Storage (S3):**
- Cloudflare R2 (Free tier is generous and sufficient for starters) or AWS S3.

## 2. System Dependencies & Swap Setup

Connect to your Ubuntu 24.04 server and set up the Swap file to ensure stability:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

Next, update your system and install necessary dependencies (Git, Python 3.12, and Docker):

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-pip python3-venv python3-dev
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu$(. /etc/os-release && echo VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```
## 3. Run Profiles Explained

The project supports three distinct launch profiles:

- **dev**: For local development and testing. Uses Ngrok to expose local webhooks to Telegram. Changes to code update dynamically without restarting containers, though initial execution is slightly slower.
- **prod**: For production environments. Highly optimized, stable, and fast. Requires a dedicated server with a static domain, plus external Database and S3 storage. Recommended for live trading.
- **standalone**: Similar to `prod`, but hosts the PostgreSQL database and MinIO (S3 compatible) storage on the same server within Docker. Suitable for low-budget startups, though decoupling (using `prod`) is recommended for scaling.

## 4. Step-by-Step Installation

### Step 1: Clone the Repository
Clone the project to your server or local machine and navigate to the directory:
```bash
git clone https://github.com/Xyroset/Web-Telegram-Shop.git
cd Web-Telegram-Shop
```

### Step 2: Initialize Configuration
Run the setup script to generate `.env` files from templates, create secure Django/Webhook keys, and set defaults:
```bash
make init
```

### Step 3: Configure Environment Variables
Open the generated `.env` file and fill in the required fields based on your deployment profile.

**Base Settings:**
- `DEBUG`: Set to `True` for `dev`, `False` for `prod`/`standalone`.
- `TZ`: Keep as `UTC` or set to your preferred timezone.

**Database (Required for prod, standalone can use defaults):**
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT`
- `POSTGRES_HOST`

**S3 Storage (Required for prod, standalone can use defaults):**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_STORAGE_BUCKET_NAME`
- `AWS_S3_ENDPOINT_URL`
- `AWS_S3_REGION_NAME`
- `AWS_S3_CUSTOM_DOMAIN`

**Telegram Bot (Required):**
- `TELEGRAM_BOT_TOKEN`: Get this from @BotFather on Telegram.

**Ngrok (Required for dev profile ONLY):**
- `NGROK_AUTHTOKEN`: Get this from your ngrok dashboard (do not include 'https://').
- `NGROK_STATIC_DOMAIN`: Your static ngrok domain.

**Payment Gateways (Testnet / Sandbox):**
- `SANDBOX_NOWPAYMENTS_API_KEY`: Key from sandbox.nowpayments.io.
- `SANDBOX_NOWPAYMENTS_IPN_SECRET`: Webhook secret. URL format: `https://<YOUR_DOMAIN>/api/v1/payments/nowpayments/` (or your ngrok domain)
- `SANDBOX_CRYPTOBOT_API_KEY`: Key from @CryptoTestnetBot. Webhook URL format: `https://<YOUR_DOMAIN>/api/v1/payments/cryptobot/` (or your ngrok domain)

**Payment Gateways (Mainnet / Production):**
- `NOWPAYMENTS_API_KEY`: Key from nowpayments.io.
- `NOWPAYMENTS_IPN_SECRET`: Webhook secret. URL format: `https://<YOUR_DOMAIN>/api/v1/payments/nowpayments/` (or your ngrok domain)
- `CRYPTOBOT_API_KEY`: Key from @CryptoBot. Webhook URL format: `https://<YOUR_DOMAIN>/api/v1/payments/cryptobot/` (or your ngrok domain)

**Monitoring (Optional but recommended):**
- `SENTRY_DSN`: Your project DSN from Sentry.io for error tracking.

**Domains (Required for prod / standalone):**
Point your A-records to your server's IP address (TTL 300).
- `FRONTEND_VIRTUAL_HOST`: E.g., `yourdomain.com,www.yourdomain.com` (no https://)
- `FRONTEND_LETSENCRYPT_HOST`: Same as above.
- `BACKEND_VIRTUAL_HOST`: E.g., `api.yourdomain.com` (no https://)
- `BACKEND_LETSENCRYPT_HOST`: Same as above.
*(Note: If using standalone, you will also configure an `s3.` subdomain).*

**Email Notifications (Optional):**
- `DEFAULT_EMAIL`: Sending email address.
- `EMAIL_HOST_USER`: Usually matches DEFAULT_EMAIL.
- `EMAIL_HOST_PASSWORD`: App password (see [this guide](https://www.youtube.com/watch?v=OGNajVcyz1I) for Gmail setup).

### Step 4 & 5: Build and Start
Build the images and start the containers using your chosen profile (`dev`, `prod`, or `standalone`).

To build and start simultaneously:
```bash
make start-dev ARGS="--build"
```
*(Replace `start-dev` with `start-prod` or `start-standalone` as needed).*

Once the images are built, you can start the project in the future simply by running:
```bash
make start-dev
```

### Step 6: Verification
Watch the terminal output. If the startup is successful, you will see Celery workers booting up. 
- Open Telegram and test your bot.
- Access the Admin Panel at `https://api.<YOUR_DOMAIN>/admin` (or your ngrok domain).

## 5. Continuous Deployment (CD) (Optional)

If you want to automate your deployments via GitHub Actions, we have provided a template workflow.

1. Navigate to `.github/workflows/`.
2. Rename `cd.yaml.example` to `cd.yaml`.
3. Add the required deployment secrets (e.g., SSH keys, server IP, Docker credentials) to your GitHub Repository Secrets as defined in the YAML file.
4. Push to the `main` branch to trigger the automated deployment.
