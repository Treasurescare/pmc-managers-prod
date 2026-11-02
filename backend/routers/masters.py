"""Master data CRUD: Companies, Roles, Approval Matrices, Categories."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from pydantic import BaseModel, Field

from db import db
from models.masters import CompanyIn, RoleIn, ApprovalMatrixIn
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/masters", tags=["masters"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# ---------- Categories (v50g — procurement category master) ----------
# Backs the Category dropdown on Notices and Tender Builder. Seeded on
# startup from UNSPSC taxonomy; team can edit / add / disable as needed.

class CategoryIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=200)
    name_ru: Optional[str] = None
    name_kz: Optional[str] = None
    country_scope: Optional[List[str]] = None  # None/[] = all countries
    required_licences: Optional[List[str]] = None
    parent_code: Optional[str] = None
    unspsc_code: Optional[str] = None
    source: Optional[str] = "manual"  # 'unspsc' | 'manual'
    is_active: bool = True


@router.get("/categories")
async def list_categories(
    country: Optional[str] = None,
    include_inactive: bool = False,
    admin=Depends(require_role("admin", "reviewer", "support", "committee_member")),
) -> List[dict]:
    q: dict = {}
    if not include_inactive:
        q["is_active"] = True
    if country:
        cu = country.upper()
        q["$or"] = [
            {"country_scope": {"$in": [cu]}},
            {"country_scope": {"$exists": False}},
            {"country_scope": None},
            {"country_scope": []},
        ]
    rows = [_out(r) async for r in db.categories.find(q).sort("name", 1)]
    return rows


@router.get("/categories/public")
async def list_categories_public(country: Optional[str] = None) -> List[dict]:
    """PUBLIC — used by vendor registration + public notice board filters."""
    q: dict = {"is_active": True}
    if country:
        cu = country.upper()
        q["$or"] = [
            {"country_scope": {"$in": [cu]}},
            {"country_scope": {"$exists": False}},
            {"country_scope": None},
            {"country_scope": []},
        ]
    rows = [_out(r) async for r in db.categories.find(q).sort("name", 1)]
    return rows


@router.post("/categories")
async def create_category(
    payload: CategoryIn,
    admin=Depends(require_role("admin")),
) -> dict:
    if await db.categories.find_one({"code": payload.code}):
        raise HTTPException(status_code=409, detail="Category code already exists")
    doc = payload.model_dump()
    doc.update({"created_at": now_iso(), "created_by": admin["id"]})
    res = await db.categories.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("category.create", admin, "category", payload.code,
                    {"name": payload.name})
    return _out(doc)


@router.patch("/categories/{category_id}")
async def update_category(
    category_id: str,
    payload: CategoryIn,
    admin=Depends(require_role("admin")),
) -> dict:
    r = await db.categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {**payload.model_dump(), "updated_at": now_iso()}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.categories.find_one({"_id": ObjectId(category_id)})
    await audit_log("category.update", admin, "category", payload.code,
                    {"name": payload.name})
    return _out(doc)


_STOP = {"and", "or", "for", "of", "the", "&", "works", "work", "procurement", "installation", "system", "systems",
         "amc", "blocks", "main", "external", "ht/lt", "(wtp)", "(stp)", "(ots)", "(hydrants)", "hostel", "hotel", "academic"}


async def _suggest_unspsc(name: str) -> list:
    from routers.masters_v2 import _rank, _title_match_regex
    words = [w.strip("()/,").lower() for w in name.replace("&", " ").split()]
    words = [w for w in words if len(w) > 2 and w not in _STOP]
    seen, rows = set(), []
    for term in [" ".join(words)] + words:
        if not term:
            continue
        q = {"is_active": True, "level": {"$in": ["commodity", "class"]},
             "title_en": {"$regex": _title_match_regex(term), "$options": "i"}}
        async for d in db.masters_unspsc.find(q, {"_id": 0, "code": 1, "title_en": 1, "level": 1, "segment": 1}).limit(300):
            if d["code"] not in seen:
                seen.add(d["code"])
                hits = sum(w in d["title_en"].lower() for w in words)
                rows.append({**d, "_hits": hits})
    rows.sort(key=lambda d: -d["_hits"])
    top = [r for r in rows if r["_hits"] == (rows[0]["_hits"] if rows else 0)]
    best = _rank(top, words[0] if words else name, 3) + _rank([r for r in rows if r not in top], name, 3)
    return [{"code": r["code"], "title": r["title_en"], "level": r.get("level")} for r in best[:3]]


@router.get("/categories/unspsc-suggestions")
async def unspsc_suggestions(admin=Depends(require_role("admin"))) -> list:
    out = []
    async for c in db.categories.find({"is_active": {"$ne": False}, "$or": [
            {"unspsc_code": None}, {"unspsc_code": ""}, {"unspsc_code": {"$exists": False}}]}).sort("name", 1):
        out.append({"id": str(c["_id"]), "name": c["name"], "code": c.get("code"), "suggestions": await _suggest_unspsc(c["name"])})
    return out


class UnspscApproveIn(BaseModel):
    unspsc_code: str = Field(..., min_length=2, max_length=12)


@router.post("/categories/{category_id}/approve-unspsc")
async def approve_unspsc(category_id: str, body: UnspscApproveIn, admin=Depends(require_role("admin"))) -> dict:
    u = await db.masters_unspsc.find_one({"code": body.unspsc_code}, {"title_en": 1})
    if not u:
        raise HTTPException(status_code=422, detail="Unknown UNSPSC code")
    r = await db.categories.update_one({"_id": ObjectId(category_id)},
                                       {"$set": {"unspsc_code": body.unspsc_code, "unspsc_title": u["title_en"], "updated_at": now_iso()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await audit_log("category.unspsc_approved", admin, "category", category_id, {"unspsc_code": body.unspsc_code})
    return _out(await db.categories.find_one({"_id": ObjectId(category_id)}))



@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    admin=Depends(require_role("admin")),
) -> dict:
    doc = await db.categories.find_one({"_id": ObjectId(category_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    # Soft delete — flip is_active to False to preserve historical references.
    await db.categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {"is_active": False, "updated_at": now_iso()}},
    )
    await audit_log("category.deactivate", admin, "category",
                    doc.get("code", ""), {"name": doc.get("name", "")})
    return {"ok": True, "deactivated": True}


# ---------- Sectors & Contract Types (v56q — taxonomy above UNSPSC) ----------
# Two 2-level masters: Sector (industry/domain) -> Contract Type (delivery
# model) -> UNSPSC commodity code. Own collections so they never pollute the
# UNSPSC category pickers.

class TaxonomyIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=48)
    name: str = Field(..., min_length=1, max_length=200)
    parent_code: Optional[str] = None
    is_active: bool = True
    source: Optional[str] = "manual"


async def _tax_list(coll, include_inactive: bool) -> List[dict]:
    q: dict = {} if include_inactive else {"is_active": True}
    return [_out(r) async for r in coll.find(q).sort("name", 1)]


async def _tax_create(coll, kind: str, payload: "TaxonomyIn", admin) -> dict:
    if await coll.find_one({"code": payload.code}):
        raise HTTPException(status_code=409, detail=f"{kind} code already exists")
    doc = payload.model_dump()
    doc.update({"created_at": now_iso(), "created_by": admin["id"]})
    res = await coll.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log(f"{kind}.create", admin, kind, payload.code, {"name": payload.name})
    return _out(doc)


async def _tax_update(coll, kind: str, tid: str, payload: "TaxonomyIn", admin) -> dict:
    r = await coll.update_one({"_id": ObjectId(tid)},
                              {"$set": {**payload.model_dump(), "updated_at": now_iso()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await audit_log(f"{kind}.update", admin, kind, payload.code, {"name": payload.name})
    return _out(await coll.find_one({"_id": ObjectId(tid)}))


async def _tax_delete(coll, kind: str, tid: str, admin) -> dict:
    doc = await coll.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await coll.update_one({"_id": ObjectId(tid)},
                          {"$set": {"is_active": False, "updated_at": now_iso()}})
    await audit_log(f"{kind}.deactivate", admin, kind, doc.get("code", ""),
                    {"name": doc.get("name", "")})
    return {"ok": True, "deactivated": True}


@router.post("/dedupe-taxonomy")
async def dedupe_taxonomy(admin=Depends(require_role("admin"))) -> dict:
    """v56u — remove duplicate taxonomy rows (same `code`) from sectors,
    contract_types and categories, keeping the earliest document per code.
    Idempotent and non-destructive to unique data; returns duplicates deleted
    per collection."""
    result = {}
    for name, coll in (("sectors", db.sectors),
                       ("contract_types", db.contract_types),
                       ("categories", db.categories)):
        seen = set()
        dup_ids = []
        async for doc in coll.find({}, {"_id": 1, "code": 1}).sort("_id", 1):
            code = doc.get("code")
            if code in seen:
                dup_ids.append(doc["_id"])
            else:
                seen.add(code)
        if dup_ids:
            await coll.delete_many({"_id": {"$in": dup_ids}})
        result[name] = len(dup_ids)
    await audit_log("masters.dedupe_taxonomy", admin, "masters", "taxonomy", result)
    return {"ok": True, "deleted": result}


@router.get("/sectors")
async def list_sectors(include_inactive: bool = False,
                       admin=Depends(require_role("admin", "reviewer", "support", "committee_member"))) -> List[dict]:
    return await _tax_list(db.sectors, include_inactive)


@router.get("/sectors/public")
async def list_sectors_public() -> List[dict]:
    """PUBLIC — vendor registration + public notice board filters."""
    return await _tax_list(db.sectors, False)


@router.post("/sectors")
async def create_sector(payload: TaxonomyIn, admin=Depends(require_role("admin"))) -> dict:
    return await _tax_create(db.sectors, "sector", payload, admin)


@router.patch("/sectors/{tid}")
async def update_sector(tid: str, payload: TaxonomyIn, admin=Depends(require_role("admin"))) -> dict:
    return await _tax_update(db.sectors, "sector", tid, payload, admin)


@router.delete("/sectors/{tid}")
async def delete_sector(tid: str, admin=Depends(require_role("admin"))) -> dict:
    return await _tax_delete(db.sectors, "sector", tid, admin)


@router.get("/contract-types")
async def list_contract_types(include_inactive: bool = False,
                              admin=Depends(require_role("admin", "reviewer", "support", "committee_member"))) -> List[dict]:
    return await _tax_list(db.contract_types, include_inactive)


@router.get("/contract-types/public")
async def list_contract_types_public() -> List[dict]:
    """PUBLIC — vendor registration + public notice board filters."""
    return await _tax_list(db.contract_types, False)


@router.post("/contract-types")
async def create_contract_type(payload: TaxonomyIn, admin=Depends(require_role("admin"))) -> dict:
    return await _tax_create(db.contract_types, "contract_type", payload, admin)


@router.patch("/contract-types/{tid}")
async def update_contract_type(tid: str, payload: TaxonomyIn, admin=Depends(require_role("admin"))) -> dict:
    return await _tax_update(db.contract_types, "contract_type", tid, payload, admin)


@router.delete("/contract-types/{tid}")
async def delete_contract_type(tid: str, admin=Depends(require_role("admin"))) -> dict:
    return await _tax_delete(db.contract_types, "contract_type", tid, admin)


# ---------- Companies ----------

@router.get("/companies")
async def list_companies(admin=Depends(require_role("admin", "reviewer"))) -> List[dict]:
    return [_out(c) async for c in db.companies.find({}).sort("name", 1)]


@router.post("/companies")
async def create_company(payload: CompanyIn, admin=Depends(require_role("admin"))) -> dict:
    if await db.companies.find_one({"code": payload.code}):
        raise HTTPException(status_code=409, detail="Company code already exists")
    doc = payload.model_dump()
    doc.update({"documents": {}, "licenses": [],
                "created_at": now_iso(), "created_by": admin["id"]})
    res = await db.companies.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("company.create", admin, "company", payload.code, {"name": payload.name})
    return _out(doc)


@router.patch("/companies/{company_id}")
async def update_company(company_id: str, payload: CompanyIn,
                         admin=Depends(require_role("admin"))) -> dict:
    # v56 — profile-only update. `documents`/`licenses` are NOT in CompanyIn,
    # so this $set can never clear uploaded files.
    r = await db.companies.update_one({"_id": ObjectId(company_id)},
                                      {"$set": {**payload.model_dump(),
                                                "updated_at": now_iso()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await audit_log("company.update", admin, "company", payload.code, {"name": payload.name})
    return _out(await db.companies.find_one({"_id": ObjectId(company_id)}))


# ---------- Company documents (v56) ----------
# Single upload slot each for Incorporation Certificate, MOA and AOA; Licenses
# are a repeatable list (multiple files). Files are uploaded via the shared
# /uploads flow (scope="company-docs"); we persist only the storage key + meta.

COMPANY_DOC_SLOTS = {"incorporation_certificate", "moa", "aoa"}


class CompanyDocIn(BaseModel):
    key: str
    filename: str
    content_type: Optional[str] = None


class CompanyLicenseIn(CompanyDocIn):
    label: Optional[str] = None


async def _get_company_or_404(company_id: str) -> dict:
    try:
        doc = await db.companies.find_one({"_id": ObjectId(company_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed company id")
    if not doc:
        raise HTTPException(status_code=404, detail="Company not found")
    return doc


@router.put("/companies/{company_id}/documents/{slot}")
async def set_company_document(company_id: str, slot: str, payload: CompanyDocIn,
                               admin=Depends(require_role("admin"))) -> dict:
    if slot not in COMPANY_DOC_SLOTS:
        raise HTTPException(status_code=422,
            detail=f"Unknown document slot '{slot}'")
    await _get_company_or_404(company_id)
    meta = {"key": payload.key, "filename": payload.filename,
            "content_type": payload.content_type, "uploaded_at": now_iso(),
            "uploaded_by": admin.get("email")}
    await db.companies.update_one({"_id": ObjectId(company_id)},
                                  {"$set": {f"documents.{slot}": meta,
                                            "updated_at": now_iso()}})
    await audit_log("company.document_set", admin, "company", company_id,
                    {"slot": slot, "filename": payload.filename})
    return _out(await db.companies.find_one({"_id": ObjectId(company_id)}))


@router.delete("/companies/{company_id}/documents/{slot}")
async def delete_company_document(company_id: str, slot: str,
                                  admin=Depends(require_role("admin"))) -> dict:
    await _get_company_or_404(company_id)
    await db.companies.update_one({"_id": ObjectId(company_id)},
                                  {"$unset": {f"documents.{slot}": ""},
                                   "$set": {"updated_at": now_iso()}})
    await audit_log("company.document_delete", admin, "company", company_id,
                    {"slot": slot})
    return _out(await db.companies.find_one({"_id": ObjectId(company_id)}))


@router.post("/companies/{company_id}/licenses")
async def add_company_license(company_id: str, payload: CompanyLicenseIn,
                              admin=Depends(require_role("admin"))) -> dict:
    await _get_company_or_404(company_id)
    lic = {"key": payload.key, "filename": payload.filename,
           "content_type": payload.content_type, "label": payload.label,
           "uploaded_at": now_iso(), "uploaded_by": admin.get("email")}
    await db.companies.update_one({"_id": ObjectId(company_id)},
                                  {"$push": {"licenses": lic},
                                   "$set": {"updated_at": now_iso()}})
    await audit_log("company.license_add", admin, "company", company_id,
                    {"filename": payload.filename, "label": payload.label})
    return _out(await db.companies.find_one({"_id": ObjectId(company_id)}))


@router.delete("/companies/{company_id}/licenses/{index}")
async def delete_company_license(company_id: str, index: int,
                                 admin=Depends(require_role("admin"))) -> dict:
    doc = await _get_company_or_404(company_id)
    lics = doc.get("licenses") or []
    if index < 0 or index >= len(lics):
        raise HTTPException(status_code=404, detail="License not found")
    removed = lics.pop(index)
    await db.companies.update_one({"_id": ObjectId(company_id)},
                                  {"$set": {"licenses": lics,
                                            "updated_at": now_iso()}})
    await audit_log("company.license_delete", admin, "company", company_id,
                    {"filename": removed.get("filename")})
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


# v52cx — delete an approval matrix. Blocks deletion if any notice still
# references it so a running approval chain can't suddenly lose its spine.
@router.delete("/approval-matrices/{matrix_id}")
async def delete_matrix(matrix_id: str,
                        admin=Depends(require_role("admin"))) -> dict:
    doc = await db.approval_matrices.find_one({"_id": ObjectId(matrix_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    in_use = await db.notices.count_documents({"approval_matrix_id": matrix_id})
    if in_use:
        raise HTTPException(status_code=409,
            detail=f"{in_use} notice(s) still use this matrix. Reassign them before deleting.")
    await db.approval_matrices.delete_one({"_id": ObjectId(matrix_id)})
    await audit_log("approval_matrix.delete", admin, "approval_matrix",
                    doc.get("name") or matrix_id, {})
    return {"ok": True, "deleted": matrix_id}
