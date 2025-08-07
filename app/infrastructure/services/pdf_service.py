# app/infrastructure/services/pdf_service.py (SOLUTION FINALE)
import os
import logging
from datetime import datetime
from typing import Tuple, Optional
from weasyprint import HTML
from app.application.ports.pdf_generator import IPdfGenerator
from app.domain.entities.share_issuance import ShareIssuance
from app.domain.entities.share_certificate import ShareCertificate

logger = logging.getLogger(__name__)


class WeasyPrintPdfGenerator(IPdfGenerator):
    def __init__(self, storage_path: str = "./certificates"):
        self.storage_path = storage_path
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        logger.info(f"PDF Generator initialized with storage path: {self.storage_path}")
    
    def generate_share_certificate(self, issuance: ShareIssuance) -> ShareCertificate:
        """
        Version finale qui évite le conflit WeasyPrint
        """
        logger.info(f"🔥 SYNC PDF Generation started for issuance {issuance.id}")
        
        try:
            # Create certificate entity
            certificate = ShareCertificate(
                share_issuance_id=issuance.id,
                watermark=f"Certificate No. {str(issuance.id)[:8].upper()}",
                generation_date=datetime.now()
            )
            
            logger.info(f"✅ Certificate entity created: {certificate.id}")
            
            # Generate HTML content
            html_content = self._generate_html_content(issuance, certificate)
            logger.info(f"✅ HTML generated (length: {len(html_content)})")
            
            # Generate PDF filename
            filename = f"certificate_{certificate.id}.pdf"
            file_path = os.path.join(self.storage_path, filename)
            logger.info(f"✅ Target file path: {file_path}")
            
            # 🎯 SOLUTION: Utiliser la méthode alternative qui évite le conflit
            success, error_msg = self._generate_pdf_alternative(
                html_content=html_content,
                output_path=file_path,
                css_content=self._get_css_styles()
            )
            
            if success:
                certificate.storage_path = file_path
                logger.info(f"🎉 Certificate generation completed: {certificate.id}")
                return certificate
            else:
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"❌ PDF generation failed: {str(e)}")
            raise Exception(f"PDF generation error: {str(e)}")
    
    def _generate_pdf_alternative(
        self,
        html_content: str,
        output_path: str,
        css_content: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Méthode alternative qui évite le conflit WeasyPrint
        Intègre le CSS directement dans le HTML
        """
        try:
            logger.info("🔄 Using alternative PDF generation method...")
            
            # Créer le répertoire si nécessaire
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"✅ Created directory: {output_dir}")
            
            # 🎯 SOLUTION CLEF: Intégrer le CSS directement dans le HTML
            if css_content:
                html_with_style = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Share Certificate</title>
                    <style>
                        {css_content}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
                </html>
                """
            else:
                html_with_style = html_content
            
            # 🎯 GÉNÉRER PDF AVEC UNE SEULE MÉTHODE (évite le conflit)
            logger.info("🔄 Generating PDF with integrated styles...")
            HTML(string=html_with_style).write_pdf(output_path)
            
            # Vérifier que le fichier a été créé
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"✅ PDF successfully generated: {output_path} (size: {file_size} bytes)")
                return True, None
            else:
                error_msg = f"PDF file was not created at {output_path}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"PDF generation error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"❌ Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return False, error_msg
    
    def _generate_html_content(self, issuance: ShareIssuance, certificate: ShareCertificate) -> str:
        """
        Generate HTML content SANS les balises html/head/body 
        (elles seront ajoutées dans _generate_pdf_alternative)
        """
        try:
            # Safer string formatting
            quantity_str = str(issuance.quantity.value)
            price_str = f"{issuance.price_per_share.amount} {issuance.price_per_share.currency}"
            total_str = f"{issuance.total_value.amount} {issuance.total_value.currency}"
            issue_date_str = issuance.issue_date.strftime('%B %d, %Y')
            gen_date_str = certificate.generation_date.strftime('%Y-%m-%d %H:%M:%S')
            
            # HTML CONTENT SEULEMENT (sans html/head/body)
            html_body = f"""
<div class="wrapper">
  <div class="certificate">
    <div class="watermark">{certificate.watermark}</div>

    <div class="header">
      <h1>SHARE CERTIFICATE</h1>
      <div class="subhead">
         <strong>{certificate.watermark}</strong>
      </div>
    </div>

    <div class="content">
      <p class="intro">This certifies that</p>

      <p class="shareholder-name">
        {issuance.shareholder_name.upper() if issuance.shareholder_name else ""}
      </p>

      <p class="ownership-text">is the registered holder of</p>

      <div class="share-details">
        <div class="share-quantity">
          {quantity_str}
        </div>
        <div class="share-class">
          fully paid shares of {issuance.share_class_id} class
        </div>
      </div>

      <div class="financial-details">
        <div class="financial-grid">
          <div class="financial-item">
            <span class="financial-label">Price per share</span>
            <span class="financial-value">{price_str}</span>
          </div>
          <div class="financial-item">
            <span class="financial-label">Total value</span>
            <span class="financial-value">{total_str}</span>
          </div>
          <div class="financial-item">
            <span class="financial-label">Issue date</span>
            <span class="financial-value">{issue_date_str}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="footer">
      <div class="signatures">
        <div class="signature">
          <div class="line"></div>
          <p>Director</p>
        </div>
        <div class="signature">
          <div class="line"></div>
          <p>Secretary</p>
        </div>
      </div>

      <div class="generation-info">
        <p>Generated on: {gen_date_str}</p>
        <p>Certificate ID: {certificate.id}</p>
      </div>
    </div>
  </div>
</div>
"""
            return html_body
            
        except Exception as e:
            raise Exception(f"HTML generation error: {str(e)}")
    
    def _get_css_styles(self) -> str:
        """CSS styles optimisés"""
        return """
@page {
  size: A4;
  margin: 2cm;
}

:root {
  --paper: #fffef9;
  --ink: #1f2937;            /* gris anthracite lisible */
  --accent: #8b6b2d;         /* doré discret */
  --border: #3f3f46;         /* gris foncé pour les bordures */
  --muted: #6b7280;          /* texte secondaire */
}

* {
  box-sizing: border-box;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

html, body {
  height: 100%;
}

body {
  font-family: "Garamond", "Times New Roman", serif;
  margin: 0;
  padding: 0;
  background: #f5f5f5;
  color: var(--ink);
}

.wrapper {
  max-width: 210mm; /* Largeur A4 */
  margin: 24px auto;
  padding: 0 16px;
}

.certificate {
  position: relative;
  background: var(--paper);
  padding: 40px 48px;
  /* Cadre ornemental (double bordure + filet) */
  border: 6px double var(--border);
  outline: 1px solid color-mix(in srgb, var(--border) 40%, white);
  box-shadow: 0 6px 24px rgba(0,0,0,0.08);
  min-height: 80vh;
}

/* Filigrane (watermark) */
.certificate .watermark {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  pointer-events: none;
  user-select: none;
  opacity: 0.06;
  font-size: clamp(64px, 12vw, 140px);
  font-weight: 600;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: var(--ink);
  transform: rotate(-18deg);
}

/* En-tête */
.header {
  position: relative;
  text-align: center;
  padding-bottom: 24px;
  margin-bottom: 32px;
  border-bottom: 2px solid color-mix(in srgb, var(--border) 85%, white);
}

.header h1 {
  margin: 0;
  font-size: 28px;
  letter-spacing: 0.20em;
  color: var(--ink);
}

.subhead {
  margin-top: 10px;
  font-size: 12px;
  color: var(--muted);
}

.subhead strong {
  color: var(--ink);
  font-weight: 700;
}

/* Corps */
.content {
  position: relative;
  text-align: center;
  line-height: 1.8;
  z-index: 1; /* au-dessus du watermark */
}

.intro {
  font-size: 16px;
  margin: 0 0 18px 0;
  color: var(--ink);
}

.shareholder-name {
  font-size: clamp(18px, 3vw, 22px);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink);
  text-decoration: underline;
  margin: 8px 0 16px 0;
  padding: 4px 8px;
}

.ownership-text {
  font-size: 16px;
  margin: 10px 0 18px 0;
  color: var(--ink);
}

.share-details {
  margin: 28px auto 24px auto;
  padding: 18px 16px;
  max-width: 520px;
  background:
    linear-gradient(0deg, rgba(139,107,45,0.06), rgba(139,107,45,0.06));
  border: 1.5px solid color-mix(in srgb, var(--accent) 60%, var(--border));
  border-radius: 8px;
}

.share-quantity {
  font-size: clamp(36px, 6vw, 52px);
  font-weight: 800;
  line-height: 1.1;
  margin-bottom: 8px;
  color: var(--ink);
}

.share-class {
  font-size: 16px;
  color: color-mix(in srgb, var(--ink) 85%, white);
}

/* Détails financiers en grille */
.financial-details {
  margin: 26px auto 8px auto;
  max-width: 600px;
  padding: 16px 18px;
  border-left: 4px solid var(--accent);
  background:
    linear-gradient(0deg, rgba(139,107,45,0.04), rgba(139,107,45,0.04));
}

.financial-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

.financial-item {
  text-align: left;
}

.financial-label {
  display: block;
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.financial-value {
  font-size: 14px;
  color: var(--ink);
  font-weight: 600;
}

/* Pied de page */
.footer {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 16px;
  align-items: end;
  margin-top: 48px;
  padding-top: 24px;
  border-top: 2px solid color-mix(in srgb, var(--border) 85%, white);
}

.signatures {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 28px;
}

.signature {
  text-align: center;
}

.signature .line {
  width: 100%;
  height: 1px;
  background: var(--ink);
  margin: 0 0 8px 0;
}

.signature p {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.generation-info {
  text-align: right;
  font-size: 10.5px;
  color: var(--muted);
}

.generation-info p {
  margin: 4px 0;
}

/* Impression */
@media print {
  body {
    background: transparent;
  }
  .wrapper {
    margin: 0;
    padding: 0;
    max-width: none;
  }
  .certificate {
    box-shadow: none;
  }
}
"""
