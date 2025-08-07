# Cap Table Management Backend

## Overview

This backend application is designed for cap table (capitalization table) management, built with a robust architecture inspired by Domain-Driven Design (DDD) and Clean Architecture principles. The project demonstrates enterprise-grade architectural patterns while maintaining simplicity and pragmatism appropriate for the scope.

## Technical Approach and Architectural Decisions

### Architecture Philosophy

The architecture is built at the intersection of four key realities:
- **Technological Reality**: AI acceleration enabling rapid development of complex architectures
- **Business Reality**: Financial domain complexity requiring robust domain modeling
- **Technical Assessment Reality**: Demonstrating advanced technical skills within time constraints  
- **Product Reality**: Anticipating inevitable feature evolution and scalability needs

### Key Architectural Principles

**Domain-Driven Design (DDD) & Clean Architecture**
- Strong separation of concerns across Domain, Application, and Infrastructure layers
- Hexagonal architecture (ports and adapters) ensuring framework independence
- CQRS pattern implementation for clear read/write separation

**Strategic Benefits:**
- **Business Complexity Anticipation**: Cap table management involves complex business rules (emissions, history tracking, shareholder profiles, audits). Modular architecture isolates these rules for independent evolution.
- **Extension Capabilities**: Decoupled layers facilitate easy feature additions such as:
  - Multi-tenancy for managing multiple companies
  - Validation workflows and electronic signatures
  - Advanced reporting and custom PDF/Excel exports
- **Technical Excellence**: Demonstrates mastery of modern software architecture, comprehensive testing strategies, and development best practices.

## Project Structure

```
captable-backend/
├── alembic/                     # Alembic migration scripts
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── application/            # Application layer (CQRS)
│   │   ├── commands/           # Business commands (write operations)
│   │   ├── queries/            # Queries (read operations)
│   │   ├── handlers/           # Command & query handlers
│   │   ├── dtos/               # Data transfer objects
│   │   ├── services/           # Business services
│   │   └── ports/              # Interfaces (secondary ports)
│   ├── domain/                 # Domain layer (DDD)
│   │   ├── entities/           # Business entities (User, Shareholder, etc.)
│   │   ├── events/             # Domain events
│   │   └── value_objects/      # Value objects (Email, Money, etc.)
│   ├── infrastructure/         # Infrastructure layer (adapters, implementations)
│   │   ├── api/                # Routes, middlewares, authentication
│   │   │   ├── routes/         # REST endpoints (FastAPI routers)
│   │   │   └── auth/           # JWT management, dependencies
│   │   ├── config/             # Application configuration (settings, .env)
│   │   ├── database/           # Database connection, models, repositories
│   │   │   └── repositories/   # Repository implementations
│   │   └── services/           # Concrete implementations (PDF, email, etc.)
│   └── tests/                  # Unit and integration tests
│       ├── unit/
│       └── integration/
├── run.py                      # Application launcher
├── setup_db.py                 # Database setup script
├── setup.bat                   # Automated installation script (Windows)
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic configuration
├── pytest.ini                 # Pytest configuration
├── docker-compose.yml          # Docker stack (optional)
└── Dockerfile                  # Application Docker image
```

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** 
  - Default configuration: username `postgres`, password `root`, default port (5432)
  - Update the `.env` file if your PostgreSQL configuration differs
- **Windows Environment** (project developed on Windows)
- **GTK Runtime** (required for WeasyPrint PDF generation)
  - Download from: [GTK for Windows Runtime Environment](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe)

## Local Setup Instructions

### Option 1: Automated Setup (Recommended)

Execute the automated setup script:
```bash
setup.bat
```

### Option 2: Manual Setup

If the automated script doesn't work, follow these steps (inside the backend workspace root):

1. **Create and activate virtual environment:**
```bash
python -m venv venv
venv\Scripts\activate
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up databases:**
```bash
python setup_db.py
```

4. **Run database migrations:**
```bash
alembic upgrade head
```

5. **Launch the application:**
```bash
python run.py
```

## AI Tools Used

The following AI tools significantly accelerated the development process:

- **ChatGPT** - Architecture design and code generation
- **Cline (VS Code Extension) & GPT-4.1** - Primary AI coding agent
- **GitHub Copilot** - Code completion and suggestions
- **Gemini 2.5 Pro** - Complex problem solving and optimization
- **Claude Sonnet 4** - Documentation and architectural review

## Key Accelerating Prompts

*Note: LLMs perform significantly better when engaged in role-playing scenarios, as demonstrated in the prompts below.*

### 1. Architecture Design Expert Role-Playing Prompt

```
You are an expert in designing robust, scalable, and maintainable backend architectures. You master fundamental software development principles such as:

- Rigorous application of SOLID principles and Clean Architecture
- Judicious use of Design Patterns (creational, structural, behavioral) adapted to business context
- Strict separation of responsibilities (Domain, Application, Infrastructure) for better readability and evolution
- Implementation of hexagonal architecture (ports and adapters) to ensure independence from frameworks or databases

🎯 In this context, your role is to design the backend architecture of a Cap Table management application. The objective is to model this architecture at the conceptual level, without framework implementation (no FastAPI code for example), defining only entities, relationships, aggregates, business rules, and logical structuring of the application.
```

### 2. Business Domain Analysis Prompt

```
The business logic of a Cap Table (capitalization table) is detailed in the provided business document. Analyze this document carefully to understand the entities, their interactions, and associated workflows.

✨ Based on the functional requirements below, design a backend architecture aligned with Domain-Driven Design (DDD), Clean Architecture, and hexagonal architecture principles.

This architecture must:
- Be modular, scalable, and testable
- Leverage good patterns where they bring real value
- Remain sufficiently simple and pragmatic, consistent with the modest size of the project

📋 Functional Requirements (User Stories)
[Detailed user stories for Admin and Shareholder roles...]
```

### 3. Technical Implementation Prompt

```
You are a senior backend developer expert in FastAPI, specialized in technical implementation of robust, testable, and scalable architectures based on the best architectural principles.

Given the logical architecture, classes, and associations of a Cap Table application attached, you will now:

🛠️ Implement this architecture concretely in several steps:
- Create the complete associated project tree structure in the active directory
- Generate necessary files with structuring code: business entities, value objects, persistence models, service interfaces (ports), etc.
- Write each file progressively, starting from domain foundations up to the highest layer

The objective is to build a solid, clear, extensible project foundation.
```

## Features Implemented

### Admin Features
- Authentication and secure login
- Dashboard with shareholder overview and total share counts
- Shareholding distribution visualization (pie chart)
- Add new shareholders (name, email)
- Initiate share emission processes
- Generate watermarked PDF certificates for emissions

### Shareholder Features  
- Authentication and secure login
- Personal dashboard with share holdings information
- View all individual share emissions
- Download associated PDF certificates

## Testing

The application includes comprehensive testing coverage:
- **Unit Tests**: Domain logic and business rules validation
- **Integration Tests**: API endpoints and database interactions

Run tests with:
```bash
pytest
```

## Development Notes

This project represents a strategic approach balancing:
- **Rapid AI-Assisted Development**: Leveraging modern AI tools to implement complex architectures efficiently
- **Enterprise Architecture Patterns**: Demonstrating mastery of DDD, Clean Architecture, and hexagonal architecture
- **Business Domain Complexity**: Proper modeling of financial domain complexities inherent in cap table management
- **Future-Proof Design**: Architecture designed for inevitable feature expansion and scaling requirements

The combination of AI acceleration with solid architectural principles enables the delivery of enterprise-grade solutions within compressed timeframes while maintaining code quality and system maintainability.












