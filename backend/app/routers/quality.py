"""
Quality control: operations (name + API key) and functions that run on incoming data.
CRUD requires auth; POST /run uses API key in header.
"""
import json
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.database import get_db
from ..db.models import User, QualityControlOperation, QualityControlFunction, QualityControlRun
from ..auth import get_current_user
from ..services.quality_engine import run_quality_checks

router = APIRouter(prefix="/api/quality", tags=["quality"])


# ----- Schemas -----

class OperationCreate(BaseModel):
    name: str


class OperationUpdate(BaseModel):
    name: Optional[str] = None
    is_public: Optional[bool] = None


class OperationResponse(BaseModel):
    id: int
    name: str
    api_key: Optional[str] = None
    is_public: bool = False
    last_sample_json: Optional[str] = None
    created_at: str


class FunctionCreate(BaseModel):
    name: str
    function_type: str  # "missing", "range", "custom"
    config: Optional[dict] = None
    sort_order: Optional[int] = None


class FunctionUpdate(BaseModel):
    name: Optional[str] = None
    function_type: Optional[str] = None
    config: Optional[dict] = None
    sort_order: Optional[int] = None


class FunctionResponse(BaseModel):
    id: int
    name: str
    function_type: str
    config: Optional[dict] = None
    sort_order: int
    created_at: str


class RunPayload(BaseModel):
    data: list[dict[str, Any]]


def ensure_user_owns_operation(db: Session, user: User, operation_id: int) -> QualityControlOperation:
    op = db.query(QualityControlOperation).filter(
        QualityControlOperation.id == operation_id,
        QualityControlOperation.user_id == user.id,
    ).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")
    return op


# ----- Operations (auth required) -----

@router.post("/operations", response_model=OperationResponse)
def create_operation(
    body: OperationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    existing = db.query(QualityControlOperation).filter(
        QualityControlOperation.user_id == current_user.id,
        QualityControlOperation.name == name,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="An operation with this name already exists")
    api_key = secrets.token_urlsafe(32)
    op = QualityControlOperation(
        user_id=current_user.id,
        name=name,
        api_key=api_key,
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return OperationResponse(
        id=op.id,
        name=op.name,
        api_key=api_key,
        is_public=op.is_public,
        last_sample_json=op.last_sample_json,
        created_at=op.created_at.isoformat(),
    )


def _op_response(op: QualityControlOperation, include_key: bool = True) -> OperationResponse:
    return OperationResponse(
        id=op.id,
        name=op.name,
        api_key=op.api_key if include_key else None,
        is_public=op.is_public,
        last_sample_json=op.last_sample_json,
        created_at=op.created_at.isoformat(),
    )


@router.get("/operations", response_model=list[OperationResponse])
def list_operations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ops = db.query(QualityControlOperation).filter(
        QualityControlOperation.user_id == current_user.id,
    ).order_by(QualityControlOperation.name).all()
    return [_op_response(op) for op in ops]


@router.get("/operations/{operation_id}", response_model=OperationResponse)
def get_operation(
    operation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    op = ensure_user_owns_operation(db, current_user, operation_id)
    return _op_response(op)


@router.patch("/operations/{operation_id}", response_model=OperationResponse)
def update_operation(
    operation_id: int,
    body: OperationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    op = ensure_user_owns_operation(db, current_user, operation_id)
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Name is required")
        if name != op.name:
            existing = db.query(QualityControlOperation).filter(
                QualityControlOperation.user_id == current_user.id,
                QualityControlOperation.name == name,
            ).first()
            if existing:
                raise HTTPException(status_code=409, detail="An operation with this name already exists")
            op.name = name
    if body.is_public is not None:
        op.is_public = body.is_public
    db.commit()
    db.refresh(op)
    return _op_response(op)


@router.delete("/operations/{operation_id}")
def delete_operation(
    operation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    op = ensure_user_owns_operation(db, current_user, operation_id)
    db.delete(op)
    db.commit()
    return {"success": True}


# ----- Functions (auth required) -----

@router.post("/operations/{operation_id}/functions", response_model=FunctionResponse)
def create_function(
    operation_id: int,
    body: FunctionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    op = ensure_user_owns_operation(db, current_user, operation_id)
    sort_order = body.sort_order
    if sort_order is None:
        max_order = db.query(QualityControlFunction).filter(
            QualityControlFunction.operation_id == operation_id,
        ).count()
        sort_order = max_order
    fn = QualityControlFunction(
        operation_id=op.id,
        name=(body.name or "").strip() or "Unnamed",
        function_type=body.function_type or "custom",
        config_json=json.dumps(body.config) if body.config is not None else None,
        sort_order=sort_order,
    )
    db.add(fn)
    db.commit()
    db.refresh(fn)
    return FunctionResponse(
        id=fn.id,
        name=fn.name,
        function_type=fn.function_type,
        config=json.loads(fn.config_json) if fn.config_json else None,
        sort_order=fn.sort_order,
        created_at=fn.created_at.isoformat(),
    )


@router.get("/operations/{operation_id}/functions", response_model=list[FunctionResponse])
def list_functions(
    operation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_owns_operation(db, current_user, operation_id)
    fns = db.query(QualityControlFunction).filter(
        QualityControlFunction.operation_id == operation_id,
    ).order_by(QualityControlFunction.sort_order, QualityControlFunction.id).all()
    return [
        FunctionResponse(
            id=f.id,
            name=f.name,
            function_type=f.function_type,
            config=json.loads(f.config_json) if f.config_json else None,
            sort_order=f.sort_order,
            created_at=f.created_at.isoformat(),
        )
        for f in fns
    ]


@router.patch("/operations/{operation_id}/functions/{function_id}", response_model=FunctionResponse)
def update_function(
    operation_id: int,
    function_id: int,
    body: FunctionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_owns_operation(db, current_user, operation_id)
    fn = db.query(QualityControlFunction).filter(
        QualityControlFunction.id == function_id,
        QualityControlFunction.operation_id == operation_id,
    ).first()
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")
    if body.name is not None:
        fn.name = (body.name or "").strip() or fn.name
    if body.function_type is not None:
        fn.function_type = body.function_type
    if body.config is not None:
        fn.config_json = json.dumps(body.config)
    if body.sort_order is not None:
        fn.sort_order = body.sort_order
    db.commit()
    db.refresh(fn)
    return FunctionResponse(
        id=fn.id,
        name=fn.name,
        function_type=fn.function_type,
        config=json.loads(fn.config_json) if fn.config_json else None,
        sort_order=fn.sort_order,
        created_at=fn.created_at.isoformat(),
    )


@router.delete("/operations/{operation_id}/functions/{function_id}")
def delete_function(
    operation_id: int,
    function_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_owns_operation(db, current_user, operation_id)
    fn = db.query(QualityControlFunction).filter(
        QualityControlFunction.id == function_id,
        QualityControlFunction.operation_id == operation_id,
    ).first()
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")
    db.delete(fn)
    db.commit()
    return {"success": True}


# ----- Run (API key auth) -----

def get_operation_by_api_key(
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> QualityControlOperation:
    if not api_key or not api_key.strip():
        raise HTTPException(status_code=401, detail="X-API-Key header required")
    op = db.query(QualityControlOperation).filter(QualityControlOperation.api_key == api_key.strip()).first()
    if not op:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return op


@router.post("/run")
def run_quality(
    body: RunPayload,
    operation: QualityControlOperation = Depends(get_operation_by_api_key),
    db: Session = Depends(get_db),
):
    """Run this operation's functions on the provided data. Authenticate with header: X-API-Key: <your-key>."""
    data = body.data or []
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="'data' must be a list of objects")
    fns = (
        db.query(QualityControlFunction)
        .filter(QualityControlFunction.operation_id == operation.id)
        .order_by(QualityControlFunction.sort_order, QualityControlFunction.id)
        .all()
    )
    function_specs = []
    for f in fns:
        config = json.loads(f.config_json) if f.config_json else None
        function_specs.append((f.name, f.function_type, config or {}))
    results = run_quality_checks(data, function_specs)
    all_passed = all(r["passed"] for r in results)

    MAX_SAMPLE_ROWS = 100
    operation.last_sample_json = json.dumps(data[:MAX_SAMPLE_ROWS])

    run_record = QualityControlRun(
        operation_id=operation.id,
        success=all_passed,
        results_json=json.dumps(results),
        row_count=len(data),
    )
    db.add(run_record)
    db.commit()

    return {
        "operation_id": operation.id,
        "operation_name": operation.name,
        "success": all_passed,
        "results": results,
    }


# ----- Public read-only endpoints (no auth) -----

@router.get("/public")
def list_public_operations(db: Session = Depends(get_db)):
    """List all QC operations marked as public, with summary of their latest run."""
    ops = (
        db.query(QualityControlOperation)
        .filter(QualityControlOperation.is_public == True)  # noqa: E712
        .order_by(QualityControlOperation.name)
        .all()
    )
    result = []
    for op in ops:
        latest_run = (
            db.query(QualityControlRun)
            .filter(QualityControlRun.operation_id == op.id)
            .order_by(QualityControlRun.created_at.desc())
            .first()
        )
        result.append({
            "id": op.id,
            "name": op.name,
            "owner": op.user.username,
            "created_at": op.created_at.isoformat(),
            "function_count": len(op.functions),
            "latest_run": {
                "id": latest_run.id,
                "success": latest_run.success,
                "row_count": latest_run.row_count,
                "created_at": latest_run.created_at.isoformat(),
            } if latest_run else None,
        })
    return result


@router.get("/public/{operation_id}")
def get_public_operation(operation_id: int, db: Session = Depends(get_db)):
    """Get a single public QC operation with only its latest run results (read-only)."""
    op = db.query(QualityControlOperation).filter(
        QualityControlOperation.id == operation_id,
        QualityControlOperation.is_public == True,  # noqa: E712
    ).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found or not public")
    latest_run = (
        db.query(QualityControlRun)
        .filter(QualityControlRun.operation_id == op.id)
        .order_by(QualityControlRun.created_at.desc())
        .first()
    )
    return {
        "id": op.id,
        "name": op.name,
        "owner": op.user.username,
        "created_at": op.created_at.isoformat(),
        "latest_run": {
            "id": latest_run.id,
            "success": latest_run.success,
            "row_count": latest_run.row_count,
            "results": json.loads(latest_run.results_json),
            "created_at": latest_run.created_at.isoformat(),
        } if latest_run else None,
    }


@router.get("/public/{operation_id}/history")
def get_public_operation_history(operation_id: int, db: Session = Depends(get_db)):
    """Return acceptance-rate time series for a public operation (up to 1 year back)."""
    op = db.query(QualityControlOperation).filter(
        QualityControlOperation.id == operation_id,
        QualityControlOperation.is_public == True,  # noqa: E712
    ).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found or not public")

    cutoff = datetime.utcnow() - timedelta(days=365)
    runs = (
        db.query(QualityControlRun)
        .filter(
            QualityControlRun.operation_id == op.id,
            QualityControlRun.created_at >= cutoff,
        )
        .order_by(QualityControlRun.created_at.asc())
        .all()
    )

    points: list[dict] = []
    for run in runs:
        try:
            results = json.loads(run.results_json)
        except (json.JSONDecodeError, TypeError):
            continue
        for r in results:
            cd = r.get("chart_data")
            if cd and cd.get("type") == "acceptance_bar":
                points.append({
                    "date": run.created_at.isoformat(),
                    "accepted_pct": cd.get("accepted_pct", 0),
                    "rejected_pct": cd.get("rejected_pct", 0),
                    "total": cd.get("total", 0),
                    "run_id": run.id,
                })
                break

    return {"operation_id": op.id, "points": points}
