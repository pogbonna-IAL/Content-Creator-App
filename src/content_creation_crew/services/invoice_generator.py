"""
Invoice PDF generator using ReportLab

Generates professional PDF invoices compliant with international standards.
"""
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, date
from io import BytesIO
import logging

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("ReportLab not installed. Install with: pip install reportlab")

logger = logging.getLogger(__name__)


class InvoiceGenerator:
    """
    Generate professional PDF invoices
    
    Features:
    - Multi-currency support
    - Tax breakdown
    - Company branding
    - International compliance
    """
    
    # Company details (configure via environment or database)
    COMPANY_NAME = "Content Creation Crew"
    COMPANY_ADDRESS = "123 Innovation Street"
    COMPANY_CITY = "Lagos, Nigeria"
    COMPANY_POSTAL = "100001"
    COMPANY_EMAIL = "billing@contentcrew.ai"
    COMPANY_PHONE = "+234 XXX XXX XXXX"
    COMPANY_TAX_ID = "12345678-0001"  # Nigeria TIN
    
    def __init__(self):
        """Initialize invoice generator"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")
    
    def generate_invoice_pdf(
        self,
        invoice_data: Dict[str, Any],
        customer_data: Dict[str, Any],
        line_items: List[Dict[str, Any]],
        tax_details: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate invoice PDF
        
        Args:
            invoice_data: Invoice details (number, date, due_date, amounts, etc.)
            customer_data: Customer information (name, email, address)
            line_items: List of line items with description, quantity, price
            tax_details: Tax calculation details
        
        Returns:
            PDF bytes
        """
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build content
        story = []
        styles = getSampleStyleSheet()
        
        # Add custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#374151'),
            spaceAfter=6,
        )
        
        # Header: Company Info
        story.append(Paragraph(self.COMPANY_NAME, title_style))
        story.append(Paragraph(self.COMPANY_ADDRESS, styles['Normal']))
        story.append(Paragraph(self.COMPANY_CITY, styles['Normal']))
        story.append(Paragraph(f"Email: {self.COMPANY_EMAIL} | Phone: {self.COMPANY_PHONE}", styles['Normal']))
        story.append(Paragraph(f"Tax ID: {self.COMPANY_TAX_ID}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Invoice title and number
        invoice_title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#dc2626'),
            alignment=TA_RIGHT,
        )
        story.append(Paragraph(f"INVOICE", invoice_title_style))
        story.append(Paragraph(f"#{invoice_data['invoice_number']}", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Invoice details table
        invoice_info = [
            ['Invoice Date:', invoice_data['invoice_date']],
            ['Due Date:', invoice_data['due_date']],
            ['Status:', invoice_data['status'].upper()],
        ]
        
        info_table = Table(invoice_info, colWidths=[1.5*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Bill to section
        story.append(Paragraph("BILL TO:", heading_style))
        story.append(Paragraph(customer_data.get('company_name') or customer_data.get('contact_name', 'N/A'), styles['Normal']))
        if customer_data.get('email'):
            story.append(Paragraph(customer_data['email'], styles['Normal']))
        if customer_data.get('address_line1'):
            story.append(Paragraph(customer_data['address_line1'], styles['Normal']))
            if customer_data.get('address_line2'):
                story.append(Paragraph(customer_data['address_line2'], styles['Normal']))
            address_parts = [
                customer_data.get('city', ''),
                customer_data.get('state_province', ''),
                customer_data.get('postal_code', ''),
            ]
            address_line = ', '.join([p for p in address_parts if p])
            if address_line:
                story.append(Paragraph(address_line, styles['Normal']))
            story.append(Paragraph(customer_data.get('country_code', ''), styles['Normal']))
        
        if customer_data.get('tax_id'):
            story.append(Paragraph(f"Tax ID: {customer_data['tax_id']}", styles['Normal']))
        
        story.append(Spacer(1, 0.4*inch))
        
        # Line items table
        story.append(Paragraph("ITEMS", heading_style))
        
        # Table header
        table_data = [['Description', 'Quantity', 'Unit Price', 'Amount']]
        
        # Add line items
        currency = invoice_data.get('currency', 'USD')
        for item in line_items:
            table_data.append([
                item.get('description', ''),
                str(item.get('quantity', 1)),
                self._format_currency(item.get('unit_price', 0), currency),
                self._format_currency(item.get('amount', 0), currency),
            ])
        
        # Create table
        items_table = Table(table_data, colWidths=[3.5*inch, 0.8*inch, 1.2*inch, 1.2*inch])
        items_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Body
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Totals section
        totals_data = []
        
        # Subtotal
        totals_data.append(['Subtotal:', self._format_currency(invoice_data['subtotal'], currency)])
        
        # Tax
        if tax_details and invoice_data.get('tax_amount', 0) > 0:
            tax_label = f"{tax_details.get('tax_name', 'Tax')} ({float(tax_details.get('tax_rate', 0)) * 100:.2f}%):"
            totals_data.append([tax_label, self._format_currency(invoice_data['tax_amount'], currency)])
            
            # Add reverse charge notice if applicable
            if tax_details.get('reverse_charge'):
                story.append(Paragraph(
                    "<i>* Reverse charge applies - customer to self-account for VAT</i>",
                    styles['Normal']
                ))
                story.append(Spacer(1, 0.1*inch))
        
        # Total
        totals_data.append(['TOTAL:', self._format_currency(invoice_data['total'], currency)])
        
        # Amount paid
        if invoice_data.get('amount_paid', 0) > 0:
            totals_data.append(['Paid:', f"-{self._format_currency(invoice_data['amount_paid'], currency)}"])
        
        # Amount due
        if invoice_data.get('amount_due', 0) > 0:
            totals_data.append(['Amount Due:', self._format_currency(invoice_data['amount_due'], currency)])
        
        totals_table = Table(totals_data, colWidths=[5.5*inch, 1.2*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(totals_table)
        story.append(Spacer(1, 0.4*inch))
        
        # Payment terms and notes
        if invoice_data.get('memo'):
            story.append(Paragraph("NOTES:", heading_style))
            story.append(Paragraph(invoice_data['memo'], styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Footer
        footer_text = "Thank you for your business! For questions about this invoice, please contact us at " + self.COMPANY_EMAIL
        story.append(Spacer(1, 0.3*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER,
        )
        story.append(Paragraph(footer_text, footer_style))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _format_currency(self, amount: float, currency: str = "USD") -> str:
        """Format amount as currency"""
        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "NGN": "₦",
        }
        
        symbol = symbols.get(currency, currency + " ")
        return f"{symbol}{amount:,.2f}"


# Singleton instance
_invoice_generator = None


def get_invoice_generator() -> InvoiceGenerator:
    """Get singleton invoice generator instance"""
    global _invoice_generator
    if _invoice_generator is None:
        _invoice_generator = InvoiceGenerator()
    return _invoice_generator

