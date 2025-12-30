from io import BytesIO
from decimal import Decimal
from collections import defaultdict
from django.utils import timezone
from django.conf import settings
import os

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Spacer,
    Image,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib import colors

from bookings.models import Booking, BookingDocument
from bookings.utils.s3_utils import upload_to_s3


# -------------------------
# CONSTANTS
# -------------------------
LOGO_PATH = os.path.join(settings.BASE_DIR, "staticfiles/logo1.png")
SIGN_PATH = os.path.join(settings.BASE_DIR, "staticfiles/sign.jpeg")
GST_NUMBER = "09AAMCR4918B1ZA"
CURRENCY = "Rs."


def generate_invoice_pdf(booking_id):
    booking = (
        Booking.objects
        .select_related("user", "address")
        .prefetch_related("items")
        .get(id=booking_id)
    )

    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    invoice_no = f"INV-{booking.ref_id}-{timestamp}"

    buffer = BytesIO()

    # ✅ Reduced margins to align everything
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="Right",
        alignment=TA_RIGHT,
    ))

    elements = []

    # -------------------------
    # HEADER
    # -------------------------
    header_table = Table(
        [
            [
                Image(LOGO_PATH, width=160, height=80),
                Paragraph(
                    f"""
                    <font size="14"><b>ROUTINE PATHLAB PVT. LTD.</b></font><br/>
                    E-113, SECOND FLOOR NOIDA<br/>
                    Phone no.: +918447007749<br/>
                    Email: info@drpathcare.com <br/>
                    GSTIN: 09AAMCR4918B1ZA <br/>
                    State: 09-Uttar Pradesh <br/>
                    """,
                    styles["Right"],
                ),
            ]
        ],
        colWidths=[280, 250],
    )

    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 12))

    styles.add(ParagraphStyle(
        name="CenterBlock",
        alignment=1,  # TA_CENTER
        fontSize=11,
        leading=16,
        spaceAfter=12,
    ))

    invoice_center_block = f"""
    <b>SUPPLY INVOICE</b><br/>
    Invoice No: {invoice_no}<br/>
    Date: {timezone.now().strftime('%d-%m-%Y')}
    """

    elements.append(Paragraph(invoice_center_block, styles["CenterBlock"]))
    elements.append(Spacer(1, 12))


    # -------------------------
    # BILL TO
    # -------------------------

    bill_left = f"""
    <b>Bill To</b><br/>
    {booking.user.first_name} {booking.user.last_name}<br/>
    {booking.user.mobile} {booking.user.email}
    """

    bill_right = ""
    if booking.address:
        bill_right = f"""
    <b>Address</b><br/>
    {booking.address.line1}<br/>
    {booking.address.location.city} - {booking.address.location.pincode}
    """

    bill_table = Table(
        [
            [
                Paragraph(bill_left, styles["Normal"]),
                Paragraph(bill_right, styles["Right"]),
            ]
        ],
        colWidths=[280, 250],
    )

    bill_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(bill_table)
    elements.append(Spacer(1, 14))


    # -------------------------
    # GROUP ITEMS
    # -------------------------
    grouped = defaultdict(lambda: {
        "name": "",
        "qty": 0,
        "base": Decimal("0.00"),
        "offer": Decimal("0.00"),
    })

    for item in booking.items.all():
        ref = item.lab_test or item.profile or item.package
        name = ref.name if ref else "Test"

        grouped[name]["name"] = name
        grouped[name]["qty"] += 1
        grouped[name]["base"] += item.base_price
        grouped[name]["offer"] += item.offer_price or item.base_price

    # -------------------------
    # ITEMS TABLE
    # -------------------------
    table_data = [
        ["#", "Test Name", "Qty", "Price", "Amount"]
    ]

    for idx, row in enumerate(grouped.values(), start=1):
        table_data.append([
            idx,
            row["name"],
            row["qty"],
            f"{CURRENCY} {row['base']:.2f}",
            f"{CURRENCY} {row['offer']:.2f}",
        ])

    items_table = Table(
        table_data,
        colWidths=[30, 240, 50, 90, 90],
        repeatRows=1,
    )

    items_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(items_table)
    elements.append(Spacer(1, 14))

    # -------------------------
    # TOTALS (RIGHT ALIGNED, NO GAP)
    # -------------------------
    totals_table = Table(
        [
            ["Sub Total", f"{CURRENCY} {booking.base_total:.2f}"],
            ["Discount", f"- {CURRENCY} {booking.discount_amount:.2f}"],
            ["TOTAL", f"{CURRENCY} {booking.final_amount:.2f}"],
        ],
        colWidths=[380, 110],
    )

    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONT", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("LINEABOVE", (0, 2), (-1, 2), 0.75, colors.black),
        ("TOPPADDING", (0, 2), (-1, 2), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    elements.append(totals_table)
    elements.append(Spacer(1, 20))

    # -------------------------
    # FOOTER (LEFT ALIGNED SIGNATURE)
    # -------------------------
    elements.append(Paragraph(
        "This is a computer generated invoice.",
        styles["Normal"]
    ))

    elements.append(Spacer(1, 12))

    elements.append(
        Image(
            SIGN_PATH,
            width=90,
            height=60,
            hAlign="LEFT"   # 🔑 THIS FIXES IT
        )
    )
    elements.append(Paragraph("<b>Authorized Signatory</b>", styles["Normal"]))

    # -------------------------
    # BUILD PDF
    # -------------------------
    doc.build(elements)
    buffer.seek(0)

    buffer.name = f"{invoice_no}.pdf"
    buffer.content_type = "application/pdf"

    file_url = upload_to_s3(
        buffer,
        prefix="booking_docs/invoices/",
    )
    BookingDocument.objects.filter(booking=booking,doc_type="invoice").delete()
    return BookingDocument.objects.create(
        booking=booking,
        name=f"{invoice_no}.pdf",
        file_url=file_url,
        doc_type="invoice",
        uploaded_by=None,
    )
