
# Judicial Case Management System - Deployment Guide

## Table of Contents
1. [Render Deployment](#render-deployment)
2. [AWS Deployment](#aws-deployment)
3. [Azure Deployment](#azure-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Production Configuration](#production-configuration)

## Render Deployment

### Step 1: Prepare Repository
```bash
# Ensure .env.example exists (no secrets)
# Ensure .gitignore includes .env

git add .
git commit -m "Prepare for Render deployment"
git push
```

### Step 2: Create PostgreSQL Database
1. Go to https://render.com/dashboard
2. Click "New +" → "PostgreSQL"
3. Configure:
   - Name: `judicial-db`
   - Database name: `judicial_case_db`
   - User: `postgres`
4. Note connection string

### Step 3: Create Backend Web Service
1. Click "New +" → "Web Service"
2. Connect GitHub repository
3. Configure:
   - Name: `judicial-backend`
   - Environment: `Python 3.11`
   - Build Command: `pip install -r backend/requirements.txt && python backend/manage.py migrate`
   - Start Command: `gunicorn judicial_backend.wsgi:application --bind 0.0.0.0:$PORT --chdir backend`
4. Set environment variables:
   ```
   DEBUG=False
   SECRET_KEY=<generate-random-key>
   DATABASE_URL=<from-PostgreSQL-service>
   ALLOWED_HOSTS=your-app.onrender.com
   OPENAI_API_KEY=<your-key>
   ```

### Step 4: Create Frontend Web Service
1. Click "New +" → "Web Service"
2. Connect GitHub repository
3. Configure:
   - Name: `judicial-frontend`
   - Environment: `Node 18`
   - Build Command: `cd frontend && npm install && npm run build`
   - Start Command: `cd frontend && npx serve -s build -l 3000`
4. Set environment variables:
   ```
   REACT_APP_API_URL=https://your-backend.onrender.com/api
   ```

### Step 5: Deploy
- Render automatically deploys on every push
- Monitor deployment in Dashboard

## AWS Deployment

### Architecture
```
Route53 → CloudFront (CDN) → ALB → ECS Fargate
                ↓
              S3 (Static)
                ↓
              RDS (PostgreSQL)
                ↓
              ElastiCache (Redis)
```

### Prerequisites
- AWS Account
- AWS CLI configured
- IAM permissions

### Step 1: Create RDS Database
```bash
aws rds create-db-instance \
  --db-instance-identifier judicial-db \
  --db-instance-class db.t3.small \
  --engine postgres \
  --engine-version 15.3 \
  --master-username postgres \
  --master-user-password <strong-password> \
  --allocated-storage 20 \
  --publicly-accessible false \
  --vpc-security-group-ids sg-xxxxx
```

### Step 2: Create ElastiCache Redis
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id judicial-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1
```

### Step 3: Create ECR Repositories
```bash
# Backend
aws ecr create-repository --repository-name judicial-backend

# Frontend
aws ecr create-repository --repository-name judicial-frontend
```

### Step 4: Build and Push Images
```bash
# Build backend image
docker build -t judicial-backend:latest -f docker/Dockerfile .

# Tag image
docker tag judicial-backend:latest \
  <account-id>.dkr.ecr.<region>.amazonaws.com/judicial-backend:latest

# Push to ECR
aws ecr get-login-password --region <region> | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.<region>.amazonaws.com

docker push <account-id>.dkr.ecr.<region>.amazonaws.com/judicial-backend:latest
```

### Step 5: Create ECS Cluster and Services
```bash
# Create cluster
aws ecs create-cluster --cluster-name judicial-cluster

# Create task definition (JSON format)
# See: docker/ecs-task-definition.json

aws ecs register-task-definition \
  --cli-input-json file://docker/ecs-task-definition.json
```

### Step 6: Configure S3 for Static Files
```bash
# Create bucket
aws s3 mb s3://judicial-case-mgmt-static

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket judicial-case-mgmt-static \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket judicial-case-mgmt-static \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### Step 7: Configure CloudFront
1. Go to AWS CloudFront Console
2. Create distribution
3. Origin: S3 bucket or ALB
4. Cache policy: Managed policy for Django

### Step 8: Configure Route53
1. Create hosted zone
2. Create A record pointing to CloudFront distribution

## Azure Deployment

### Architecture
```
Azure Front Door → App Service → Azure Database for PostgreSQL
                                ↓
                              Azure Cache for Redis
```

### Prerequisites
- Azure Account
- Azure CLI installed
- Resource Group created

### Step 1: Create Database
```bash
az postgres server create \
  --resource-group judicial-rg \
  --name judicial-db-server \
  --admin-user postgres \
  --admin-password <password> \
  --sku-name B_Gen5_1 \
  --version 15
```

### Step 2: Create Redis Cache
```bash
az redis create \
  --resource-group judicial-rg \
  --name judicial-redis \
  --sku basic \
  --vm-size c0
```

### Step 3: Create App Service Plan
```bash
az appservice plan create \
  --name judicial-plan \
  --resource-group judicial-rg \
  --sku B1 \
  --is-linux
```

### Step 4: Deploy Backend
```bash
# Create web app
az webapp create \
  --resource-group judicial-rg \
  --plan judicial-plan \
  --name judicial-backend-app \
  --runtime "python|3.11"

# Deploy code
cd backend
az webapp up --resource-group judicial-rg \
  --name judicial-backend-app

# Configure environment
az webapp config appsettings set \
  --resource-group judicial-rg \
  --name judicial-backend-app \
  --settings \
  DEBUG=False \
  SECRET_KEY=<key> \
  DATABASE_URL=<postgresql-url> \
  OPENAI_API_KEY=<key>
```

### Step 5: Deploy Frontend
```bash
# Build
cd frontend
npm run build

# Deploy to Static Web App
az staticwebapp create \
  --resource-group judicial-rg \
  --name judicial-frontend \
  --location westus2 \
  --source https://github.com/your-repo.git \
  --branch main \
  --app-location frontend/build
```

## Docker Deployment

### Local Docker Deployment
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Verify
docker-compose ps

# View logs
docker-compose logs -f
```

### Docker Swarm Deployment
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml judicial

# Verify
docker stack ps judicial
```

### Kubernetes Deployment

Create `k8s/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: judicial-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: judicial-backend
  template:
    metadata:
      labels:
        app: judicial-backend
    spec:
      containers:
      - name: backend
        image: judicial-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: judicial-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

Deploy:
```bash
kubectl apply -f k8s/deployment.yaml
kubectl expose deployment judicial-backend --type=LoadBalancer --port=80 --target-port=8000
```

## Production Configuration

### Environment Variables (Production)
```env
DEBUG=False
SECRET_KEY=<random-64-character-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@host:port/dbname
REDIS_URL=redis://user:password@host:port/0
OPENAI_API_KEY=sk-xxxxx
USE_LOCAL_LLM=False
CELERY_BROKER_URL=redis://host:port/0
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Security Checklist
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS configured correctly
- [ ] SECRET_KEY changed
- [ ] HTTPS enabled
- [ ] Database backups configured
- [ ] SSL certificates installed
- [ ] Rate limiting enabled
- [ ] WAF rules configured
- [ ] Security headers set
- [ ] CORS configured properly
- [ ] API keys secured
- [ ] Logging configured
- [ ] Monitoring enabled
- [ ] Backup retention set
- [ ] Disaster recovery plan

### Performance Optimization
- Enable caching headers
- Enable gzip compression
- Optimize database queries
- Use CDN for static files
- Configure auto-scaling
- Set up load balancing
- Enable connection pooling
- Monitor performance metrics

### Monitoring and Logging
```bash
# AWS CloudWatch
aws logs create-log-group --log-group-name /ecs/judicial

# Azure Monitor
az monitor metrics create --resource-group judicial-rg

# Datadog (3rd party)
# Add Datadog agent to containers
```

### Backup and Recovery
```bash
# AWS RDS automated backups
aws rds modify-db-instance \
  --db-instance-identifier judicial-db \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00"

# Manual backup
aws rds create-db-snapshot \
  --db-instance-identifier judicial-db \
  --db-snapshot-identifier judicial-backup-$(date +%Y%m%d)
```

### Health Checks
Configure health check endpoints:
- Backend: `/api/health/`
- Frontend: `/`

### SSL Certificates
```bash
# Using Let's Encrypt with Certbot
certbot certonly --standalone -d yourdomain.com

# Auto-renewal
certbot renew --dry-run
```

---

For production support and troubleshooting, contact your DevOps team or cloud provider support.
