from uuid import UUID, uuid4
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ShareCertificate:
    id: UUID = field(default_factory=uuid4)
    share_issuance_id: UUID = None
    watermark: str = ""
    storage_path: str = ""
    generation_date: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.share_issuance_id is None:
            raise ValueError("Share issuance ID is required")
