from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Form
from app.auth import decode_access_token
from app.db import db
from typing import List
from bson import ObjectId
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
from app.utils.file_utils import extract_text_from_file  # ✅ generalized extractor
from app.llm_utils import summarize_medical_text
import os
import asyncio
from app.utils.metrics_parser import extract_metrics

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ✅ Auth helper
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

# ✅ Upload endpoint with domain, tags, auto-summarization
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    tags: List[str] = Form(default=[]),
    domain: str = Form(default="unknown"),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(token)
    user_id = user["sub"]

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
        f.flush()

    await asyncio.sleep(0.5)

    try:
        text = extract_text_from_file(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {e}")

    # === Summary Logic ===
    if not text.strip():
        summary = "No text found in file — likely a scan or image-only file."
    else:
        try:
            summary = await summarize_medical_text(text)
        except Exception:
            summary = "Summary could not be generated."

    # === Store Record Metadata ===
    record = {
        "user_id": user_id,
        "filename": file.filename,
        "file_type": file.content_type,
        "upload_date": datetime.utcnow(),
        "domain": domain,
        "tags": tags,
        "summary": summary
    }

    await db.health_records.insert_one(record)

    # === Extract and Store Health Metrics ===
    try:
        metrics = extract_metrics(text)
        for metric in metrics:
            metric.update({
                "user_id": user_id,
                "filename": file.filename,
                "upload_date": datetime.utcnow()
            })
        if metrics:
            await db.health_metrics.insert_many(metrics)
    except Exception as e:
        print(f"Metric extraction failed: {e}")

    return {
        "message": "File uploaded, summarized, and metrics extracted successfully",
        "filename": file.filename,
        "summary": summary
    }

# ✅ List file metadata (basic info)
@router.get("/list")
async def list_files(token_data: dict = Depends(get_current_user)):
    user_id = token_data["sub"]
    files_cursor = db.health_records.find({"user_id": user_id})
    files = []
    async for file in files_cursor:
        files.append({
            "filename": file["filename"],
            "upload_date": file["upload_date"],
            "domain": file.get("domain", "unknown"),
            "user_id": str(file["user_id"])
        })
    return files

# ✅ List full file info
@router.get("/files")
async def list_user_files(token: str = Depends(oauth2_scheme)):
    user = await get_current_user(token)
    user_id = user["sub"]
    cursor = db.health_records.find({"user_id": user_id})
    files = []
    async for record in cursor:
        record["_id"] = str(record["_id"])
        files.append(record)
    return {"files": files}

# ✅ Manual summarize (if needed again)
@router.post("/summarize/{file_id}")
async def summarize_report(file_id: str, token: str = Depends(oauth2_scheme)):
    user = await get_current_user(token)
    user_id = user["sub"]

    record = await db.health_records.find_one({
        "_id": ObjectId(file_id),
        "user_id": user_id
    })

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = os.path.join(UPLOAD_DIR, record["filename"])
    text = extract_text_from_file(file_path)

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text found in file")

    summary = await summarize_medical_text(text)

    await db.health_records.update_one(
        {"_id": ObjectId(file_id)},
        {"$set": {"summary": summary}}
    )

    return {"summary": summary}

# ✅ Search with keyword/domain/summary presence
@router.get("/search")
async def search_files(
    token: str = Depends(oauth2_scheme),
    keyword: str = Query(default="", description="Search term"),
    has_summary: bool = Query(default=None),
    domain: str = Query(default=None),
):
    user = await get_current_user(token)
    user_id = user["sub"]

    query = {"user_id": user_id}

    if keyword:
        query["$or"] = [
            {"filename": {"$regex": keyword, "$options": "i"}},
            {"summary": {"$regex": keyword, "$options": "i"}},
        ]

    if domain:
        query["domain"] = domain

    if has_summary is not None:
        query["summary"] = {"$ne": None} if has_summary else None

    cursor = db.health_records.find(query)
    results = []
    async for record in cursor:
        record["_id"] = str(record["_id"])
        results.append(record)

    return {"results": results}

@router.get("/metrics/trend")
async def get_metric_trend(
    metric: str = Query(..., description="Health metric to track (e.g., glucose)"),
    token: str = Depends(oauth2_scheme)
):
    user = await get_current_user(token)
    user_id = user["sub"]

    cursor = db.health_metrics.find(
        {"user_id": user_id, "metric": metric.lower()}
    ).sort("upload_date", 1)

    results = []
    async for entry in cursor:
        results.append({
            "value": entry["value"],
            "unit": entry.get("unit"),
            "date": entry["upload_date"].date().isoformat(),
            "filename": entry.get("filename")
        })

    return {
        "metric": metric,
        "values": results
    }