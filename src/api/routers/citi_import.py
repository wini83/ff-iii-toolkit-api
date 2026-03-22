from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from api.deps_runtime import get_citi_import_runtime
from api.mappers.citi_import import map_preview_to_response
from api.models.citi_import import CitiImportParseResponse, CitiImportTextRequest
from services.citi_import.service import CitiImportService
from services.exceptions import FileNotFound, InvalidFileFormat, InvalidFileId
from services.guards import require_active_user

router = APIRouter(
    prefix="/api/tools/citi",
    tags=["citi-import"],
    dependencies=[Depends(require_active_user)],
)


@router.post(
    "/upload",
    response_model=CitiImportParseResponse,
)
async def upload_citi_text(
    file: UploadFile = File(...),
    include_positive: bool = Query(default=False),
    chunk_size: int = Query(default=60, ge=1, le=1000),
    svc: CitiImportService = Depends(get_citi_import_runtime),
):
    try:
        content = await file.read()
        result = await svc.upload_text_file(
            filename=file.filename,
            file_bytes=content,
            include_positive=include_positive,
            chunk_size=chunk_size,
        )
        return map_preview_to_response(result)
    except InvalidFileFormat as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/parse-text",
    response_model=CitiImportParseResponse,
)
async def parse_citi_text(
    payload: CitiImportTextRequest,
    svc: CitiImportService = Depends(get_citi_import_runtime),
):
    result = await svc.parse_text(
        raw_text=payload.text,
        include_positive=payload.include_positive,
        chunk_size=payload.chunk_size,
    )
    return map_preview_to_response(result)


@router.get(
    "/files/{file_id}",
    response_model=CitiImportParseResponse,
)
async def get_citi_file(
    file_id: str,
    svc: CitiImportService = Depends(get_citi_import_runtime),
):
    try:
        result = await svc.get_file(file_id=file_id)
        return map_preview_to_response(result)
    except InvalidFileId as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFound as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc


@router.post("/files/{file_id}/export-csv")
async def export_citi_csv(
    file_id: str,
    svc: CitiImportService = Depends(get_citi_import_runtime),
):
    try:
        payload = await svc.export_csv_zip(file_id=file_id)
    except InvalidFileId as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFound as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc

    return StreamingResponse(
        payload.content,
        media_type=payload.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{payload.filename}"',
        },
    )
