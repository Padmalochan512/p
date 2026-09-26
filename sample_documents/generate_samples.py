from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime, timedelta

SAMPLE_DIR = Path(__file__).resolve().parent

def build_pdf_invoice(
    file_path: Path,
    vendor_name: str,
    vendor_address: str,
    vendor_gst: str,
    vendor_phone: str,
    invoice_number: str,
    po_number: str,
    invoice_date: str,
    due_date: str,
    customer_name: str,
    customer_address: str,
    currency_symbol: str,
    currency_code: str,
    items: list,
    subtotal: float,
    tax_rate: float,
    tax_amount: float,
    shipping: float,
    discount: float,
    total: float,
    notes: str = "Thank you for your business. Please remit payment by the due date."
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
        fontSize=20,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=3
    )
    sub_style = ParagraphStyle(
        'SubStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor("#475569")
    )
    inv_header_right = ParagraphStyle(
        'HeaderRight',
        parent=styles['Normal'],
        fontSize=10,
        alignment=2,
        textColor=colors.HexColor("#1e293b")
    )
    meta_title = ParagraphStyle(
        'MetaTitle',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#0f172a")
    )

    elements = []

    # 1. Header
    header_data = [
        [
            Paragraph(f"<b>{vendor_name}</b>", title_style),
            Paragraph(f"<b>TAX INVOICE</b><br/><font color='#2563eb' size=11><b>#{invoice_number}</b></font>", inv_header_right)
        ],
        [
            Paragraph(f"{vendor_address}<br/><b>GSTIN/Tax ID:</b> {vendor_gst}<br/>Phone: {vendor_phone}", sub_style),
            Paragraph(f"<b>Date:</b> {invoice_date}<br/><b>Due Date:</b> {due_date}<br/><b>P.O. #:</b> {po_number}", inv_header_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[4.0 * inch, 3.2 * inch])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4)
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

    # 2. Bill To & Terms
    bill_data = [
        [
            Paragraph("<b>BILLED TO:</b>", meta_title),
            Paragraph("<b>PAYMENT TERMS:</b>", meta_title)
        ],
        [
            Paragraph(f"<b>{customer_name}</b><br/>{customer_address}", sub_style),
            Paragraph(f"Net 30 Days<br/>Currency: {currency_code} ({currency_symbol})<br/>Direct Bank Transfer", sub_style)
        ]
    ]
    t_bill = Table(bill_data, colWidths=[4.0 * inch, 3.2 * inch])
    t_bill.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4)
    ]))
    elements.append(t_bill)
    elements.append(Spacer(1, 12))

    # 3. Line items
    table_rows = [["Item Description", "Qty", f"Unit Price ({currency_symbol})", f"Total ({currency_symbol})"]]
    for it in items:
        table_rows.append([
            it["desc"],
            str(it["qty"]),
            f"{currency_symbol}{it['price']:,.2f}",
            f"{currency_symbol}{it['amount']:,.2f}"
        ])

    t_items = Table(table_rows, colWidths=[3.8 * inch, 0.8 * inch, 1.3 * inch, 1.3 * inch])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_items)
    elements.append(Spacer(1, 10))

    # 4. Summary Totals
    summary_rows = [
        ["", f"Subtotal:", f"{currency_symbol}{subtotal:,.2f}"],
        ["", f"GST/Tax ({tax_rate}%):", f"{currency_symbol}{tax_amount:,.2f}"]
    ]
    if shipping > 0:
        summary_rows.append(["", "Shipping & Freight:", f"{currency_symbol}{shipping:,.2f}"])
    if discount > 0:
        summary_rows.append(["", "Discount:", f"-{currency_symbol}{discount:,.2f}"])
    summary_rows.append(["", "Total Amount Due:", f"{currency_symbol}{total:,.2f}"])

    t_sum = Table(summary_rows, colWidths=[3.8 * inch, 1.8 * inch, 1.6 * inch])
    t_sum.setStyle(TableStyle([
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (1,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (1,-1), (-1,-1), 11),
        ('TEXTCOLOR', (1,-1), (-1,-1), colors.HexColor("#2563eb")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LINEABOVE', (1,-1), (-1,-1), 1.2, colors.HexColor("#2563eb")),
    ]))
    elements.append(t_sum)
    elements.append(Spacer(1, 16))

    # 5. Notes
    elements.append(Paragraph(f"<b>Notes:</b> {notes}", sub_style))

    doc.build(elements)

def generate_samples():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.utcnow()
    d_today = today.strftime("%Y-%m-%d")
    d_due = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    d_past = (today - timedelta(days=10)).strftime("%Y-%m-%d")

    # Sample 1: Clean Approved IT Services (INR ₹)
    build_pdf_invoice(
        file_path=SAMPLE_DIR / "sample_01_it_services_approved.pdf",
        vendor_name="Infospectrum Cloud Technologies Pvt Ltd",
        vendor_address="Plot 45, Electronics City Phase 1, Bengaluru, KA 560100",
        vendor_gst="29ABCDE1234F1Z5",
        vendor_phone="+91 80 4455 6677",
        invoice_number="INV-2026-1001",
        po_number="PO-INF-8802",
        invoice_date=d_today,
        due_date=d_due,
        customer_name="Starlight Media Enterprises",
        customer_address="742 MG Road, Indiranagar, Bengaluru, KA 560038",
        currency_symbol="₹",
        currency_code="INR",
        items=[
            {"desc": "Cloud Infrastructure Management & DevOps", "qty": 1, "price": 45000.00, "amount": 45000.00},
            {"desc": "Kubernetes Cluster Node Hosting (2 Months)", "qty": 2, "price": 12500.00, "amount": 25000.00},
            {"desc": "Database Backup & Disaster Recovery SLA", "qty": 1, "price": 8500.00, "amount": 8500.00}
        ],
        subtotal=78500.00,
        tax_rate=18.0,
        tax_amount=14130.00,
        shipping=0.0,
        discount=0.0,
        total=92630.00
    )

    # Sample 2: High-Value Server Rack Hardware (Triggers > ₹50,000 High Value)
    build_pdf_invoice(
        file_path=SAMPLE_DIR / "sample_02_high_value_servers.pdf",
        vendor_name="Titan Data Center Hardware Solutions",
        vendor_address="88 Industrial Hub, Whitefield, Bengaluru, KA 560066",
        vendor_gst="29TITAN9988G1Z9",
        vendor_phone="+91 80 9988 7766",
        invoice_number="INV-2026-5540",
        po_number="PO-TITAN-01",
        invoice_date=d_today,
        due_date=d_due,
        customer_name="Global Analytics & AI Corp",
        customer_address="120 Outer Ring Road, Bengaluru, KA 560103",
        currency_symbol="₹",
        currency_code="INR",
        items=[
            {"desc": "Titan 4U High-Density GPU Compute Rack", "qty": 2, "price": 240000.00, "amount": 480000.00},
            {"desc": "100Gbps Fibre Optic Switch Interface", "qty": 4, "price": 18500.00, "amount": 74000.00}
        ],
        subtotal=554000.00,
        tax_rate=18.0,
        tax_amount=99720.00,
        shipping=5000.00,
        discount=10000.00,
        total=648720.00,
        notes="High-value procurement order. Requires Finance Director sign-off."
    )

    # Sample 3: Math Mismatch Calculation Discrepancy (Flagged)
    build_pdf_invoice(
        file_path=SAMPLE_DIR / "sample_03_math_discrepancy_flagged.pdf",
        vendor_name="Apex Office & Workspace Supplies",
        vendor_address="12 Sector 5, Salt Lake, Kolkata, WB 700091",
        vendor_gst="19APEXX7766H1Z2",
        vendor_phone="+91 33 2233 4455",
        invoice_number="INV-2026-3390",
        po_number="PO-OFFICE-99",
        invoice_date=d_today,
        due_date=d_due,
        customer_name="Starlight Media Enterprises",
        customer_address="742 MG Road, Bengaluru, KA 560038",
        currency_symbol="₹",
        currency_code="INR",
        items=[
            {"desc": "Ergonomic Mesh Swivel Chairs", "qty": 4, "price": 7500.00, "amount": 30000.00},
            # Line math error: 2 x 12000 is 24000, but printed 20000
            {"desc": "Motorized Height Adjustable Desks", "qty": 2, "price": 12000.00, "amount": 20000.00}
        ],
        subtotal=50000.00,
        tax_rate=18.0,
        tax_amount=9000.00,
        shipping=1500.00,
        discount=0.0,
        total=65000.00, # Discrepancy: 50000 + 9000 + 1500 = 60500, but printed 65000
        notes="Intended testing sample with arithmetic discrepancies."
    )

    # Sample 4: Due Date Inconsistency (Due Date Precedes Invoice Date)
    build_pdf_invoice(
        file_path=SAMPLE_DIR / "sample_04_date_inconsistency.pdf",
        vendor_name="CyberGuard Security Consultants",
        vendor_address="15 Bandra Kurla Complex, Mumbai, MH 400051",
        vendor_gst="27CYBER3322K1Z4",
        vendor_phone="+91 22 6677 8899",
        invoice_number="INV-2026-7788",
        po_number="PO-SEC-44",
        invoice_date=d_today,
        due_date=d_past, # 10 days before issue date
        customer_name="Starlight Media Enterprises",
        customer_address="742 MG Road, Bengaluru, KA 560038",
        currency_symbol="₹",
        currency_code="INR",
        items=[
            {"desc": "Quarterly Cloud Security & Penetration Audit", "qty": 1, "price": 35000.00, "amount": 35000.00}
        ],
        subtotal=35000.00,
        tax_rate=18.0,
        tax_amount=6300.00,
        shipping=0.0,
        discount=0.0,
        total=41300.00,
        notes="Due date precedes billing date. Test date logic flag."
    )
    print("Sample PDF invoices generated successfully in sample_documents/")

if __name__ == "__main__":
    generate_samples()
