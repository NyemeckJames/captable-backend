# Cap Table Management Backend

Backend for managing a company capitalization table: shareholders, share issuances,
PDF certificates and an audit trail. Built with FastAPI and PostgreSQL, structured
along Domain-Driven Design and Clean Architecture lines.

## Architecture

Three layers, with dependencies pointing inward only.

**Domain** holds the entities (`Company`, `Shareholder`, `ShareIssuance`,
`ShareCertificate`, `AuditEvent`), the value objects (`Money`, `Email`,
`ShareQuantity`) and the domain events. It imports nothing from the outside.

**Application** holds the use cases, split by intent: commands and their handlers on
the write side, queries and their handlers on the read side, DTOs at the boundary,
and ports declaring what the layer needs from the infrastructure (repositories, PDF
generation, event publishing, email).

**Infrastructure** implements those ports: SQLAlchemy repositories, JWT
authentication, WeasyPrint certificates, FastAPI routes. Replacing an adapter here
changes no caller above it.

The separation is not decoration. Cap table rules accumulate quickly (issuance
limits, share classes, ownership history, audit requirements), and keeping them in
the domain is what allows them to be tested without a database and changed without
touching transport.

```
captable-backend/
├── alembic/                    # Migrations: the schema is owned here, not by the app
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── domain/                 # Entities, value objects, domain events, exceptions
│   ├── application/            # Commands, queries, handlers, DTOs, ports, services
│   ├── infrastructure/         # API, auth, database, adapters
│   └── tests/                  # unit/ and integration/
├── scripts/seed_admin.py       # Bootstrap company and admin account
├── .github/workflows/ci.yml    # Byte-compile and test on every push
├── docker-compose.yml          # PostgreSQL, the API, and a one-shot test runner
└── Dockerfile
```

## Security controls

**Perimeter, not just role.** Every route exposing an issuance or a document derived
from one calls `CertificateGenerationService.authorize_issuance_access` before
reading anything. A shareholder reaches an issuance only through the profile that
belongs to them; an admin passes without a profile lookup. The check lives in the
service rather than in the routes so that adding a branch to a handler cannot
silently bypass it, and `AccessDeniedException` maps to 403 while a missing
resource maps to 404 — the two are never conflated.

**Deny by default.** `HTTPBearer(auto_error=False)` with an explicit 401, role
dependencies on every protected route, and inactive accounts rejected at
authentication.

**Closed surface in production.** `/docs`, `/redoc` and `/openapi.json` are served
only when `ENVIRONMENT` is not `production`. CORS origins come from configuration,
never a wildcard. `SECRET_KEY` and `DATABASE_URL` have no defaults: a missing secret
stops the process at boot instead of falling back to a known value.

**Nothing sensitive in the logs.** Standard library logging throughout, no `print`.
JWT payloads, user objects and passwords are never written out.

**No credentials created by starting the application.** The bootstrap admin is
created by `python -m scripts.seed_admin`, run knowingly against a chosen database.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Pango and its dependencies, required by WeasyPrint for PDF generation
  (`libpango-1.0-0 libpangoft2-1.0-0` on Debian/Ubuntu; the
  [GTK runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
  on Windows)

## Setup

Copy `.env.example` to `.env` and fill it in. Every value is required; the file is
never versioned.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python setup_db.py               # creates the captable and captable_test databases
alembic upgrade head             # applies the schema
python -m scripts.seed_admin     # creates the company and the admin account
python run.py                    # starts the API on http://127.0.0.1:8000
```

`setup.bat` chains the same steps on Windows.

## Tests

Against a local PostgreSQL, with `TEST_DATABASE_URL` pointing at it:

```bash
pytest -q
```

Or through the stack, which needs nothing installed and no port published on the
host:

```bash
docker compose --profile test run --rm tests
```

Unit tests cover the domain rules and the access rules with mocked ports.
Integration tests run against a real PostgreSQL rather than a substitute, because
the constraints being exercised belong to the schema as much as to the code.

The scope tests in `app/tests/integration/api/test_certificate_access.py` are
regression tests: they set up the exact state in which the perimeter used to be
bypassable and assert a 403.

On Windows, `conftest.py` switches asyncio to the selector event loop: asyncpg
cannot run on the Proactor loop Python selects there by default.

CI runs the byte-compilation and the full suite against PostgreSQL 16 on every push.

## Features

**Admin**: authentication, dashboard with shareholder overview and share totals, add
shareholders, issue shares, generate watermarked PDF certificates, read the audit
trail.

**Shareholder**: authentication, list of their own issuances, download of their own
certificates.

## Built with AI assistance, under review

This backend was written with heavy use of coding agents, on a deadline. Recording
what that involved is more useful than hiding it, so both halves are documented: what
the models produced, and what had to be caught.

### The prompts that shaped the architecture

Role framing measurably improves the output on architectural work, so each prompt
assigns one.

**1. Conceptual architecture, before any framework**

```
You are an expert in designing robust, scalable, and maintainable backend
architectures. You master fundamental software development principles such as:

- Rigorous application of SOLID principles and Clean Architecture
- Judicious use of Design Patterns adapted to business context
- Strict separation of responsibilities (Domain, Application, Infrastructure)
- Implementation of hexagonal architecture (ports and adapters) to ensure
  independence from frameworks or databases

Design the backend architecture of a Cap Table management application. Model this
architecture at the conceptual level, without framework implementation (no FastAPI
code for example), defining only entities, relationships, aggregates, business
rules, and logical structuring of the application.
```

Asking for the model without the framework is the point: it forces the domain to be
stated before FastAPI has a chance to shape it.

**2. Domain analysis against the functional requirements**

```
The business logic of a Cap Table is detailed in the provided business document.
Analyze this document carefully to understand the entities, their interactions, and
associated workflows.

Based on the functional requirements below, design a backend architecture aligned
with Domain-Driven Design, Clean Architecture, and hexagonal architecture
principles. This architecture must be modular, scalable and testable, leverage
patterns where they bring real value, and remain sufficiently simple and pragmatic,
consistent with the modest size of the project.
```

The last clause carries its weight: without it, models reliably over-engineer.

**3. Implementation, from the inside out**

```
You are a senior backend developer expert in FastAPI, specialized in technical
implementation of robust, testable, and scalable architectures.

Given the logical architecture, classes, and associations attached, implement it
concretely: create the project tree, generate the files with structuring code
(entities, value objects, persistence models, ports), and write each file
progressively, starting from domain foundations up to the highest layer.
```

### What review had to catch

Generated code is fast and confidently wrong in specific places. The defects that
mattered here, and how they were closed:

- **A perimeter bypass on certificates.** The download route short-circuited on an
  already generated certificate and returned the PDF without calling the service
  that checks ownership, so any authenticated shareholder could read another's
  certificate by changing the UUID in the URL. The metadata route checked nothing at
  all. Both now authorize before any branch, and two integration tests pin the
  behaviour.
- **Sensitive data written to stdout.** Decoded JWT payloads, user objects and, in
  the fixtures, plaintext passwords. All replaced by logging that carries none of it.
- **Privileged account creation at startup**, with the password read from settings on
  every boot. Moved to an explicit script.
- **Defaults that widen the surface**: `debug` on, documentation open, CORS hard-coded.
  Inverted, and driven by configuration.

The lesson the project actually taught: agents accelerate the parts that are
structurally repetitive, and they are least reliable exactly where the rules are
implicit — who may see what. That is where review time belongs, and where the tests
were written.
