"""
Quality control: operations (name + API key) and functions that run on incoming data.
CRUD requires auth; POST /run uses API key in header.
"""
import json
import secrets
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.database import get_db
from ..db.models import User, QualityControlOperation, QualityControlFunction
from ..auth import get_current_user
from ..services.quality_engine import run_quality_checks

router = APIRouter(prefix="/api/quality", tags=["quality"])


# ----- Schemas -----

class OperationCreate(BaseModel):
    name: str


class OperationResponse(BaseModel):
    id: int
    name: str
    api_key: Optional[str] = None  # only on create or when explicitly requested
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
    return [
        OperationResponse(id=op.id, name=op.name, api_key=op.api_key, created_at=op.created_at.isoformat())
        for op in ops
    ]


@router.get("/operations/{operation_id}", response_model=OperationResponse)
def get_operation(
    operation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    op = ensure_user_owns_operation(db, current_user, operation_id)
    return OperationResponse(
        id=op.id,
        name=op.name,
        api_key=op.api_key,
        created_at=op.created_at.isoformat(),
    )


@router.patch("/operations/{operation_id}", response_model=OperationResponse)
def update_operation(
    operation_id: int,
    body: OperationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    op = ensure_user_owns_operation(db, current_user, operation_id)
    name = (body.name or "").strip()
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
    db.commit()
    db.refresh(op)
    return OperationResponse(id=op.id, name=op.name, api_key=op.api_key, created_at=op.created_at.isoformat())


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
    return {
        "operation_id": operation.id,
        "operation_name": operation.name,
        "success": all_passed,
        "results": results,
    }
