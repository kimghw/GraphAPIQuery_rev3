# Microsoft Graph API Mail Collection System v1.0.0

A comprehensive system for collecting and managing Microsoft 365 email data using Microsoft Graph API with OAuth 2.0 authentication.

## 🚀 Features

### Authentication & Account Management
- **Multi-user Support**: Manage multiple Microsoft 365 accounts
- **OAuth 2.0 Flows**: Support for Authorization Code Flow and Device Code Flow
- **Token Management**: Automatic token refresh and validation
- **Scope Management**: Dynamic permission scope handling

### Mail Operations
- **Query Mail**: Filter messages by date, sender, read status, importance
- **Send Mail**: Send emails with HTML or text content
- **Delta Synchronization**: Incremental sync using Microsoft Graph delta links
- **Real-time Notifications**: Webhook support for new message alerts

### Data Management
- **Query History**: Track and audit all mail queries
- **External API Integration**: Forward new messages to external systems
- **Database Storage**: Persistent storage for accounts, tokens, and mail data
- **Structured Logging**: Comprehensive audit trails

## 🏗️ Architecture

This project follows **Clean Architecture** principles with a **Ports and Adapters** pattern:

```
├── core/                   # Business logic (domain-driven)
│   ├── domain/            # Entities and domain models
│   └── usecases/          # Business use cases and ports
├── adapters/              # External interfaces
│   ├── api/               # FastAPI REST endpoints
│   ├── cli/               # Command-line interface
│   ├── db/                # Database adapters
│   └── external/          # External service clients
├── config/                # Configuration management
├── tests/                 # Test suites
└── main.py               # Application entry point
```

### Key Design Principles
- **Core Independence**: Business logic has no external dependencies
- **Interface Segregation**: Thin adapters for different entry points
- **Dependency Inversion**: Core depends only on abstractions
- **Single Responsibility**: Each component has a focused purpose

## 🛠️ Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Language** | Python | 3.11+ | Core runtime |
| **Web Framework** | FastAPI | 0.104.1 | REST API server |
| **CLI Framework** | Typer | 0.9.0 | Command-line interface |
| **Database** | SQLite/PostgreSQL | - | Data persistence |
| **ORM** | SQLAlchemy | 2.0.23 | Database abstraction |
| **HTTP Client** | HTTPX | 0.25.2 | Async HTTP calls |
| **Authentication** | MSAL | 1.25.0 | Microsoft OAuth |
| **Validation** | Pydantic | 2.5.0 | Data validation |
| **Logging** | Structlog | 23.2.0 | Structured logging |
| **Testing** | Pytest | 7.4.3 | Test framework |

## 📋 Prerequisites

- Python 3.11 or higher
- Microsoft Azure AD application registration
- Microsoft 365 account with appropriate permissions

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd GraphAPIQuery_rev3

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```env
# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=sqlite:///./graphapi.db

# Microsoft Graph API
MICROSOFT_TENANT_ID=your-tenant-id
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_REDIRECT_URI=http://localhost:8000/auth/callback

# External API (optional)
EXTERNAL_API_ENDPOINT=http://localhost:9000/api/messages
EXTERNAL_API_TIMEOUT=30
EXTERNAL_API_RETRY_ATTEMPTS=3

# Server
HOST=127.0.0.1
PORT=8000
```

### 3. Initialize Database

```bash
# Using CLI
python -m adapters.cli.main init

# Or using Python
python -c "from adapters.db.database import migrate_database_sync; from config.settings import get_settings; migrate_database_sync(get_settings())"
```

### 4. Start the Application

#### Web API Server
```bash
# Development mode
python main.py

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### CLI Interface
```bash
# Show help
python -m adapters.cli.main --help

# Check system status
python -m adapters.cli.main status

# Authentication commands
python -m adapters.cli.main auth --help

# Mail commands
python -m adapters.cli.main mail --help
```

## 📖 Usage Examples

### Authentication

#### Create Account (Authorization Code Flow)
```bash
python -m adapters.cli.main auth create \
  --email user@example.com \
  --tenant-id your-tenant-id \
  --client-id your-client-id \
  --flow authorization_code \
  --client-secret your-client-secret \
  --redirect-uri http://localhost:8000/auth/callback
```

#### Create Account (Device Code Flow)
```bash
python -m adapters.cli.main auth create \
  --email user@example.com \
  --tenant-id your-tenant-id \
  --client-id your-client-id \
  --flow device_code
```

#### Authenticate Account
```bash
python -m adapters.cli.main auth authenticate --email user@example.com
```

#### List Accounts
```bash
python -m adapters.cli.main auth list
```

### Mail Operations

#### Query Recent Mail
```bash
python -m adapters.cli.main mail query \
  --days 7 \
  --limit 10 \
  --unread-only
```

#### Send Mail
```bash
python -m adapters.cli.main mail send \
  --to recipient@example.com \
  --subject "Test Subject" \
  --body "Test message body" \
  --body-type text
```

#### Delta Synchronization
```bash
python -m adapters.cli.main mail sync --folder inbox
```

### API Usage

#### Create Account via API
```bash
curl -X POST "http://localhost:8000/auth/accounts" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "tenant_id": "your-tenant-id",
    "client_id": "your-client-id",
    "authentication_flow": "authorization_code",
    "scopes": ["offline_access", "User.Read", "Mail.Read", "Mail.Send"],
    "client_secret": "your-client-secret",
    "redirect_uri": "http://localhost:8000/auth/callback"
  }'
```

#### Query Mail via API
```bash
curl -X GET "http://localhost:8000/mail/query?days=7&limit=10" \
  -H "Accept: application/json"
```

## 🔧 Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=adapters

# Run specific test file
pytest tests/test_auth_usecases.py

# Run with verbose output
pytest -v
```

### Code Quality
```bash
# Format code
black .

# Sort imports
isort .

# Type checking (if mypy is installed)
mypy core/ adapters/
```

### Database Management

#### Reset Database
```bash
rm graphapi.db
python -m adapters.cli.main init
```

#### Backup Database
```bash
cp graphapi.db graphapi_backup_$(date +%Y%m%d).db
```

## 📊 API Documentation

When running in development mode, API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🔐 Security Considerations

### OAuth 2.0 Security
- Uses PKCE (Proof Key for Code Exchange) for enhanced security
- Tokens are stored securely in the database
- Automatic token refresh prevents expired token issues
- Scope validation ensures minimal required permissions

### Data Protection
- Structured logging for audit trails
- No sensitive data in logs
- Database encryption at rest (when using appropriate database)
- HTTPS enforcement in production

### Best Practices
- Regular token rotation
- Scope minimization
- Webhook signature verification
- Rate limiting compliance

## 🚀 Deployment

### Production Environment

1. **Environment Variables**
```env
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host:port/db
```

2. **Database Migration**
```bash
python -c "from adapters.db.database import migrate_database_sync; from config.settings import get_settings; migrate_database_sync(get_settings())"
```

3. **Start Application**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow Clean Architecture principles
- Write comprehensive tests
- Use type hints throughout
- Follow PEP 8 style guidelines
- Add docstrings to all public methods

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

#### Authentication Errors
- Verify Azure AD application configuration
- Check redirect URI matches exactly
- Ensure required permissions are granted

#### Database Issues
- Check database file permissions
- Verify SQLite/PostgreSQL installation
- Run database migration

#### API Rate Limits
- Microsoft Graph API has rate limits
- Implement exponential backoff
- Monitor usage in Azure portal

### Getting Help
- Check the [API documentation](http://localhost:8000/docs)
- Review test files for usage examples
- Open an issue for bugs or feature requests

## 🔄 Changelog

### v1.0.0 (2025-01-01)
- Initial release
- Multi-user authentication support
- Mail query and send functionality
- Delta synchronization
- Webhook support
- CLI and API interfaces
- Comprehensive test suite

---

**Built with ❤️ using Clean Architecture principles**
