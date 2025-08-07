# app/application/ports/pdf_generator.py (VERSION SYNCHRONE)
from abc import ABC, abstractmethod
from app.domain.entities.share_issuance import ShareIssuance
from app.domain.entities.share_certificate import ShareCertificate


class IPdfGenerator(ABC):
    @abstractmethod
    def generate_share_certificate(self, issuance: ShareIssuance) -> ShareCertificate:
        """
        Génère un certificat PDF pour une issuance d'actions
        
        Args:
            issuance: L'issuance d'actions pour laquelle générer le certificat
            
        Returns:
            ShareCertificate: Le certificat généré avec le chemin du fichier PDF
            
        Raises:
            Exception: Si la génération échoue
        """
        pass