# Cap Table Management Backend

A robust backend application for managing company capitalization tables (cap tables) built with **FastAPI**, implementing **Clean Architecture**, **Domain-Driven Design (DDD)**, and **CQRS** patterns.

## 🏗️ Architecture Overview

This application follows the principles of Clean Architecture with three main layers:

1. **Domain Layer**: Contains the core business logic and rules
2. **Application Layer**: Orchestrates use cases and coordinates between domain and infrastructure
3. **Infrastructure Layer**: Handles external concerns like databases, APIs, and services

### Key Patterns Implemented

- **Clean Architecture**: Separation of concerns with dependency inversion
- **Domain-Driven Design (DDD)**: Rich domain models with aggregates and value objects
- **CQRS**: Separate models for read and write operations
- **Event-Driven Architecture**: Domain events for decoupled side effects

## 🚀 Features

- **JWT Authentication**: Secure token-based authentication
- **Shareholders Management**: Create and manage company shareholders
- **Share Issuances**: Issue shares to shareholders with validation
- **PDF Certificate Generation**: Automatic generation of share certificates
- **Admin Dashboard**: Overview of all shareholders and their holdings
- **Shareholder Dashboard**: Individual shareholder view of their shares
- **Role-based Access Control**: Admin and shareholder roles with appropriate permissions

## 📋 API Endpoints

### Authentication
- `POST /api/token/` - Login and get access token

### Shareholders
- `GET /api/shareholders/` - Get admin dashboard (Admin only)
- `POST /api/shareholders/` - Create new shareholder (Admin only)

### Share Issuances
- `GET /api/issuances/` - Get issuances (all for admin, own for shareholders)
- `POST /api/issuances/` - Create new share issuance (Admin only)
- `GET /api/issuances/{id}/certificate/` - Generate and download PDF certificate

## 🛠️ Technology Stack

- **FastAPI**: Modern, high-performance web framework
- **PostgreSQL**: Robust relational database
- **SQLAlchemy**: Async ORM with Alembic migrations
- **Pydantic**: Data validation and serialization
- **WeasyPrint**: PDF generation
- **JWT**: Secure authentication
- **Docker**: Containerization for easy deployment

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (if running locally without Docker)

### Using Docker (Recommended)

1. **Clone the repository**
```bash
git clone <repository-url>
cd captable-backend
```

2. **Start the application**
```bash
docker-compose up --build
```

3. **The API will be available at:**
- Main API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Local Development

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Set up PostgreSQL database**
```bash
# Create database
createdb captable_db
```

3. **Set environment variables**
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/captable_db"
export SECRET_KEY="your-secret-key-here"
```

4. **Run migrations**
```bash
alembic upgrade head
```

5. **Start the application**
```bash
uvicorn app.main:app --reload
```

## 🧪 Testing

### Test Users
The application comes with predefined test users:

**Admin User:**
- Email: `admin@captable.com`
- Password: `admin123`
- Role: `admin`

**Shareholder User:**
- Email: `shareholder@captable.com`
- Password: `shareholder123`
- Role: `shareholder`

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest app/tests/unit/domain/test_company.py
```

### API Testing with curl

1. **Login and get token:**
```bash
curl -X POST "http://localhost:8000/api/token/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@captable.com&password=admin123"
```

2. **Create a shareholder:**
```bash
curl -X POST "http://localhost:8000/api/shareholders/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Investor", "email": "john@investor.com", "role": "investor"}'
```

3. **Create share issuance:**
```bash
curl -X POST "http://localhost:8000/api/issuances/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shareholder_id": "SHAREHOLDER_UUID",
    "share_class_id": "ordinary",
    "quantity": 1000,
    "price_per_share": 10.50,
    "currency": "EUR"
  }'
```

## 📁 Project Structure

```
captable-backend/
├── app/
│   ├── domain/              # Core business logic
│   │   ├── entities/        # Domain entities
│   │   ├── value_objects/   # Value objects
│   │   ├── events/          # Domain events
│   │   └── exceptions.py    # Domain exceptions
│   ├── application/         # Use cases and application logic
│   │   ├── commands/        # Command objects
│   │   ├── queries/         # Query objects
│   │   ├── handlers/        # Command/Query handlers
│   │   ├── ports/           # Interface definitions
│   │   └── dtos/            # Data transfer objects
│   ├── infrastructure/      # External concerns
│   │   ├── database/        # Database repositories
│   │   ├── api/             # REST API routes
│   │   ├── services/        # External services
│   │   └── config/          # Configuration
│   └── tests/               # Test suite
├── alembic/                 # Database migrations
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## 🔧 Configuration

Key configuration options in `app/infrastructure/config/settings.py`:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing key
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time
- `DEBUG`: Enable debug mode

## 📈 Domain Model

### Key Entities

- **Company**: Aggregate root managing share classes and authorized shares
- **Shareholder**: Individual or entity holding shares
- **ShareIssuance**: Record of shares issued to a shareholder
- **ShareCertificate**: PDF certificate for share ownership

### Value Objects

- **Email**: Validated email address
- **Money**: Amount with currency
- **ShareQuantity**: Number of shares with validation

### Business Rules

- Cannot issue more shares than authorized
- Share prices must be positive
- Email addresses must be unique
- Only admins can create shareholders and issuances
- Shareholders can only view their own data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
