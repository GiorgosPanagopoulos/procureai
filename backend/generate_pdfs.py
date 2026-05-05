"""Generate valid PDF files for testing procurement data."""

from datetime import datetime
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:
    # If reportlab is not available, use fpdf2
    pass


def create_contract_buildpro():
    """Create a sample construction contract PDF."""
    pdf_path = Path(__file__).parent / "data" / "pdfs" / "contract_buildpro.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Add content
    story.append(Paragraph("<b>CONSTRUCTION SERVICES CONTRACT</b>", styles["Heading1"]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("<b>BETWEEN:</b>", styles["Normal"]))
    story.append(Paragraph("BuildPro Construction Services Inc.", styles["Normal"]))
    story.append(Paragraph("123 Construction Avenue, New York, NY 10001", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>AND:</b>", styles["Normal"]))
    story.append(Paragraph("ABC Development Corporation", styles["Normal"]))
    story.append(Paragraph("456 Commercial Plaza, New York, NY 10002", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("<b>PROJECT SCOPE:</b>", styles["Heading2"]))
    story.append(
        Paragraph(
            "Commercial office building renovation and construction management services. "
            "Work includes structural reinforcement, electrical systems upgrade, HVAC installation, "
            "interior finishing, and project management oversight.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>CONTRACT TERMS:</b>", styles["Heading2"]))
    story.append(Paragraph("Project Duration: 18 months", styles["Normal"]))
    story.append(Paragraph("Start Date: June 1, 2024", styles["Normal"]))
    story.append(Paragraph("Completion Date: December 1, 2025", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>PRICING:</b>", styles["Heading2"]))
    story.append(Paragraph("Total Contract Value: $2,450,000.00 USD", styles["Normal"]))
    story.append(
        Paragraph(
            "Payment Terms: Monthly invoicing based on completion milestones",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>DELIVERABLES:</b>", styles["Heading2"]))
    story.append(Paragraph("• Detailed project timeline and schedule", styles["Normal"]))
    story.append(Paragraph("• Weekly progress reports", styles["Normal"]))
    story.append(Paragraph("• Construction permits and inspections", styles["Normal"]))
    story.append(Paragraph("• Final as-built documentation", styles["Normal"]))
    story.append(Paragraph("• Project completion certificate", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(
        Paragraph(f"Signature Date: {datetime.now().strftime('%B %d, %Y')}", styles["Normal"])
    )

    doc.build(story)
    print(f"✓ Created {pdf_path}")


def create_contract_techsupply():
    """Create a sample technology supply agreement PDF."""
    pdf_path = Path(__file__).parent / "data" / "pdfs" / "contract_techsupply.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>TECHNOLOGY SUPPLY AND SUPPORT AGREEMENT</b>", styles["Heading1"]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("<b>VENDOR:</b>", styles["Normal"]))
    story.append(Paragraph("TechSupply Global Inc.", styles["Normal"]))
    story.append(Paragraph("789 Innovation Drive, San Jose, CA 95110", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>CLIENT:</b>", styles["Normal"]))
    story.append(Paragraph("Enterprise Systems LLC", styles["Normal"]))
    story.append(Paragraph("321 Business Boulevard, Chicago, IL 60601", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("<b>SERVICES INCLUDED:</b>", styles["Heading2"]))
    story.append(
        Paragraph(
            "• Supply of 100x High-performance servers (2U rack format)",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph(
            "• Network infrastructure equipment (switches, routers, firewalls)",
            styles["Normal"],
        )
    )
    story.append(Paragraph("• 3-year comprehensive support and maintenance", styles["Normal"]))
    story.append(Paragraph("• Hardware replacement warranty", styles["Normal"]))
    story.append(Paragraph("• 24/7 technical support hotline", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>DELIVERY SCHEDULE:</b>", styles["Heading2"]))
    story.append(Paragraph("Equipment delivery: Q2 2024", styles["Normal"]))
    story.append(Paragraph("Installation and configuration: Q2 2024", styles["Normal"]))
    story.append(Paragraph("Support period: 3 years from delivery", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>TOTAL AGREEMENT VALUE:</b>", styles["Heading2"]))
    story.append(Paragraph("$875,500.00 USD", styles["Normal"]))
    story.append(
        Paragraph(
            "Payment: 30% upon order, 50% upon delivery, 20% upon installation completion",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.3 * inch))

    story.append(
        Paragraph(f"Agreement Date: {datetime.now().strftime('%B %d, %Y')}", styles["Normal"])
    )

    doc.build(story)
    print(f"✓ Created {pdf_path}")


def create_pricelist_mediequip():
    """Create a sample medical equipment price list PDF."""
    pdf_path = Path(__file__).parent / "data" / "pdfs" / "pricelist_mediequip.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>MEDIEQUIP HEALTHCARE SOLUTIONS</b>", styles["Heading1"]))
    story.append(Paragraph("<b>2024 PRICE LIST</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Effective Date: January 1, 2024", styles["Normal"]))
    story.append(Paragraph("Edition: Q1 2024", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Create pricing table
    data = [
        ["Product Code", "Description", "Unit Price", "Bulk Discount"],
        ["MED-001", "Digital Patient Monitor (12-lead ECG)", "$1,250.00", "15% for 5+"],
        ["MED-002", "Portable Ultrasound System", "$8,500.00", "10% for 2+"],
        ["MED-003", "Automated Blood Analyzer", "$3,200.00", "12% for 3+"],
        ["MED-004", "Ventilator (ICU-grade)", "$12,800.00", "8% for 1+"],
        ["MED-005", "IV Infusion Pump (Smart)", "$450.00", "20% for 10+"],
        ["MED-006", "Defibrillator (AED)", "$1,500.00", "15% for 5+"],
        ["MED-007", "Pulse Oximeter (Tabletop)", "$280.00", "25% for 20+"],
        ["MED-008", "Blood Pressure Monitor (Automatic)", "$380.00", "18% for 15+"],
    ]

    table = Table(data, colWidths=[1.2 * inch, 2.5 * inch, 1.2 * inch, 1.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("<b>TERMS & CONDITIONS:</b>", styles["Normal"]))
    story.append(
        Paragraph(
            "• All prices in USD and subject to 2% increase on January 1, 2025",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph("• Bulk discounts apply to orders of specified quantities", styles["Normal"])
    )
    story.append(Paragraph("• Delivery: 2-4 weeks from order confirmation", styles["Normal"]))
    story.append(
        Paragraph("• Installation and training available at additional cost", styles["Normal"])
    )

    doc.build(story)
    print(f"✓ Created {pdf_path}")


def create_pricelist_officemart():
    """Create a sample office supplies price list PDF."""
    pdf_path = Path(__file__).parent / "data" / "pdfs" / "pricelist_officemart.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>OFFICEMART SUPPLIES & EQUIPMENT</b>", styles["Heading1"]))
    story.append(Paragraph("<b>BULK ORDER PRICE LIST</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Valid: January 1 - December 31, 2024", styles["Normal"]))
    story.append(
        Paragraph("Contact: sales@officemart.com | Phone: 1-800-OFFICE1", styles["Normal"])
    )
    story.append(Spacer(1, 0.3 * inch))

    # Create pricing table
    data = [
        ["SKU", "Product Name", "Unit Price", "Box Price", "MOQ"],
        [
            "OM-PAPER-001",
            "Copy Paper (8.5x11, 20lb)",
            "$5.99",
            "$55.00 (10 reams)",
            "100 reams",
        ],
        [
            "OM-PEN-002",
            "Ballpoint Pens (Blue, box of 50)",
            "$12.50",
            "N/A",
            "500 units",
        ],
        ["OM-DESK-003", 'Executive Desk (60" x 30")', "$325.00", "N/A", "1"],
        ["OM-CHAIR-004", "Ergonomic Office Chair", "$249.99", "N/A", "5"],
        ["OM-CABINET-005", "4-Drawer Filing Cabinet", "$189.99", "N/A", "10"],
        [
            "OM-FOLDER-006",
            "Manila Folders (Letter, 100ct)",
            "$8.75",
            "$82.00 (10 box)",
            "100 units",
        ],
        [
            "OM-LABEL-007",
            "Mailing Labels (100 sheets)",
            "$4.95",
            "$44.00 (10 pack)",
            "500 sheets",
        ],
        ["OM-TONER-008", "Laser Toner Cartridge (Black)", "$85.00", "N/A", "1"],
    ]

    table = Table(data, colWidths=[0.9 * inch, 2.2 * inch, 1.0 * inch, 1.4 * inch, 1.0 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("<b>ORDER INFORMATION:</b>", styles["Normal"]))
    story.append(Paragraph("• Minimum order quantities shown in MOQ column", styles["Normal"]))
    story.append(
        Paragraph(
            "• Volume discounts: 10% off for orders over $1,000, 15% off for over $5,000",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph("• Free shipping on orders over $500 (continental US)", styles["Normal"])
    )
    story.append(Paragraph("• Payment: Net 30 for established accounts", styles["Normal"]))

    doc.build(story)
    print(f"✓ Created {pdf_path}")


if __name__ == "__main__":
    print("Generating procurement PDFs...")
    try:
        create_contract_buildpro()
        create_contract_techsupply()
        create_pricelist_mediequip()
        create_pricelist_officemart()
        print("\n✓ All PDFs generated successfully!")
    except Exception as e:
        print(f"✗ Error generating PDFs: {e}")
        raise
