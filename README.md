# ⚠️ DEPRECATED - Snake Classic Python Backend

> **This project has been deprecated and is no longer maintained.**
>
> This Python/FastAPI backend has been replaced by a new .NET 10 backend with Clean Architecture.
>
> **New Backend Repository:** [snake-classic-backend](https://github.com/user/snake-classic-backend) (`.NET 10`)
>
> ## Why the migration?
> - **Better Performance**: .NET 10 offers superior performance for real-time game backends
> - **Clean Architecture**: Improved maintainability with Domain, Application, Infrastructure, and API layers
> - **SignalR**: Real-time multiplayer support with SignalR instead of WebSockets
> - **Type Safety**: Stronger type system and compile-time checks
> - **Hangfire**: Robust job scheduling with PostgreSQL persistence
>
> ## Migration Date
> December 2024
>
> ---
>
> # Legacy Documentation (for reference only)

---

# 🐍 Snake Classic - Notification Backend (LEGACY)

High-performance FastAPI-based backend service for managing push notifications for the Snake Classic Flutter game. Built with Firebase Cloud Messaging integration, advanced scheduling capabilities, and comprehensive testing tools.

## ✨ Features

### 🔥 Firebase Integration
- **Firebase Cloud Messaging (FCM)** - Send push notifications to iOS and Android
- **Firebase Admin SDK** - Secure server-to-server communication
- **Token Management** - Validate, register, and manage user FCM tokens
- **Topic Subscriptions** - Organize users into notification groups

### 📱 Notification Types
- **🏆 Tournament Alerts** - New tournaments, reminders, results
- **👥 Social Notifications** - Friend requests, challenges, multiplayer invites
- **🎖️ Achievement Unlocks** - Progress celebrations and milestones
- **📅 Daily Reminders** - Retention campaigns and daily challenges
- **⭐ Special Events** - Limited-time events and announcements

### 📅 Advanced Scheduling
- **APScheduler Integration** - Robust job scheduling with persistence
- **Recurring Notifications** - Daily challenges, weekly leaderboards
- **Tournament Sequences** - Automated reminder chains (60min, 15min, 5min)
- **User Retention Campaigns** - Smart re-engagement strategies
- **Time Zone Support** - Localized scheduling

### 🎯 Targeting & Personalization
- **Individual Targeting** - Send to specific users via FCM tokens
- **Topic Broadcasting** - Send to groups of subscribed users
- **Conditional Messaging** - Firebase condition-based targeting
- **User Segmentation** - Organize users by preferences and behavior
- **Smart Recommendations** - Auto-subscribe users to relevant topics

### 🛠️ Developer Experience
- **Interactive API Documentation** - Auto-generated Swagger/OpenAPI docs
- **Testing Suite** - Comprehensive test endpoints for development
- **Health Monitoring** - Service health checks and diagnostics
- **Beautiful Logging** - Structured, categorized logging with emojis
- **Error Handling** - Graceful error handling with detailed responses

## 🚀 Quick Start

### 1. Setup Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Firebase

1. Copy your Firebase service account key to `firebase-admin-key.json`
2. Update `.env` file with your configuration

### 4. Run the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8393 --reload

# Or use Python directly
python -m app.main
```

## 📚 API Documentation

Access the interactive API documentation at: `http://localhost:8393/docs`

### 📨 Core Notification APIs

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/v1/notifications/send-individual` | POST | Send notification to specific user |
| `/api/v1/notifications/send-topic` | POST | Send notification to topic subscribers |
| `/api/v1/notifications/send-multicast` | POST | Send notification to multiple tokens |
| `/api/v1/notifications/schedule` | POST | Schedule future notification |
| `/api/v1/notifications/scheduled` | GET | List scheduled notifications |
| `/api/v1/notifications/schedule/{job_id}` | DELETE | Cancel scheduled notification |

### 🎮 Game Template APIs

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/v1/notifications/game-templates/tournament-started` | POST | Tournament start notification |
| `/api/v1/notifications/game-templates/achievement-unlocked` | POST | Achievement unlock notification |
| `/api/v1/notifications/game-templates/friend-request` | POST | Friend request notification |
| `/api/v1/notifications/game-templates/daily-challenge` | POST | Daily challenge notification |

### 👥 User Management APIs

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/v1/users/register-token` | POST | Register user's FCM token |
| `/api/v1/users/token/{user_id}` | GET | Get user's token info |
| `/api/v1/users/token/{user_id}` | DELETE | Delete user's token |
| `/api/v1/users/topics/{user_id}` | GET | Get user's subscribed topics |
| `/api/v1/users/topics/{user_id}/subscribe` | POST | Subscribe user to topics |
| `/api/v1/users/topics/{user_id}/unsubscribe` | POST | Unsubscribe user from topics |
| `/api/v1/users/` | GET | List all registered users |

### 📢 Topic Management APIs

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/v1/notifications/topics/subscribe` | POST | Subscribe token to topic |
| `/api/v1/notifications/topics/unsubscribe` | POST | Unsubscribe token from topic |

### 🏆 Tournament APIs

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/v1/tournaments/schedule-notifications` | POST | Schedule all tournament notifications |

### 🧪 Testing APIs

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/v1/test/health` | GET | Health check endpoint |
| `/api/v1/test/send-test-notification` | POST | Send test notification |
| `/api/v1/test/send-topic-test` | POST | Send test topic notification |
| `/api/v1/test/validate-token` | POST | Validate FCM token |
| `/api/v1/test/firebase-status` | GET | Check Firebase connection |
| `/api/v1/test/quick-game-notification` | POST | Quick game notification templates |

## Notification Types

The system supports various notification types for the Snake Classic game:

- **Tournament Alerts** (`tournament`) - New tournaments, results
- **Social Notifications** (`social`) - Friend requests, challenges
- **Achievement Unlocks** (`achievement`) - New achievements earned
- **Daily Reminders** (`daily_reminder`) - Come back and play
- **Special Events** (`special_event`) - Limited-time challenges

## Scheduled Notifications

The backend includes an advanced scheduling system:

- Daily challenge reminders
- Tournament start/end notifications
- Weekly leaderboard updates
- Retention campaigns for inactive users

## 💡 Usage Examples

### Send Test Notification
```bash
curl -X POST "http://localhost:8393/api/v1/test/send-test-notification" \
  -H "Content-Type: application/json" \
  -d '{
    "fcm_token": "YOUR_FCM_TOKEN_HERE",
    "title": "🐍 Hello Snake Classic!",
    "body": "This is a test notification from the backend!",
    "route": "home"
  }'
```

### Register User Token
```bash
curl -X POST "http://localhost:8393/api/v1/users/register-token" \
  -H "Content-Type: application/json" \
  -d '{
    "fcm_token": "USER_FCM_TOKEN",
    "user_id": "user123",
    "username": "SnakePlayer",
    "platform": "flutter"
  }'
```

### Send Achievement Notification
```bash
curl -X POST "http://localhost:8393/api/v1/notifications/game-templates/achievement-unlocked" \
  -H "Content-Type: application/json" \
  -d '{
    "achievement_name": "Snake Master",
    "achievement_id": "snake_master_001",
    "fcm_token": "USER_FCM_TOKEN"
  }'
```

### Schedule Tournament Notifications
```bash
curl -X POST "http://localhost:8393/api/v1/tournaments/schedule-notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "tournament_name": "Snake Masters Championship",
    "tournament_id": "smc_2024_001",
    "start_time": "2024-12-01T18:00:00Z",
    "reminder_minutes": [60, 15, 5]
  }'
```

### Subscribe to Topics
```bash
curl -X POST "http://localhost:8393/api/v1/notifications/topics/subscribe" \
  -H "Content-Type: application/json" \
  -d '{
    "fcm_token": "USER_FCM_TOKEN",
    "topic": "tournaments"
  }'
```

## 📊 Topic Organization

The system organizes notifications into topics for efficient targeting:

- **`tournaments`** - General tournament announcements
- **`tournament_reminders`** - Tournament start reminders  
- **`daily_challenge`** - Daily challenge notifications
- **`social_updates`** - Social features and friend activities
- **`achievements`** - Achievement unlocks and milestones
- **`special_events`** - Limited-time events and promotions
- **`leaderboard_updates`** - Weekly/monthly leaderboard results
- **`retention_campaign`** - Re-engagement notifications for inactive users

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Firebase Configuration
FIREBASE_PROJECT_ID=your-firebase-project-id
GOOGLE_APPLICATION_CREDENTIALS=firebase-admin-key.json

# API Configuration  
API_HOST=127.0.0.1
API_PORT=8393
API_RELOAD=true

# Security
API_SECRET_KEY=your-secure-random-key

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Firebase Setup

1. **Create Firebase Project**: Go to [Firebase Console](https://console.firebase.google.com/)
2. **Enable FCM**: Enable Firebase Cloud Messaging in your project
3. **Generate Service Account Key**:
   - Go to Project Settings → Service Accounts
   - Click "Generate New Private Key"  
   - Save as `firebase-admin-key.json`
4. **Update Configuration**: Add your project ID to `.env`

## 🏗️ Development

### Project Structure

```
notification_backend/
├── app/
│   ├── core/           # Core configurations
│   ├── models/         # Pydantic models
│   ├── routes/         # API routes
│   ├── services/       # Business logic
│   └── main.py         # Application entry point
├── tests/              # Unit tests
├── requirements.txt    # Python dependencies
└── .env               # Environment variables
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app
```

## 🚀 Deployment

### 🐳 Docker Deployment (Recommended)

The fastest way to deploy this backend service is using Docker. This method ensures consistent environments and easy deployment.

#### Prerequisites
- Docker and Docker Compose installed
- Firebase service account key file
- Configured `.env` file

#### Step 1: Prepare Configuration Files

```bash
# Copy and configure your environment file
cp .env.example .env
# Edit .env with your configuration

# Place your Firebase service account key
# Save your firebase-admin-key.json in the project root
```

#### Step 2: Build and Run with Docker Compose

```bash
# Build and start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

The service will be available at `http://localhost:8393`

#### Step 3: Health Check

```bash
# Test the deployment
curl http://localhost:8393/api/v1/test/health

# Check Firebase connection
curl http://localhost:8393/api/v1/test/firebase-status
```

#### Docker Compose Configuration

```yaml
version: '3.8'

services:
  snake-notification-backend:
    build: .
    container_name: snake-notification-api
    ports:
      - "8393:8393"
    environment:
      - ENVIRONMENT=production
    env_file:
      - .env
    volumes:
      - ./firebase-admin-key.json:/app/firebase-admin-key.json:ro
    restart: unless-stopped
```

#### Production Docker Setup

For production deployment with SSL and reverse proxy:

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  snake-notification-backend:
    build: .
    environment:
      - ENVIRONMENT=production
      - EXTERNAL_API_URL=https://api.yourdomain.com
    env_file:
      - .env.production
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - snake-notification-backend
    restart: unless-stopped
```

#### Manual Docker Build

```bash
# Build the image
docker build -t snake-notification-backend .

# Run the container
docker run -d \
  --name snake-notification-api \
  -p 8393:8393 \
  --env-file .env \
  -v $(pwd)/firebase-admin-key.json:/app/firebase-admin-key.json:ro \
  snake-notification-backend

# View logs
docker logs -f snake-notification-api
```

### 🔧 Traditional Deployment

#### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Generate secure `API_SECRET_KEY`
- [ ] Use real Firebase service account key
- [ ] Set up proper logging and monitoring
- [ ] Configure rate limiting
- [ ] Set up SSL/TLS certificates
- [ ] Use production WSGI server (Gunicorn/uWSGI)
- [ ] Set up database for token persistence
- [ ] Configure backup and disaster recovery

#### Gunicorn Production Server

```bash
# Install Gunicorn
pip install gunicorn[standard]

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8393
```

### Environment-Specific Configuration

```bash
# Production
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8393
API_RELOAD=false
LOG_LEVEL=WARNING

# Staging  
ENVIRONMENT=staging
API_HOST=0.0.0.0
API_PORT=8393
API_RELOAD=false
LOG_LEVEL=INFO

# Development
ENVIRONMENT=development
API_HOST=127.0.0.1
API_PORT=8393
API_RELOAD=true
LOG_LEVEL=DEBUG
```

## 🔒 Security

### Best Practices

- **🔐 Firebase Credentials**: Never commit service account keys to version control
- **🔑 API Keys**: Use strong, randomly generated API secret keys
- **🌍 Environment Variables**: Store all sensitive data in environment variables
- **🚧 Rate Limiting**: Implement rate limiting to prevent API abuse
- **📝 Logging**: Log all requests but never log sensitive information
- **🔒 HTTPS**: Always use HTTPS in production
- **👤 Authentication**: Implement proper API authentication for production

### Security Headers

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Add security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com"])
app.add_middleware(CORSMiddleware, allow_origins=["https://yourdomain.com"])
```

## 📊 Monitoring & Analytics

### Health Monitoring

```bash
# Check service health
curl http://localhost:8393/health

# Check Firebase status  
curl http://localhost:8393/api/v1/test/firebase-status

# List scheduled jobs
curl http://localhost:8393/api/v1/notifications/scheduled
```

### Logging

The service uses structured logging with categories:

- **🔥 FIREBASE** - Firebase operations
- **📨 NOTIFICATION** - Notification sending
- **⏰ SCHEDULER** - Job scheduling  
- **👥 USER** - User management
- **🌐 NETWORK** - HTTP requests
- **⚠️ ERROR** - Error conditions

### Performance Metrics

- **Response Time**: API endpoint response times
- **Success Rate**: Notification delivery success rate  
- **Queue Length**: Scheduled job queue status
- **Error Rate**: Failed notification attempts
- **Token Validation**: FCM token validity rates

## 🧪 Testing

### Manual Testing

```bash
# Run the test suite
python test_server.py

# Individual endpoint tests
curl -X GET http://localhost:8393/health
curl -X POST http://localhost:8393/api/v1/test/send-test-notification
```

### Automated Testing

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=app tests/

# Integration tests
pytest tests/integration/
```

## 🔧 Troubleshooting

### Common Issues

**Firebase Authentication Errors**
```
Solution: Verify firebase-admin-key.json is valid and has correct permissions
```

**Port Already in Use**
```
Solution: Kill existing process or change PORT in .env
lsof -ti:8393 | xargs kill -9
```

**Missing Dependencies** 
```
Solution: Reinstall requirements
pip install -r requirements.txt
```

**Schedule Jobs Not Running**
```
Solution: Check scheduler service status in /health endpoint
```

## 📞 Support

For issues and questions:

1. Check the [interactive API docs](http://localhost:8393/docs)
2. Review the logs for error messages
3. Test with the provided testing endpoints
4. Verify Firebase configuration and credentials

## 📝 Changelog

### v1.0.0 (Current)
- ✅ Firebase Cloud Messaging integration
- ✅ Advanced scheduling with APScheduler  
- ✅ Game-specific notification templates
- ✅ User token management and topic subscriptions
- ✅ Comprehensive testing suite
- ✅ Interactive API documentation
- ✅ Production-ready configuration