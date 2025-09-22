# Présentation Technique - Backend Cap Table Management

## 1. Domaine Métier

### Contexte d'affaires
Ce projet adresse la problématique de la gestion digitalisée des tables de capitalisation (cap tables) pour les entreprises. Une cap table est un document essentiel qui détaille la répartition du capital social d'une entreprise entre ses différents actionnaires.

### Problématiques métier résolues
- **Traçabilité** : Suivi complet de l'historique des émissions d'actions et des transferts
- **Conformité réglementaire** : Génération automatique de certificats d'actions et maintien d'une piste d'audit
- **Gestion multi-classes** : Support des actions ordinaires et préférentielles avec droits différenciés
- **Sécurité** : Authentification robuste et séparation des rôles (admin/shareholder)

## 2. Principes et Choix Architecturaux

### Architecture Hexagonale (Clean Architecture)
J'ai adopté une architecture en couches strictes pour garantir la maintenabilité et l'évolutivité :

```
app/
├── domain/           # Cœur métier pur (entités, value objects, événements)
├── application/      # Cas d'usage et orchestration (handlers, commands, queries)
├── infrastructure/   # Implémentations techniques (DB, API, services externes)
```

### Principes SOLID appliqués
- **Single Responsibility** : Chaque classe a une responsabilité unique (ex: `CreateIssuanceHandler` ne gère que la création d'émission)
- **Open/Closed** : Extension via interfaces sans modification du code existant
- **Dependency Inversion** : Les couches supérieures définissent des ports/interfaces que l'infrastructure implémente

### Domain-Driven Design (DDD)
- **Entités riches** : `Company`, `ShareIssuance` avec logique métier encapsulée
- **Value Objects** : `Money`, `ShareQuantity`, `Email` garantissant l'intégrité des données
- **Agrégats** : Company comme racine d'agrégat pour les émissions d'actions
- **Events** : `ShareIssuanceCompleted` pour la communication inter-bounded contexts

### CQRS Pattern
Séparation claire entre :
- **Commands** : Actions modifiant l'état (`CreateIssuanceCommand`)
- **Queries** : Lectures sans effet de bord (`GetIssuancesQuery`)
- **Handlers** : Orchestration avec injection de dépendances

## 3. Solution Technique Implémentée

### Stack Technologique
- **Framework** : FastAPI (Python 3.11+)
  - Performance native avec support async/await
  - Documentation OpenAPI automatique
  - Validation Pydantic intégrée
  
- **ORM** : SQLAlchemy 2.0
  - Support async natif avec asyncpg
  - Mapping objet-relationnel flexible
  - Sessions transactionnelles

- **Base de données** : PostgreSQL
  - ACID compliance pour l'intégrité financière
  - Support UUID natif pour les identifiants
  - Performances optimales pour les agrégations

- **Migrations** : Alembic
  - Versionning du schéma de base de données
  - Rollback possible en cas d'erreur
  - Migrations automatiques et manuelles

### Sécurité
- **Authentification JWT** : Tokens Bearer avec expiration configurable
- **Hachage bcrypt** : Protection des mots de passe
- **RBAC** : Role-Based Access Control (admin/shareholder)
- **Audit trail** : Enregistrement de toutes les actions sensibles

### Services Externes
- **PDF Generation** : WeasyPrint pour les certificats d'actions
- **Email** : Interface abstraite permettant multiple implémentations
- **Events** : Publisher/Subscriber in-memory (extensible vers RabbitMQ/Kafka)

## 4. Perspectives et Évolutivité

### Scalabilité horizontale
- Architecture stateless permettant le load balancing
- Possibilité de migration vers des microservices par bounded context
- Cache Redis pour les lectures fréquentes (dashboard)

### Intégrations futures
- **Blockchain** : Immutabilité des certificats via smart contracts
- **KYC/AML** : Intégration avec providers de vérification d'identité
- **Reporting** : Export vers Excel/PDF pour les assemblées générales
- **Multi-tenancy** : Support de plusieurs entreprises par instance

### Améliorations techniques
- Migration vers un event store (EventStore DB)
- Implémentation de saga patterns pour les transactions distribuées
- GraphQL pour les requêtes complexes côté frontend

## 5. Points Clés du Code

### 5.1 Domain Layer - Company Entity (`app/domain/entities/company.py`)
**Rôle** : Racine d'agrégat encapsulant toute la logique métier des émissions

```python
def issue_shares(...) -> ShareIssuance:
    # Validation des règles métier
    # Vérification du plafond d'actions autorisées
    # Création de l'émission
    # Publication d'événement domaine
```

### 5.2 Repository Pattern (`app/infrastructure/database/repositories/base_repository.py`)
**Rôle** : Abstraction de la persistance avec gestion d'erreurs centralisée

- Wrapper async pour toutes les opérations DB
- Rollback automatique en cas d'erreur
- Conversion entre modèles domaine et DB

### 5.3 Command Handlers (`app/application/handlers/command_handlers.py`)
**Rôle** : Orchestration des cas d'usage avec injection de dépendances

- Transaction boundaries claires
- Coordination entre multiples repositories
- Publication d'événements après succès

### 5.4 Value Objects (`app/domain/value_objects/money.py`)
**Rôle** : Garantir l'intégrité et l'immutabilité des données métier

- Validation à la construction
- Opérations métier (multiply, add)
- Type safety pour éviter les erreurs

### 5.5 Audit Service (`app/application/services/audit_service.py`)
**Rôle** : Traçabilité complète des actions utilisateurs

- Enregistrement automatique via décorateurs
- Métadonnées enrichies (IP, user-agent)
- Requêtes temporelles pour l'analyse

### 5.6 JWT Authentication (`app/infrastructure/api/auth/jwt_handler.py`)
**Rôle** : Sécurisation stateless de l'API

- Génération de tokens avec claims custom
- Middleware de vérification automatique
- Refresh token pattern implementable

### 5.7 Migration System (`alembic/versions/`)
**Rôle** : Évolution contrôlée du schéma de base de données

- Migrations atomiques et réversibles
- Support des contraintes et index
- Historique complet des changements

## 6. ORM et Gestion des Migrations

### SQLAlchemy 2.0
**Choix stratégique** : J'ai opté pour SQLAlchemy 2.0 pour ses capacités :
- **Async natif** : Performance optimale avec FastAPI
- **Type hints** : Meilleure intégration avec les outils modernes
- **Declarative mapping** : Code plus lisible et maintenable

### Architecture des modèles
```python
# Base declarative pour tous les modèles
Base = declarative_base()

# Modèles avec relations bidirectionnelles
class CompanyModel(Base):
    share_classes = relationship("ShareClassModel", back_populates="company")
```

### Alembic pour les migrations
**Configuration** :
- Auto-génération des migrations depuis les modèles SQLAlchemy
- Environnement async compatible avec l'application
- Scripts de migration versionnés dans Git

**Workflow** :
1. Modification des modèles SQLAlchemy
2. `alembic revision --autogenerate -m "description"`
3. Révision manuelle du script généré
4. `alembic upgrade head` en développement
5. Déploiement atomique en production

### Patterns de persistance
- **Unit of Work** : Sessions async avec commit/rollback automatiques
- **Identity Map** : Cache de session pour éviter les requêtes redondantes
- **Lazy Loading** : Chargement à la demande des relations

## 7. Guide de Démarrage et Commandes

### Prérequis
- **Python 3.11+** : Version moderne avec support complet de l'async
- **PostgreSQL 14+** : Base de données relationnelle
- **pip** : Gestionnaire de paquets Python

### Installation et Configuration

#### 1. Configuration initiale (Windows)
```batch
# Script automatisé pour Windows
setup.bat
```
Ce script effectue automatiquement :
- Création de l'environnement virtuel Python
- Installation des dépendances (requirements.txt)
- Création du fichier .env depuis .env.example
- Création des bases de données (captable, captable_test)
- Exécution des migrations Alembic
- Démarrage du serveur

#### 2. Configuration manuelle (Linux/Mac)
```bash
# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos paramètres

# Créer les bases de données
python setup_db.py

# Exécuter les migrations
alembic upgrade head
```

### Démarrage du Serveur

#### Option 1 : Script Python avec configuration
```bash
python run.py
```
Ce script offre :
- Chargement automatique des variables d'environnement
- Configuration du host/port depuis .env
- Mode debug avec hot-reload automatique
- Affichage des URLs de documentation
- Gestion propre des interruptions (Ctrl+C)

#### Option 2 : Uvicorn directement
```bash
# Mode développement avec hot-reload
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Mode production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Avec logs détaillés
uvicorn app.main:app --reload --log-level debug
```

**Paramètres Uvicorn importants** :
- `--reload` : Rechargement automatique lors des modifications de code
- `--host` : Interface réseau (0.0.0.0 pour toutes les interfaces)
- `--port` : Port d'écoute (défaut: 8000)
- `--workers` : Nombre de processus workers (production)
- `--log-level` : Niveau de log (critical, error, warning, info, debug, trace)

### Gestion des Migrations

```bash
# Créer une nouvelle migration automatique
alembic revision --autogenerate -m "Description du changement"

# Créer une migration manuelle
alembic revision -m "Description"

# Appliquer toutes les migrations
alembic upgrade head

# Revenir à une version spécifique
alembic downgrade <revision_id>

# Voir l'historique des migrations
alembic history

# Voir la migration actuelle
alembic current
```

### Tests

```bash
# Exécuter tous les tests
pytest

# Tests avec couverture
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest app/tests/unit/
pytest app/tests/integration/

# Tests en mode verbose
pytest -v

# Tests avec print statements
pytest -s
```

### Docker

```bash
# Construction de l'image
docker build -t captable-backend .

# Démarrage du conteneur
docker run -p 8000:8000 --env-file .env captable-backend

# Avec volume pour les certificats
docker run -p 8000:8000 -v $(pwd)/certificates:/app/certificates --env-file .env captable-backend
```

### URLs Importantes

Une fois le serveur démarré :
- **API** : http://localhost:8000
- **Documentation Swagger** : http://localhost:8000/docs
- **Documentation ReDoc** : http://localhost:8000/redoc
- **Health Check** : http://localhost:8000/health

### Variables d'Environnement Critiques

```env
# Sécurité JWT
SECRET_KEY=<générer-avec-openssl-rand-hex-32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Base de données
DATABASE_URL=postgresql://user:password@localhost:5432/captable
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=root

# Configuration initiale
ADMIN_EMAIL=admin@captable.com
ADMIN_PASSWORD=<mot-de-passe-fort>
COMPANY_NAME=TechStartup SAS
COMPANY_AUTHORIZED_SHARES=1000000

# Mode debug (désactiver en production)
DEBUG=False
```

### Commandes de Maintenance

```bash
# Nettoyer les migrations orphelines
alembic stamp head

# Vérifier la cohérence de la base
python -c "from app.infrastructure.database.connection import async_engine; import asyncio; asyncio.run(async_engine.dispose())"

# Générer un nouveau SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Créer un utilisateur admin via CLI
python -c "from app.main import initialize_default_data; import asyncio; asyncio.run(initialize_default_data())"
```

## 8. Éléments Additionnels Non Mentionnés

### Monitoring et Observabilité
- **Structured Logging** : Utilisation du module logging Python avec formatage JSON
- **Request ID** : Traçage des requêtes via middleware pour debugging
- **Performance Metrics** : Temps de réponse des endpoints critiques

### Optimisations de Performance
- **Connection Pooling** : Configuration SQLAlchemy avec pool_size et max_overflow
- **Async/Await** : Utilisation systématique pour les I/O operations
- **Indexes** : Sur email (users), shareholder_profile_id (issuances)

### Documentation Technique
- **OpenAPI 3.0** : Génération automatique avec FastAPI
- **Exemples de requêtes** : Dans chaque endpoint pour faciliter l'intégration
- **Schemas Pydantic** : Auto-documentation des modèles de données

### Sécurité Avancée
- **CORS Configuration** : Restriction aux origines autorisées
- **Rate Limiting** : Préparé pour intégration avec Redis
- **SQL Injection Protection** : Via SQLAlchemy ORM et paramètres bindés

### Gestion d'Erreurs
- **Domain Exceptions** : Hiérarchie claire d'exceptions métier
- **HTTP Exception Handlers** : Réponses standardisées pour les erreurs
- **Rollback Automatique** : En cas d'erreur dans les transactions

### CI/CD Ready
- **pytest.ini** : Configuration des tests automatisés
- **Dockerfile** : Containerisation pour déploiement
- **Requirements.txt** : Versions figées pour reproductibilité

## Conclusion

Ce backend représente une architecture moderne et robuste, prête pour la production et l'évolution. Les choix techniques garantissent :
- **Maintenabilité** via la séparation des préoccupations
- **Testabilité** grâce aux abstractions et injections
- **Performance** avec l'async et les optimisations DB
- **Sécurité** par design avec audit et authentification
- **Évolutivité** permettant l'ajout de nouvelles fonctionnalités sans refactoring majeur
- **Opérabilité** avec des scripts de démarrage et une configuration simple

Le projet démontre une maîtrise des patterns architecturaux modernes et des bonnes pratiques de développement backend, tout en restant pragmatique dans les choix d'implémentation.