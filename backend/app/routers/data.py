"""
Data router: upload, list files, preview, run analysis, delete result/file, download PDF.
All endpoints require authentication. Files stored per user.
"""
import io
import json
import os
import uuid
import base64
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional

from ..db.database import get_db
from ..db.models import User, DataFile, AnalysisResult
from ..auth import get_current_user
from ..services.run_analysis import (
    read_df,
    run_test,
    get_tests_schema,
)

router = APIRouter(prefix="/api/data", tags=["data"])

# Uploads directory: backend/uploads/<user_id>/
UPLOAD_BASE = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_BASE.mkdir(parents=True, exist_ok=True)


def user_upload_dir(user_id: int) -> Path:
    d = UPLOAD_BASE / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_user_owns_file(db: Session, user: User, file_id: int) -> DataFile:
    f = db.query(DataFile).filter(DataFile.id == file_id, DataFile.user_id == user.id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    if not os.path.exists(f.stored_path):
        raise HTTPException(status_code=404, detail="File no longer on disk")
    return f


# ----- Schemas -----

class FileInfo(BaseModel):
    id: int
    original_filename: str
    created_at: str


class PreviewResponse(BaseModel):
    file_id: int
    original_filename: str
    columns: list[str]
    col_types: dict
    preview_html: str
    results: list[dict]


class RunRequest(BaseModel):
    file_id: int
    test_id: str
    params: dict


# ----- Endpoints -----

@router.get("/tests")
def list_tests():
    """Return test definitions for the UI (no auth required for schema)."""
    return get_tests_schema()


@router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    csv_delimiter: str = Form("comma"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Only .csv, .xlsx, .xls allowed")

    delim = "," if csv_delimiter == "comma" else {"semicolon": ";", "tab": "\t", "pipe": "|"}.get(csv_delimiter, ",")
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    user_dir = user_upload_dir(current_user.id)
    stored_path = str(user_dir / safe_name)

    contents = file.file.read()
    with open(stored_path, "wb") as f:
        f.write(contents)

    try:
        df = read_df(stored_path, delim)
    except Exception as e:
        os.remove(stored_path)
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    data_file = DataFile(
        user_id=current_user.id,
        original_filename=file.filename,
        stored_path=stored_path,
        csv_delimiter=delim,
    )
    db.add(data_file)
    db.commit()
    db.refresh(data_file)
    return {
        "id": data_file.id,
        "original_filename": data_file.original_filename,
        "created_at": data_file.created_at.isoformat(),
    }


@router.get("/files")
def list_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    files = (
        db.query(DataFile)
        .filter(DataFile.user_id == current_user.id)
        .order_by(desc(DataFile.created_at))
        .all()
    )
    return [
        {
            "id": f.id,
            "original_filename": f.original_filename,
            "created_at": f.created_at.isoformat(),
        }
        for f in files
    ]


@router.get("/files/{file_id}/preview")
def get_preview(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data_file = ensure_user_owns_file(db, current_user, file_id)
    df = read_df(data_file.stored_path, data_file.csv_delimiter)
    columns = df.columns.tolist()
    col_types = {c: "numeric" if df[c].dtype.kind in "iufb" else "string" for c in columns}
    preview_html = df.head(10).to_html(classes="table", index=False)

    results = []
    for r in (
        db.query(AnalysisResult)
        .filter(AnalysisResult.data_file_id == file_id)
        .order_by(desc(AnalysisResult.created_at))
        .all()
    ):
        results.append({
            "id": r.id,
            "label": r.label,
            "description": r.description,
            "text": r.text,
            "figure": r.figure_base64,
            "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return {
        "file_id": data_file.id,
        "original_filename": data_file.original_filename,
        "columns": columns,
        "col_types": col_types,
        "preview_html": preview_html,
        "results": results,
    }


@router.post("/run")
def run_analysis(
    body: RunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data_file = ensure_user_owns_file(db, current_user, body.file_id)
    try:
        text, figure = run_test(
            data_file.stored_path,
            data_file.csv_delimiter,
            body.test_id,
            body.params,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    tests_schema = get_tests_schema()
    test = tests_schema.get(body.test_id, {})
    col_names = []
    for inp in test.get("inputs", []):
        v = body.params.get(inp["name"])
        if inp["type"] == "column" and v:
            col_names.append(v)
        elif inp["type"] == "multi_column" and v:
            col_names.extend(v if isinstance(v, list) else [v])
    label = f"{test.get('label', body.test_id)} ({', '.join(col_names)})"

    result = AnalysisResult(
        data_file_id=data_file.id,
        test_id=body.test_id,
        label=label,
        description=test.get("description", ""),
        text=text,
        figure_base64=figure,
        params_json=json.dumps(body.params),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return {
        "id": result.id,
        "label": result.label,
        "description": result.description,
        "text": result.text,
        "figure": result.figure_base64,
        "timestamp": result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.delete("/files/{file_id}/results/{result_id}")
def delete_result(
    file_id: int,
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_owns_file(db, current_user, file_id)
    r = db.query(AnalysisResult).filter(
        AnalysisResult.id == result_id,
        AnalysisResult.data_file_id == file_id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Result not found")
    db.delete(r)
    db.commit()
    return {"success": True}


@router.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data_file = ensure_user_owns_file(db, current_user, file_id)
    if os.path.exists(data_file.stored_path):
        os.remove(data_file.stored_path)
    db.delete(data_file)
    db.commit()
    return {"success": True}


@router.post("/files/{file_id}/download-pdf")
def download_pdf(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data_file = ensure_user_owns_file(db, current_user, file_id)
    results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.data_file_id == file_id)
        .order_by(desc(AnalysisResult.created_at))
        .all()
    )

    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(status_code=500, detail="fpdf2 not installed")

    class StatsmedPDF(FPDF):
        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"\u00a9 {datetime.now().year} Martin Segeroth, Ashraya Indrakanti", align="C")

    pdf = StatsmedPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Statsmed Analysis Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, f"File: {data_file.original_filename}    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(4)

    for r in results:
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, r.label, ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 6, f"{r.description}  |  {r.created_at.strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        pdf.ln(2)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Courier", "", 9)
        pdf.multi_cell(0, 4.5, r.text)
        if r.figure_base64:
            img_bytes = base64.b64decode(r.figure_base64)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(img_bytes)
            tmp.close()
            img_w = pdf.w - pdf.l_margin - pdf.r_margin
            pdf.image(tmp.name, w=img_w)
            os.unlink(tmp.name)
        pdf.ln(6)

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    filename = f"statsmed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
