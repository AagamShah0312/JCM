# Judicial Case Management System

A modern, secure, and scalable web-based platform for managing court case records with advanced AI-powered legal assistance.

## 🎯 Features

### Core Features
- ✅ **Case Management**: Create, update, and delete case records with full audit trails
- ✅ **Document Management**: Upload and manage case documents with version control
- ✅ **Case Timeline**: Track all case events and milestones
- ✅ **User Roles**: Role-based access control (Admin, Lawyer)
- ✅ **Notifications**: Real-time notifications for case updates and hearings
- ✅ **Advanced Search**: Full-text search with multiple filters
- ✅ **Audit Logging**: Complete audit trail of all system activities

### AI-Powered Features
- 🤖 **AI Legal Assistant**: RAG-based legal assistant for case analysis
- 📄 **Document Summarization**: Automatically summarize case documents
- 📅 **Timeline Generation**: Auto-generate timelines from documents
- 💬 **Q&A on Cases**: Ask questions and get answers based on case documents
- 🔍 **Entity Extraction**: Extract key entities from legal documents

### Security Features
- 🔐 **JWT Authentication**: Secure token-based authentication
- 🛡️ **Role-Based Access Control**: Fine-grained permission management
- 🔒 **Password Hashing**: Bcrypt-based password hashing
- 📝 **Audit Logging**: Track all user actions
- ⚡ **Rate Limiting**: API rate limiting to prevent abuse
- 🚨 **File Validation**: Secure file upload with type and size validation

## 🏗️ Architecture

### Technology Stack
- **Backend**: Django 4.2 + Django REST Framework
- **Frontend**: React 18 + Tailwind CSS
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **AI/LLM**: Google Gemini (via google-generativeai SDK)
- **Vector DB**: FAISS or Pinecone
- **Task Queue**: Celery + Redis
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx

### System Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                     │
│          Dashboard | Cases | Search | AI Chat           │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Nginx Reverse Proxy                    │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    ┌────────┐  ┌────────┐  ┌─────────┐
    │ Django │  │Celery  │  │  Redis  │
    │ API    │  │Worker  │  │  Cache  │
    └────┬───┘  └───┬────┘  └────┬────┘
         │          │            │
         └──────────┼────────────┘
                    ▼
          ┌──────────────────────┐
          │   PostgreSQL DB      │
          │  Cases, Documents... │
          └──────────────────────┘
```

## 📋 Database Schema

### Core Models
- **User**: Admin and Lawyer accounts
- **Case**: Court case records
- **CaseDocument**: Uploaded documents
- **CaseTimeline**: Case events and milestones
- **CaseNote**: Internal notes
- **Notification**: User notifications
- **AuditLog**: System audit trail
- **AIConversation**: AI chat conversations
- **AIQuery**: AI query history

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15
- Redis 7
- Docker & Docker Compose (optional)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd JudicialCaseManagementSystem
   ```

2. **Setup Backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp ../.env.example ../.env
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

3. **Setup Frontend**
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api
   - Admin Panel: http://localhost:8000/admin

### Docker Setup

```bash
# Copy environment file
cp .env.example .env

# Build and start containers
docker-compose up -d

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Access the application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login user
- `POST /api/auth/logout/` - Logout user
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/` - Update user profile

### Case Endpoints
- `GET /api/cases/` - List cases (with filtering)
- `POST /api/cases/` - Create case
- `GET /api/cases/{id}/` - Get case details
- `PUT /api/cases/{id}/` - Update case
- `DELETE /api/cases/{id}/` - Delete case
- `GET /api/cases/{id}/timeline/` - Get case timeline
- `POST /api/cases/{id}/add_timeline_event/` - Add timeline event
- `GET /api/cases/{id}/notes/` - Get case notes
- `POST /api/cases/{id}/notes/` - Add case note
- `GET /api/cases/upcoming_hearings/` - Get upcoming hearings
- `GET /api/cases/statistics/` - Get case statistics (admin only)

### Document Endpoints
- `GET /api/documents/` - List documents
- `POST /api/documents/` - Upload document
- `GET /api/documents/{id}/` - Get document details
- `GET /api/documents/{id}/download/` - Download document
- `DELETE /api/documents/{id}/` - Delete document
- `GET /api/documents/{id}/extraction/` - Get document text extraction

### AI Assistant Endpoints
- `POST /api/ai/conversations/` - Create conversation
- `GET /api/ai/conversations/` - List conversations
- `GET /api/ai/conversations/{id}/` - Get conversation
- `POST /api/ai/conversations/{id}/send_message/` - Send message
- `POST /api/ai/conversations/{id}/summarize/` - Summarize case
- `POST /api/ai/conversations/{id}/generate_timeline/` - Generate timeline

### Notification Endpoints
- `GET /api/notifications/` - List notifications
- `GET /api/notifications/unread/` - Get unread notifications
- `POST /api/notifications/{id}/mark_as_read/` - Mark as read
- `POST /api/notifications/mark_all_as_read/` - Mark all as read

## 🔒 Security Best Practices

1. **Environment Variables**: Never commit `.env` files; use `.env.example`
2. **JWT Tokens**: Access tokens expire after 15 minutes; use refresh tokens
3. **Password Policy**: Minimum 8 characters, uppercase, digit, special character
4. **File Validation**: Only PDF, DOCX, images allowed; max 10MB
5. **Rate Limiting**: 1000 requests/hour per user
6. **HTTPS**: Always use HTTPS in production
7. **CORS**: Configure allowed origins properly
8. **Audit Logs**: All sensitive operations are logged

## 📦 Deployment

### Render Deployment

1. **Create Render account** at https://render.com
2. **Create PostgreSQL database**
3. **Create Web Service** and connect GitHub repo
4. **Set environment variables** in Render dashboard
5. **Deploy**

See [DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) for detailed steps.

### AWS Deployment

See [DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) for AWS ECS and RDS setup.

### Azure Deployment

See [DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) for Azure App Service and Database setup.

## 📖 Documentation

- [Setup Guide](./docs/SETUP_GUIDE.md) - Detailed setup instructions
- [API Documentation](./docs/API_DOCUMENTATION.md) - Complete API reference
- [AI Architecture](./docs/AI_ARCHITECTURE.md) - Current AI flow, endpoints, and migration path
- [Deployment Guide](./docs/DEPLOYMENT_GUIDE.md) - Deployment to various platforms
- [Database Schema](./docs/DATABASE_SCHEMA.md) - Database design documentation

## 🧪 Testing

```bash
# Backend Tests
cd backend
pytest

# Frontend Tests
cd frontend
npm test
```

## 📝 Project Structure

```
JudicialCaseManagementSystem/
├── backend/
│   ├── judicial_backend/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── authentication/
│   │   ├── cases/
│   │   ├── documents/
│   │   ├── notifications/
│   │   ├── ai_assistant/
│   │   └── audit/
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── services/
│   │   ├── context/
│   │   └── styles/
│   ├── package.json
│   └── public/
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docs/
│   ├── SETUP_GUIDE.md
│   ├── API_DOCUMENTATION.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── DATABASE_SCHEMA.md
├── .env.example
└── README.md
```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check existing issues on GitHub
2. Review documentation in `/docs` folder
3. Create a new issue with detailed description


## 🙏 Acknowledgments

- Django and Django REST Framework community
- React community
- Open source contributors

---

**Last Updated**: 2026-05-31  
**Version**: 1.0.0
