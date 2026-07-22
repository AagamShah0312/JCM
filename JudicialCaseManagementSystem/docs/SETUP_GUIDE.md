# Judicial Case Management System - Setup Guide

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Setup](#docker-setup)
3. [Database Setup](#database-setup)
4. [AI/LLM Configuration](#aillm-configuration)
5. [Troubleshooting](#troubleshooting)

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15
- Redis 7
- Git

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create .env file**
   ```bash
   cp ../.env.example ../.env
   ```

5. **Update .env with your settings**
   ```env
   DEBUG=True
   SECRET_KEY=your-secret-key
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=judicial_case_db
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_HOST=localhost
   DB_PORT=5432
   ```

6. **Run migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Create .env file** (optional for development)
   ```bash
   echo "REACT_APP_API_URL=http://localhost:8000/api" > .env
   ```

4. **Start development server**
   ```bash
   npm start
   ```

5. **Access application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api
   - Admin Panel: http://localhost:8000/admin

## Docker Setup

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Quick Start with Docker

1. **Copy environment file**
   ```bash
   cp .env.example .env
   ```

2. **Update .env file**
   ```env
   DEBUG=False
   SECRET_KEY=your-production-secret-key
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```

3. **Build and start containers**
   ```bash
   docker-compose up -d
   ```

4. **Run migrations**
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

6. **Access application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin

### Docker Commands

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Run management commands
docker-compose exec backend python manage.py shell

# Stop containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Database Setup

### PostgreSQL Local Installation

#### Windows
1. Download installer from https://www.postgresql.org/download/windows/
2. Run installer and follow prompts
3. Set password for `postgres` user
4. Note the port (default: 5432)

#### macOS
```bash
brew install postgresql@15
brew services start postgresql@15
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### Database Creation

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE judicial_case_db;

# Create user
CREATE USER judicial_user WITH PASSWORD 'secure_password';

# Grant privileges
ALTER ROLE judicial_user SET client_encoding TO 'utf8';
ALTER ROLE judicial_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE judicial_user SET default_transaction_deferrable TO on;
ALTER ROLE judicial_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE judicial_case_db TO judicial_user;

# Exit
\q
```

## AI/LLM Configuration

### OpenAI Setup

1. **Get API Key**
   - Sign up at https://platform.openai.com
   - Go to API keys section
   - Create new secret key

2. **Update .env**
   ```env
   OPENAI_API_KEY=sk-xxx...
   USE_LOCAL_LLM=False
   ```

3. **Backend code will automatically use GPT-4**

### Local LLM with Ollama

1. **Install Ollama**
   - Download from https://ollama.ai
   - Run installer

2. **Pull model**
   ```bash
   ollama pull llama2
   ```

3. **Start Ollama**
   ```bash
   ollama serve
   ```

4. **Update .env**
   ```env
   USE_LOCAL_LLM=True
   OLLAMA_BASE_URL=http://localhost:11434
   ```

### Vector Database Setup

#### FAISS (Recommended for local development)
No setup required. FAISS is included in requirements.txt

#### Pinecone (For production)

1. **Create Pinecone account** at https://www.pinecone.io
2. **Create index** named `judicial-cases`
3. **Update .env**
   ```env
   VECTOR_DB_TYPE=pinecone
   PINECONE_API_KEY=xxx...
   PINECONE_INDEX=judicial-cases
   ```

## Redis Setup

### Local Installation

#### Windows
1. Download from https://github.com/microsoftarchive/redis/releases
2. Extract and run `redis-server.exe`

#### macOS
```bash
brew install redis
brew services start redis
```

#### Linux
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

### Verify Redis
```bash
redis-cli ping
# Should return: PONG
```

## Troubleshooting

### Database Connection Issues

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
```bash
# Check PostgreSQL is running
psql -U postgres

# Verify credentials in .env
# Ensure DB_HOST, DB_PORT, DB_NAME are correct
```

### Migration Errors

**Error**: `django.db.utils.IntegrityError`

**Solution**:
```bash
# Reset database (WARNING: deletes all data)
python manage.py flush
python manage.py migrate

# Or drop and recreate database
psql -U postgres
DROP DATABASE judicial_case_db;
CREATE DATABASE judicial_case_db;
```

### Port Already in Use

**Error**: `Address already in use`

**Solution**:
```bash
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

### Memory Issues

**Error**: `MemoryError` or application crashes

**Solution**:
- Increase swap space
- Check available RAM: `free -h`
- Reduce Celery worker processes

### Static Files Not Loading

**Solution**:
```bash
# Collect static files
python manage.py collectstatic --noinput

# Check STATIC_URL and STATIC_ROOT in settings.py
```

### API CORS Issues

**Error**: `CORS policy: blocked by CORS policy`

**Solution**:
```env
# Update .env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### AI Assistant Not Working

**Check 1**: Is OpenAI key valid?
```bash
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

**Check 2**: Are documents processed?
```bash
python manage.py shell
>>> from apps.documents.models import CaseDocument
>>> CaseDocument.objects.count()
```

**Check 3**: Are embeddings generated?
```bash
>>> from apps.ai_assistant.models import DocumentEmbedding
>>> DocumentEmbedding.objects.count()
```

## Performance Optimization

### Caching
- Enable Redis caching in production
- Configure cache timeout in settings.py

### Database Optimization
```bash
# Create indexes for frequently queried fields
python manage.py sqlsequencereset apps.cases | python manage.py dbshell

# Analyze query performance
# Use Django Debug Toolbar in development
pip install django-debug-toolbar
```

### Frontend Optimization
```bash
# Create production build
npm run build

# Analyze bundle size
npm install -g webpack-bundle-analyzer
```

## Security Configuration

1. **Update SECRET_KEY in production**
   ```bash
   python manage.py shell
   >>> from django.core.management.utils import get_random_secret_key
   >>> get_random_secret_key()
   ```

2. **Enable HTTPS**
   - Configure SSL certificates
   - Update ALLOWED_HOSTS

3. **Setup email**
   - Configure email backend in settings.py
   - Get app password for Gmail

## Next Steps

After setup:
1. Create admin account
2. Configure AI/LLM settings
3. Test API endpoints
4. Deploy to production (see DEPLOYMENT_GUIDE.md)

---

For more help, see the main README.md or contact support.
