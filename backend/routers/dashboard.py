"""Dashboard router — portfolio summary + PDF report download."""
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from models.schemas import DashboardSummary
from services.auth_service import get_current_user
from services import data_service

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def summary(user=Depends(get_current_user)):
    return data_service.dashboard_summary()


@router.get("/report/{customer_id}")
async def pdf_report(customer_id: str, user=Depends(get_current_user)):
    profile = data_service.get_customer_profile(customer_id)
    decision = data_service.get_credit_decision(customer_id)
    if not profile or not decision:
        raise HTTPException(status_code=404, detail="Customer not found")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title=f"C1B Risk Report - {customer_id}")
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"C1B Credit Risk Report — {customer_id}", styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.now(timezone.utc).isoformat()}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Customer Profile", styles["Heading2"]))
    prof_rows = [[k.replace("_", " ").title(), str(v)] for k, v in profile.items()]
    t = Table(prof_rows, colWidths=[180, 320])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Risk Assessment", styles["Heading2"]))
    risk_rows = [
        ["Risk Label", decision["risk_label"]],
        ["Risk Score", f"{decision['risk_score']:.4f}"],
        ["Recommended Action", decision["action"]],
        ["Current Limit", f"₹{decision['current_limit']:,.2f}"],
        ["Recommended Limit", f"₹{decision['recommended_limit']:,.2f}"],
        ["Current APR", f"{decision['current_apr'] * 100:.2f}%"],
        ["Recommended APR", f"{decision['recommended_apr'] * 100:.2f}%"],
        ["Opportunity Rank", str(decision["opportunity_rank"])],
    ]
    t2 = Table(risk_rows, colWidths=[180, 320])
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(t2)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Top SHAP Drivers", styles["Heading2"]))
    sh = [["Feature", "Importance"]] + [[k, f"{v:.4f}"] for k, v in decision["contributing_factors"].items()]
    t3 = Table(sh, colWidths=[260, 100])
    t3.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366F1")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(t3)
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Adverse Action Notice: This decision is based on the LightGBM Champion model "
        f"({decision['risk_label']}, score={decision['risk_score']:.4f}). Top contributing "
        "factors are listed above. Decision is replayable via model registry.",
        styles["Normal"],
    ))

    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="c1b_report_{customer_id}.pdf"'},
    )
