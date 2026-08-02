"""Master data CRUD: Companies, Roles, Approval Matrices."""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.masters import CompanyIn, RoleIn, ApprovalMatrixIn
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/masters", tags=["masters"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# ---------- Companies ----------

@router.get("/companies")
async def list_companies(admin=Depends(require_role("admin", "reviewer"))) -> List[dict]:
    return [_out(c) async for c in db.companies.find({}).sort("name", 1)]


@router.post("/companies")
async def create_company(payload: CompanyIn, admin=Depends(require_role("admin"))) -> dict:
    if await db.companies.find_one({"code": payload.code}):
        raise HTTPException(status_code=409, detail="Company code already exists")
    doc = payload.model_dump()
    doc.update({"created_at": now_iso(), "created_by": admin["id"]})
    res = await db.companies.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("company.create", admin, "company", payload.code, {"name": payload.name})
    return _out(doc)


@router.patch("/companies/{company_id}")
async def update_company(company_id: str, payload: CompanyIn,
                         admin=Depends(require_role("admin"))) -> dict:
    r = await db.companies.update_one({"_id": ObjectId(company_id)},
                                      {"$set": payload.model_dump()})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return _out(await db.companies.find_one({"_id": ObjectId(company_id)}))


# ---------- Roles ----------

@router.get("/roles")
async def list_roles(admin=Depends(require_role("admin", "reviewer"))) -> List[dict]:
    return [_out(r) async for r in db.role_master.find({}).sort("code", 1)]


@router.post("/roles")
async def create_role(payload: RoleIn, admin=Depends(require_role("admin"))) -> dict:
    if await db.role_master.find_one({"code": payload.code}):
        raise HTTPException(status_code=409, detail="Role code already exists")
    doc = payload.model_dump()
    doc.update({"created_at": now_iso(), "created_by": admin["id"]})
    res = await db.role_master.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _out(doc)


# ---------- Approval Matrix ----------

@router.get("/approval-matrices")
async def list_matrices(admin=Depends(require_role("admin", "reviewer"))) -> List[dict]:
    return [_out(m) async for m in db.approval_matrices.find({}).sort("name", 1)]


@router.post("/approval-matrices")
async def create_matrix(payload: ApprovalMatrixIn,
                        admin=Depends(require_role("admin"))) -> dict:
    doc = payload.model_dump()
    doc.update({"created_at": now_iso(), "created_by": admin["id"]})
    res = await db.approval_matrices.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("approval_matrix.create", admin, "approval_matrix", payload.name,
                    {"steps": len(payload.steps)})
    return _out(doc)


@router.patch("/approval-matrices/{matrix_id}")
async def update_matrix(matrix_id: str, payload: ApprovalMatrixIn,
                        admin=Depends(require_role("admin"))) -> dict:
    r = await db.approval_matrices.update_one({"_id": ObjectId(matrix_id)},
                                              {"$set": payload.model_dump()})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return _out(await db.approval_matrices.find_one({"_id": ObjectId(matrix_id)}))
