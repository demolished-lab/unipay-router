# Deployment

## Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| hyperswitch-server | 8080 | Hyperswitch API |
| hyperswitch-control-center | 8090 | Hyperswitch Dashboard |
| postgres | 5432 | Database |
| redis | 6379 | Cache |

## Local Development

### Prerequisites

- Python 3.10+
- Docker Desktop (or Docker Engine)
- Hyperswitch Server (via Docker or binary)

### Setup

```bash
# Clone
git clone https://github.com/your-org/unipay-router.git
cd unipay-router

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .

# Start Hyperswitch
docker-compose up -d hyperswitch-server postgres redis

# Run the API
python -m unipay_router.cli

# Or use the API directly
python -c "from unipay_router.api import UniPayAPI; print(UniPayAPI().health_check())"
```

## Cloud Deployment

### AWS (Free Tier Eligible)

```mermaid
graph TB
    subgraph "AWS Free Tier"
        EC2[t2.micro EC2]
        RDS[db.t2.micro RDS]
        ELASTICACHE[cache.t2.micro ElastiCache]
        S3[S3 Bucket]
    end

    subgraph "UniPay Stack"
        ROUTER[UniPay Router]
        HS[Hyperswitch Server]
    end

    EC2 --> ROUTER
    EC2 --> HS
    ROUTER --> RDS
    ROUTER --> ELASTICACHE
```

**Estimated Cost:** ₹0/month (within free tier limits)

### Cloudflare Workers (Edge)

```bash
# Deploy UniPay Router as Cloudflare Worker
npx wrangler deploy
```

**Estimated Cost:** ₹0/month (100K requests/day free)

### DigitalOcean (512MB Droplet)

```bash
# Create droplet
doctl compute droplet create unipay-router \
  --size s-1vcpu-512mb-10gb \
  --image ubuntu-22-04-x64 \
  --region blr1

# SSH and setup
ssh root@<ip>
curl -fsSL https://get.docker.com | sh
docker-compose up -d
```

**Estimated Cost:** ₹400/month (~$5)

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/unipay

# Redis
REDIS_URL=redis://localhost:6379

# Hyperswitch
HYPERSWITCH_URL=http://localhost:8080
HYPERSWITCH_API_KEY=...

# Provider Keys
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=xxxxx
CASHFREE_APP_ID=test_app_xxxxx
CASHFREE_SECRET=xxxxx
PAYU_MERCHANT_KEY=xxxxx
PAYU_MERCHANT_SALT=xxxxx

# FX API (Free tier)
EXCHANGE_RATE_API_KEY=xxxxx

# API Security
API_KEY=your-api-key-here
```

## Production Checklist

- [ ] Set strong API keys
- [ ] Enable HTTPS
- [ ] Configure rate limiting
- [ ] Set up monitoring (Grafana Cloud free tier)
- [ ] Configure backup for PostgreSQL
- [ ] Set up log aggregation
- [ ] Enable PCI compliance mode
- [ ] Configure webhook retry logic

## Monitoring

### Grafana Cloud (Free)

1. Sign up at [grafana.com](https://grafana.com)
2. Get API key and endpoint
3. Add to `docker-compose.yml`:

```yaml
environment:
  - GRAFANA_API_KEY=xxxxx
  - GRAFANA_ENDPOINT=https://your-instance.grafana.net
```

## SSL/TLS

Use Let's Encrypt for free SSL:

```bash
# Install certbot
apt install certbot

# Get certificate
certbot certonly --standalone -d unipay.yourdomain.com

# Update nginx config
ssl_certificate /etc/letsencrypt/live/unipay.yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/unipay.yourdomain.com/privkey.pem;
```
