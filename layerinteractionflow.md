# Workflows d'Interaction entre les Couches

Ce document détaille les flux de communication entre les trois couches architecturales (Infrastructure → Application → Domain) avec des exemples concrets issus du code.

## Architecture en Couches - Vue d'ensemble

```
┌─────────────────────────────────────────────────┐
│            INFRASTRUCTURE LAYER                  │
│  (FastAPI Routes, SQLAlchemy, JWT, Services)     │
└─────────────▲────────────┬──────────────────────┘
              │            │
              │ implements │ uses
              │            ▼
┌─────────────┴────────────────────────────────────┐
│            APPLICATION LAYER                     │
│  (Handlers, Commands, Queries, Ports, DTOs)      │
└─────────────▲────────────┬──────────────────────┘
              │            │
              │ orchestrates│ uses
              │            ▼
┌─────────────┴────────────────────────────────────┐
│               DOMAIN LAYER                       │
│  (Entities, Value Objects, Events, Exceptions)   │
└──────────────────────────────────────────────────┘
```

---

## Workflow 1: Authentification Utilisateur (Login)

### Flux complet: Infrastructure → Application → Domain → Infrastructure

```
[Client] → [FastAPI Route] → [JWT Handler] → [Repository] → [Domain Entity] → [Response]
```

### 1. Point d'entrée Infrastructure (`app/infrastructure/api/routes/auth.py:55-106`)

```python
@router.post("/api/token/")
async def login_for_access_token(
    payload: LoginRequest,
    request: Request,
    audit_service: AuditService = Depends(get_audit_service)
):
    # Infrastructure: Validation des credentials via JWT handler
    user = await authenticate_user(payload.email, payload.password)
    
    # Application: Service d'audit pour traçabilité
    await audit_service.log_event(
        action_type=AuditActionType.USER_LOGIN,
        user_id=user["id"],
        target_entity_type=AuditEntityType.USER,
        target_entity_id=user["id"],
        event_metadata={"email": user["username"]},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", "")
    )
    
    # Infrastructure: Génération du token JWT
    access_token = create_access_token(
        data={"sub": user["username"]}, 
        expires_delta=access_token_expires
    )
```

### 2. Service Infrastructure (`app/infrastructure/api/auth/jwt_handler.py:44-66`)

```python
async def authenticate_user(username: str, password: str) -> Optional[Dict]:
    async with AsyncSessionLocal() as session:
        # Infrastructure: Requête DB avec ORM SQLAlchemy
        result = await session.execute(
            select(UserModel)
            .options(joinedload(UserModel.shareholder_profile))
            .where(func.lower(UserModel.email) == username.lower())
        )
        db_user = result.scalar_one_or_none()
        
        # Infrastructure: Vérification du hash bcrypt
        if not verify_password(password, db_user.hashed_password):
            return None
        
        # Transformation en DTO pour retour
        return {
            "id": str(db_user.id),
            "username": db_user.email,
            "role": db_user.role,
            "name": profile.name if profile else "Admin User"
        }
```

### 3. Service Application (`app/application/services/audit_service.py:10-29`)

```python
class AuditService:
    async def log_event(
        self,
        action_type: AuditActionType,
        user_id: UUID,
        target_entity_type: AuditEntityType,
        target_entity_id: UUID,
        event_metadata: Optional[dict] = None,
        ip_address: str = "",
        user_agent: str = ""
    ) -> AuditEvent:
        # Domain: Création de l'entité AuditEvent
        event = AuditEvent.create(
            action_type=action_type,
            user_id=user_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            event_metadata=event_metadata,
            ip_address=ip_address,
            user_agent=user_agent
        )
        # Port: Utilisation du repository (interface)
        return await self.audit_repository.save(event)
```

### Points clés du workflow
- **Séparation des responsabilités** : FastAPI gère HTTP, JWT handler gère l'auth, Audit service gère la traçabilité
- **Domain isolation** : L'entité `AuditEvent` encapsule la logique métier
- **Port/Adapter** : `IAuditEventRepository` est une interface, `PostgresAuditRepository` l'implémente

---

## Workflow 2: Création d'une Émission d'Actions

### Flux complet avec validation métier complexe

```
[Admin User] → [POST /api/issuances] → [Command Handler] → [Domain Entity] → [Repositories] → [Event Publisher]
```

### 1. Route API (`app/infrastructure/api/routes/issuances.py:133-208`)

```python
@router.post("/api/issuances/")
async def create_issuance(
    request: CreateIssuanceRequest,
    current_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service)
):
    # Infrastructure: Injection des repositories
    company_repo = PostgresCompanyRepository(db)
    shareholder_repo = PostgresShareholderProfileRepository(db)
    issuance_repo = PostgresShareIssuanceRepository(db)
    event_publisher = InMemoryEventPublisher()
    
    # Application: Handler avec tous les ports nécessaires
    handler = CreateIssuanceHandler(
        company_repository=company_repo,
        shareholder_repository=shareholder_repo,
        issuance_repository=issuance_repo,
        event_publisher=event_publisher,
        email_service=ConsoleEmailService()
    )
    
    # Application: Command pattern
    command = CreateIssuanceCommand(
        shareholder_profile_id=request.shareholder_id,
        share_class_id=request.share_class_id,
        quantity=request.quantity,
        price_per_share=request.price_per_share,
        currency=request.currency,
        issue_date=request.issue_date
    )
    
    result = await handler.handle(command)
```

### 2. Command Handler (`app/application/handlers/command_handlers.py:147-206`)

```python
class CreateIssuanceHandler:
    async def handle(self, command) -> dict:
        # 1. Validation de la commande
        command.validate()
        
        # 2. Chargement de l'agrégat Company (racine)
        company = await self.company_repository.find_the_company()
        if not company:
            raise DomainException("Company not found")
        
        # 3. Validation de l'actionnaire
        shareholder = await self.shareholder_repository.find_by_id(
            command.shareholder_profile_id
        )
        
        # 4. Création des Value Objects
        quantity = ShareQuantity(command.quantity)
        price = Money(command.price_per_share, command.currency)
        
        # 5. LOGIQUE MÉTIER: Délégation à l'entité Company
        issuance = company.issue_shares(
            shareholder_profile_id=command.shareholder_profile_id,
            share_class_id=command.share_class_id,
            quantity=quantity,
            price_per_share=price,
            issue_date=command.issue_date
        )
        
        # 6. Persistance de l'état modifié
        await self.company_repository.save(company)
        saved_issuance = await self.issuance_repository.save(issuance)
        
        # 7. Notification par email
        await self.email_service.send_issuance_confirmation(
            to_email=shareholder_email,
            issuance=saved_issuance
        )
```

### 3. Entité Domain (`app/domain/entities/company.py:70-116`)

```python
class Company:
    def issue_shares(
        self, 
        shareholder_profile_id: UUID, 
        share_class_id: str, 
        quantity: ShareQuantity, 
        price_per_share: Money,
        issue_date: Optional[date] = None
    ) -> ShareIssuance:
        # 1. Validation de la classe d'actions
        share_class = next(
            (sc for sc in self.share_classes if sc.id == share_class_id), 
            None
        )
        if not share_class:
            raise DomainException(f"La classe d'actions '{share_class_id}' n'existe pas.")
        
        # 2. Vérification du plafond d'actions autorisées
        if not self.can_issue(quantity):
            raise DomainException(
                f"Impossible d'émettre {quantity}. "
                f"Cela dépasserait le plafond d'actions autorisées ({self.authorized_shares})."
            )
        
        # 3. Si applicable: vérifier le pool d'options
        if share_class.type == "option" and self.option_pool:
            if quantity.value > self.option_pool.available_shares.value:
                raise DomainException("Pas assez d'actions disponibles dans le pool d'options.")
            self.option_pool.allocated_shares = self.option_pool.allocated_shares.add(quantity)
        
        # 4. Créer l'émission d'actions
        issuance = ShareIssuance(
            shareholder_profile_id=shareholder_profile_id,
            share_class_id=share_class_id,
            quantity=quantity,
            price_per_share=price_per_share,
            issue_date=issue_date or date.today()
        )
        
        # 5. Mettre à jour l'état de la compagnie
        self.issued_shares = self.issued_shares.add(quantity)
        self.issuances.append(issuance)
        
        # 6. Émettre un événement de domaine
        ShareIssuanceCompleted(
            issuance_id=issuance.id,
            shareholder_profile_id=shareholder_profile_id,
            quantity=quantity.value,
            issue_date=issuance.issue_date
        ).publish()
        
        return issuance
```

### Points clés du workflow
- **Command Pattern** : Encapsulation de la requête dans une commande validée
- **Aggregate Root** : Company gère toute la logique métier d'émission
- **Domain Events** : Publication d'événements pour découplage
- **Value Objects** : Money et ShareQuantity garantissent l'intégrité

---

## Workflow 3: Génération de Certificat d'Actions (Async/Sync Mix)

### Flux hybride avec génération PDF synchrone

```
[User Request] → [Certificate Service] → [Async DB] → [Sync PDF] → [Async Save] → [Event]
```

### 1. Service Application (`app/application/services/certificate_service.py:34-83`)

```python
class CertificateGenerationService:
    async def generate_certificate_for_issuance(
        self, 
        issuance_id: UUID, 
        requesting_user_id: UUID, 
        requesting_user_role: str
    ) -> ShareCertificate:
        # 1. ASYNC: Récupérer et valider l'issuance (DB calls)
        issuance = await self._get_and_validate_issuance(
            issuance_id, requesting_user_id, requesting_user_role
        )
        
        # 2. ASYNC: Vérifier si un certificat existe déjà
        existing_certificate = await self.certificate_repository.find_by_issuance_id(
            issuance_id
        )
        if existing_certificate:
            return existing_certificate
        
        # 3. SYNC: Générer le certificat PDF (NO ASYNCIO!)
        # Appel DIRECT synchrone - pas d'asyncio
        certificate = self.pdf_generator.generate_share_certificate(issuance)
        
        # 4. ASYNC: Sauvegarder le certificat (DB call)
        saved_certificate = await self.certificate_repository.save(certificate)
        
        # 5. ASYNC: Publier l'événement (DB/messaging)
        event = CertificateGenerated(
            certificate_id=saved_certificate.id,
            issuance_id=issuance_id,
            storage_path=saved_certificate.storage_path
        )
        await self.event_publisher.publish(event)
        
        return saved_certificate
```

### 2. Validation avec contrôle d'accès (`app/application/services/certificate_service.py:85-116`)

```python
async def _get_and_validate_issuance(
    self, 
    issuance_id: UUID, 
    requesting_user_id: UUID, 
    requesting_user_role: str
) -> ShareIssuance:
    # ASYNC: Récupérer l'issuance
    issuance = await self.issuance_repository.find_by_id(issuance_id)
    if not issuance:
        raise DomainException(f"Issuance {issuance_id} not found")
    
    # Contrôle d'accès basé sur le rôle
    if requesting_user_role != "admin":
        # ASYNC: Pour un shareholder, vérifier l'appartenance
        profile = await self.profile_repository.find_by_id(
            issuance.shareholder_profile_id
        )
        
        if profile.user_id != requesting_user_id:
            raise DomainException(
                "Access denied. You can only generate certificates for your own shares."
            )
    
    return issuance
```

### 3. Service Infrastructure PDF (`app/infrastructure/services/pdf_service.py:22-50`)

```python
class WeasyPrintPdfGenerator(IPdfGenerator):
    def generate_share_certificate(self, issuance: ShareIssuance) -> ShareCertificate:
        """Version finale qui évite le conflit WeasyPrint"""
        
        # Create certificate entity
        certificate = ShareCertificate(
            share_issuance_id=issuance.id,
            watermark=f"Certificate No. {str(issuance.id)[:8].upper()}",
            generation_date=datetime.now()
        )
        
        # Generate HTML content
        html_content = self._generate_html_content(issuance, certificate)
        
        # Generate PDF filename
        filename = f"certificate_{certificate.id}.pdf"
        file_path = os.path.join(self.storage_path, filename)
        
        # Solution: Utiliser la méthode alternative qui évite le conflit
        success, error_msg = self._generate_pdf_alternative(
            html_content=html_content,
            output_path=file_path
        )
        
        if success:
            certificate.storage_path = file_path
            return certificate
        else:
            raise Exception(f"PDF generation failed: {error_msg}")
```

### Points clés du workflow
- **Mixed Async/Sync** : Gestion hybride pour compatibilité avec WeasyPrint
- **Access Control** : Validation basée sur les rôles et la propriété
- **Event Sourcing Ready** : Publication d'événements pour traçabilité

---

## Workflow 4: Dashboard Admin avec Agrégations

### Flux de lecture avec CQRS et agrégations

```
[Admin] → [GET /api/shareholders] → [Query Handler] → [Multiple Repos] → [DTO Assembly] → [Response]
```

### 1. Route API (`app/infrastructure/api/routes/shareholders.py:76-89`)

```python
@router.get("/api/shareholders/")
async def get_shareholders_dashboard(
    current_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    # Infrastructure: Injection de multiples repositories
    shareholder_repo = PostgresShareholderRepository(db)
    company_repo = PostgresCompanyRepository(db)
    issuance_repo = PostgresShareIssuanceRepository(db)
    
    # Application: Query handler avec tous les repos
    handler = GetAdminDashboardHandler(
        shareholder_repo, 
        company_repo, 
        issuance_repo
    )
    
    # Application: Query object (CQRS)
    query = GetAdminDashboardQuery()
    
    result = await handler.handle(query)
    return result
```

### 2. Query Handler (`app/application/handlers/query_handlers.py:25-76`)

```python
class GetAdminDashboardHandler:
    async def handle(self, query: GetAdminDashboardQuery) -> AdminDashboardDto:
        # 1. Récupération des données de la compagnie
        company = await self.company_repository.find_the_company()
        if not company:
            raise DomainException("Company not found")
        
        # 2. Récupération de tous les actionnaires
        shareholders = await self.shareholder_repository.find_all()
        
        # 3. Récupération de toutes les émissions pour calculs
        all_issuances = await self.issuance_repository.find_all()
        
        # 4. Construction des résumés avec agrégations
        shareholder_summaries = []
        for shareholder in shareholders:
            # Calcul du total des parts pour cet actionnaire
            shareholder_issuances = [
                issuance for issuance in all_issuances 
                if issuance.shareholder_profile_id == shareholder.id
            ]
            
            total_shares = sum(
                issuance.quantity.value 
                for issuance in shareholder_issuances
            )
            total_value = sum(
                issuance.total_value.amount 
                for issuance in shareholder_issuances
            )
            
            # Assembly du DTO
            shareholder_summaries.append(ShareholderSummaryDto(
                profile_id=shareholder.id,
                user_id=getattr(shareholder, "user_id", None),
                name=shareholder.name,
                email=shareholder.email.value,
                total_shares=total_shares,
                total_value=total_value
            ))
        
        # 5. Retour du DTO complet
        return AdminDashboardDto(
            shareholders=shareholder_summaries,
            total_issued_shares=company.issued_shares.value,
            total_authorized_shares=company.authorized_shares.value,
            company_name=company.name
        )
```

### 3. Repository avec jointures optimisées (`app/infrastructure/database/repositories/shareholder_repository.py:16-49`)

```python
class PostgresShareholderRepository(IShareholderRepository):
    async def get_all_with_total_shares(self):
        from sqlalchemy import func
        # Requête optimisée avec agrégation SQL
        result = await self.session.execute(
            select(
                ShareholderProfileModel.id,
                ShareholderProfileModel.name,
                ShareholderProfileModel.user_id,
                func.coalesce(
                    func.sum(ShareIssuanceModel.quantity), 0
                ).label("total_shares")
            )
            .outerjoin(
                ShareIssuanceModel, 
                ShareholderProfileModel.id == ShareIssuanceModel.shareholder_profile_id
            )
            .group_by(ShareholderProfileModel.id)
        )
        rows = result.all()
        
        # Enrichissement avec les emails des users
        shareholders = []
        for row in rows:
            shareholder_id, name, user_id, total_shares = row
            # Fetch user info avec eager loading
            user_result = await self.session.execute(
                select(ShareholderProfileModel)
                .options(selectinload(ShareholderProfileModel.user))
                .where(ShareholderProfileModel.id == shareholder_id)
            )
            db_shareholder = user_result.scalar_one_or_none()
            email = db_shareholder.user.email if db_shareholder and db_shareholder.user else ""
            
            shareholders.append({
                "id": shareholder_id,
                "name": name,
                "email": email,
                "total_shares": total_shares
            })
        return shareholders
```

### Points clés du workflow
- **CQRS Pattern** : Séparation lecture/écriture avec Query objects
- **DTO Assembly** : Transformation et agrégation dans le handler
- **SQL Optimization** : Jointures et agrégations au niveau DB
- **N+1 Prevention** : Eager loading avec selectinload

---

## Workflow 5: Gestion des Permissions et Multi-Tenancy

### Flux avec contrôle d'accès basé sur les rôles

```
[Shareholder] → [GET /api/issuances] → [Role Check] → [Filter by User] → [Limited Response]
```

### 1. Dependency Injection pour Auth (`app/infrastructure/api/auth/dependencies.py`)

```python
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Récupère l'utilisateur courant depuis le JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = await get_user_from_db(username)
    if user is None:
        raise credentials_exception
    
    return user

async def get_admin_user(current_user = Depends(get_current_user)):
    """Vérifie que l'utilisateur est admin"""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_shareholder_user(current_user = Depends(get_current_user)):
    """Autorise admin ou shareholder"""
    if current_user["role"] not in ["admin", "shareholder"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shareholder or admin access required"
        )
    return current_user
```

### 2. Handler avec logique conditionnelle (`app/application/handlers/query_handlers.py:82-130`)

```python
class GetIssuancesHandler:
    async def handle(self, user: dict) -> List[IssuanceSummaryDTO]:
        if user["role"] == "admin":
            # ADMIN: Voir TOUTES les émissions
            return await self._handle_admin_view()
        else:
            # SHAREHOLDER: Voir SEULEMENT ses propres émissions
            return await self._handle_shareholder_view(user["id"])
    
    async def _handle_admin_view(self) -> List[IssuanceSummaryDTO]:
        # Récupération de toutes les émissions
        all_issuances = await self.issuance_repository.find_all()
        
        # Enrichissement avec les infos des shareholders
        result = []
        for issuance in all_issuances:
            profile = await self.profile_repository.find_by_id(
                issuance.shareholder_profile_id
            )
            
            result.append(IssuanceSummaryDTO(
                id=issuance.id,
                shareholder_id=issuance.shareholder_profile_id,
                shareholder_name=profile.name if profile else "Unknown",
                share_class_id=issuance.share_class_id,
                quantity=issuance.quantity.value,
                price_per_share=float(issuance.price_per_share.amount),
                currency=issuance.price_per_share.currency,
                total_value=float(issuance.total_value.amount),
                issue_date=issuance.issue_date
            ))
        
        return result
    
    async def _handle_shareholder_view(self, user_id: str) -> List[IssuanceSummaryDTO]:
        # Récupération du profil de l'utilisateur
        user = await self.user_repository.find_by_id(UUID(user_id))
        if not user or not user.is_shareholder():
            return []
        
        # Récupération du profil shareholder
        profile = await self.profile_repository.find_by_user_id(UUID(user_id))
        if not profile:
            return []
        
        # Filtrage des émissions pour ce shareholder uniquement
        issuances = await self.issuance_repository.find_by_shareholder_profile_id(
            profile.id
        )
        
        # Transformation en DTOs
        return [
            IssuanceSummaryDTO(
                id=issuance.id,
                shareholder_id=issuance.shareholder_profile_id,
                shareholder_name=profile.name,
                share_class_id=issuance.share_class_id,
                quantity=issuance.quantity.value,
                price_per_share=float(issuance.price_per_share.amount),
                currency=issuance.price_per_share.currency,
                total_value=float(issuance.total_value.amount),
                issue_date=issuance.issue_date
            )
            for issuance in issuances
        ]
```

### 3. Route avec injection de dépendances (`app/infrastructure/api/routes/issuances.py:72-106`)

```python
@router.get("/api/issuances/")
async def get_issuances(
    # Dependency: Autorise admin ET shareholder
    current_user: dict = Depends(get_shareholder_user),
    db: AsyncSession = Depends(get_db)
):
    """Get issuances - all for admin, own for shareholder"""
    
    # Repositories
    issuance_repo = PostgresShareIssuanceRepository(db)
    profile_repo = PostgresShareholderProfileRepository(db)
    user_repo = PostgresUserRepository(db)
    
    # Handler avec les bons repositories
    handler = GetIssuancesHandler(
        issuance_repository=issuance_repo,
        profile_repository=profile_repo,
        user_repository=user_repo
    )
    
    try:
        # Le handler gère la logique selon le rôle
        result = await handler.handle(current_user)
        return result
        
    except DomainException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

### Points clés du workflow
- **Role-Based Access Control** : Filtrage au niveau handler
- **Dependency Injection** : FastAPI Depends pour l'auth
- **Data Isolation** : Les shareholders ne voient que leurs données
- **Flexible Authorization** : Même endpoint, résultats différents

---

## Principes Architecturaux Observés

### 1. Inversion de Dépendances
- Les couches supérieures définissent des interfaces (ports)
- L'infrastructure implémente ces interfaces
- Exemple: `IShareholderRepository` (port) → `PostgresShareholderRepository` (adapter)

### 2. Séparation des Préoccupations
- **Infrastructure** : Gestion HTTP, DB, Auth, Email
- **Application** : Orchestration, validation, transformation
- **Domain** : Logique métier pure, invariants, règles

### 3. CQRS (Command Query Responsibility Segregation)
- **Commands** : Modifient l'état (`CreateIssuanceCommand`)
- **Queries** : Lectures sans effet de bord (`GetAdminDashboardQuery`)
- **Handlers** : Orchestrent les opérations

### 4. Domain-Driven Design
- **Entities** : Company, ShareIssuance avec identité
- **Value Objects** : Money, ShareQuantity immutables
- **Aggregates** : Company comme racine d'agrégat
- **Domain Events** : ShareIssuanceCompleted, CertificateGenerated

### 5. Hexagonal Architecture
- **Ports** : Interfaces définies dans Application layer
- **Adapters** : Implémentations dans Infrastructure layer
- **Core** : Domain layer indépendant de tout framework

## Conclusion

Ces workflows démontrent une architecture robuste où :
- Chaque couche a une responsabilité claire
- Les dépendances pointent vers le domaine
- L'infrastructure est interchangeable
- La logique métier est protégée et testable
- Les patterns modernes (CQRS, DDD, Hexagonal) sont appliqués de manière pragmatique