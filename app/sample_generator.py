from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime, timedelta

def create_sample_pdf(
    file_path: Path,
    vendor_name: str,
    vendor_address: str,
    vendor_phone: str,
    invoice_number: str,
    po_number: str,
    invoice_date: str,
    due_date: str,
    customer_name: str,
    customer_address: str,
    items: list,
    subtotal: float,
    tax_rate: float,
    tax_amount: float,
    shipping: float,
    discount: float,
    total: float,
    notes: str = "Thank you for your business! Please send payment within 30 days."
):
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#64748b")
    )
    header_right = ParagraphStyle(
        'HeaderRight',
        parent=styles['Normal'],
        fontSize=11,
        alignment=2,
        textColor=colors.HexColor("#334155")
    )
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor("#475569"),
        leading=14
    )
    bold_meta = ParagraphStyle(
        'BoldMeta',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#0f172a"),
        leading=14
    )

    elements = []

    # Header section: Vendor and Invoice Title
    header_data = [
        [
            Paragraph(f"<b>{vendor_name}</b>", title_style),
            Paragraph(f"<b>INVOICE</b><br/><font size=12 color='#0284c7'>#{invoice_number}</font>", header_right)
        ],
        [
            Paragraph(f"{vendor_address}<br/>Phone: {vendor_phone}", subtitle_style),
            Paragraph(f"<b>Date:</b> {invoice_date}<br/><b>Due Date:</b> {due_date}<br/><b>P.O. #:</b> {po_number}", header_right)
        ]
    ]
    
    header_table = Table(header_data, colWidths=[4.0 * inch, 3.2 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=15))

    # Bill To section
    bill_data = [
        [
            Paragraph("<b>BILL TO:</b>", bold_meta),
            Paragraph("<b>PAYMENT TERMS:</b>", bold_meta)
        ],
        [
            Paragraph(f"<b>{customer_name}</b><br/>{customer_address}", meta_style),
            Paragraph(f"Net 30 Days<br/>Currency: USD ($)<br/>Method: Direct Bank Wire / ACH", meta_style)
        ]
    ]
    bill_table = Table(bill_data, colWidths=[4.0 * inch, 3.2 * inch])
    bill_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(bill_table)
    elements.append(Spacer(1, 15))

    # Line Items Table
    table_data = [["Description", "Qty", "Unit Price", "Total Amount"]]
    for item in items:
        table_data.append([
            item["desc"],
            str(item["qty"]),
            f"${item['price']:,.2f}",
            f"${item['amount']:,.2f}"
        ])

    items_table = Table(table_data, colWidths=[3.8 * inch, 0.8 * inch, 1.3 * inch, 1.3 * inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 7),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 15))

    # Summary Totals Table
    summary_data = [
        ["", "Subtotal:", f"${subtotal:,.2f}"],
        ["", f"Sales Tax ({tax_rate}%):", f"${tax_amount:,.2f}"],
    ]
    if shipping > 0:
        summary_data.append(["", "Shipping & Handling:", f"${shipping:,.2f}"])
    if discount > 0:
        summary_data.append(["", "Discount:", f"-${discount:,.2f}"])
    summary_data.append(["", "Total Amount Due:", f"${total:,.2f}"])

    summary_table = Table(summary_data, colWidths=[3.8 * inch, 1.8 * inch, 1.6 * inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (1,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (1,-1), (-1,-1), 11),
        ('TEXTCOLOR', (1,-1), (-1,-1), colors.HexColor("#0284c7")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LINEABOVE', (1,-1), (-1,-1), 1.5, colors.HexColor("#0284c7")),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Notes & Footer
    elements.append(Paragraph(f"<b>Notes:</b> {notes}", meta_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Electronic system generated invoice • ApexInvoice Processing Agent", subtitle_style))

    doc.build(elements)

def generate_all_preset_samples(target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    
    today = datetime.now()
    d_today = today.strftime("%Y-%m-%d")
    d_due = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    d_past = (today - timedelta(days=10)).strftime("%Y-%m-%d")

    # Sample 1: Standard Clean Cloud Invoice (Approved)
    create_sample_pdf(
        file_path=target_dir / "sample_cloud_hosting.pdf",
        vendor_name="Nexus Cloud Technologies Inc.",
        vendor_address="100 Silicon Blvd, Suite 400, San Francisco, CA 94107",
        vendor_phone="+1 (415) 555-0199",
        invoice_number="INV-2026-8801",
        po_number="PO-99420",
        invoice_date=d_today,
        due_date=d_due,
        customer_name="Starlight Media Corp",
        customer_address="742 Evergreen Terrace, Springfield, OR 97477",
        items=[
            {"desc": "Enterprise Dedicated Kubernetes Cluster", "qty": 1, "price": 1250.00, "amount": 1250.00},
            {"desc": "High-Throughput NVMe Block Storage (2TB)", "qty": 2, "price": 180.00, "amount": 360.00},
            {"desc": "Global CDN Bandwidth Overages (5TB)", "qty": 5, "price": 45.00, "amount": 225.00},
            {"desc": "24/7 Priority DevOps SLA Support", "qty": 1, "price": 350.00, "amount": 350.00}
        ],
        subtotal=2185.00,
        tax_rate=8.5,
        tax_amount=185.73,
        shipping=0.0,
        discount=0.0,
        total=2370.73
    )

    # Sample 2: High-Value Enterprise Hardware Invoice (High Value Alert > $5k)
    create_sample_pdf(
        file_path=target_dir / "sample_high_value_servers.pdf",
        vendor_name="Titan Hardware & Server Solutions Ltd.",
        vendor_address="450 Industrial Parkway, Austin, TX 78701",
        vendor_phone="+1 (512) 555-0812",
        invoice_number="INV-2026-9950",
        po_number="PO-ENTERPRISE-01",
        invoice_date=d_today,
        due_date=d_due,
        customer_name="Global Fintech Systems LLC",
        customer_address="120 Wall Street, 22nd Floor, New York, NY 10005",
        items=[
            {"desc": "Titan PowerEdge GPU Server Rack 4U", "qty": 2, "price": 7500.00, "amount": 15000.00},
            {"desc": "100GbE High-Speed Optical Transceivers", "qty": 8, "price": 250.00, "amount": 2000.00},
            {"desc": "Onsite Rack Mounting & Cable Management", "qty": 1, "price": 950.00, "amount": 950.00}
        ],
        subtotal=17950.00,
        tax_rate=7.0,
        tax_amount=1256.50,
        shipping=250.00,
        discount=500.00,
        total=18956.50,
        notes="High-value enterprise infrastructure hardware. Requires CFO / VP authorization."
    )

    # Sample 3: Math Mismatch Calculation Error Invoice (Flagged)
    create_sample_pdf(
        file_path=target_dir / "sample_math_discrepancy.pdf",
        vendor_name="Apex Office Furniture & Supplies",
        vendor_address="78 Commerce Way, Chicago, IL 60601",
        vendor_phone="+1 (312) 555-4321",
        invoice_number="INV-2026-3319",
        po_number="PO-OFFICE-88",
        invoice_date=d_today,
        due_date=d_due,
        customer_name="Starlight Media Corp",
        customer_address="742 Evergreen Terrace, Springfield, OR 97477",
        items=[
            {"desc": "Ergonomic Mesh Task Chairs", "qty": 4, "price": 250.00, "amount": 1000.00},
            # Intentionally erroneous amount: 2 x $400 is $800, but invoice says $750
            {"desc": "Electric Motorized Standing Desks", "qty": 2, "price": 400.00, "amount": 750.00},
            {"desc": "Dual Monitor Arm Mounts", "qty": 4, "price": 60.00, "amount": 240.00}
        ],
        subtotal=1990.00, # Sum of lines is 1990, but actual math mismatch inside row 2 and wrong total
        tax_rate=8.0,
        tax_amount=159.20,
        shipping=50.00,
        discount=0.0,
        total=2350.00, # Intentionally wrong: 1990 + 159.20 + 50 = 2199.20, but printed 2350.00
        notes="WARNING: Artificial discrepancies included for automated validation engine testing."
    )

    # Sample 4: Date Mismatch / Past Due Date Invoice (Pending Review / Flagged)
    create_sample_pdf(
        file_path=target_dir / "sample_date_inconsistency.pdf",
        vendor_name="CyberShield Security Consultants",
        vendor_address="303 Security Blvd, Boston, MA 02110",
        vendor_phone="+1 (617) 555-8822",
        invoice_number="INV-2026-4402",
        po_number="PO-SEC-09",
        invoice_date=d_today,
        due_date=d_past, # Due date is 10 days BEFORE invoice issue date!
        customer_name="Starlight Media Corp",
        customer_address="742 Evergreen Terrace, Springfield, OR 97477",
        items=[
            {"desc": "Annual Penetration Testing & Vulnerability Audit", "qty": 1, "price": 3800.00, "amount": 3800.00},
            {"desc": "SOC2 Compliance Readiness Report", "qty": 1, "price": 1200.00, "amount": 1200.00}
        ],
        subtotal=5000.00,
        tax_rate=0.0,
        tax_amount=0.0,
        shipping=0.0,
        discount=0.0,
        total=5000.00,
        notes="Due date precedes billing date. Test date logic validation."
    )
