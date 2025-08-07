from dataclasses import dataclass
from uuid import UUID
from app.application.commands.base import Query


@dataclass
class GetAdminDashboardQuery(Query):
    pass




@dataclass
class GetAllIssuancesQuery(Query):
    pass

@dataclass
class GetAllShareholdersQuery(Query):
    pass


@dataclass
class GetShareholderIssuancesQuery(Query):
    user_id: UUID
