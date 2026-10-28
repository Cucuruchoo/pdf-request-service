from typing import Annotated

import httpx
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)

from app.api.dependencies import get_request_service
from app.application.request_service import RequestService
from app.domain.errors import PdfValidationError, UpstreamError
from app.schemas.documents import DocumentResponse, DocumentUpdateRequest

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
Service = Annotated[RequestService, Depends(get_request_service)]


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def upload_document(
    request: Request,
    service: Service,
    filename: Annotated[str, Header(alias="X-Filename")],
) -> dict:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type != "application/pdf":
        raise HTTPException(
            status_code=415, detail="Content-Type must be application/pdf."
        )

    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > service.max_pdf_size_bytes:
            raise HTTPException(
            status_code=413, detail="PDF exceeds maximum allowed size."
        )

    try:
        return await service.upload(bytes(data), filename)
    except PdfValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except UpstreamError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    except (httpx.RequestError, ValueError, KeyError) as error:
        raise HTTPException(
            status_code=502, detail="Upstream service unavailable or invalid response."
        ) from error


@router.get("", response_model=list[DocumentResponse])
async def list_documents(service: Service) -> list[dict]:
    try:
        return await service.list_all()
    except (httpx.RequestError, UpstreamError) as error:
        _raise_upstream_exception(error)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, service: Service) -> dict:
    try:
        return await service.get(document_id)
    except (httpx.RequestError, UpstreamError) as error:
        _raise_upstream_exception(error)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    payload: DocumentUpdateRequest,
    service: Service,
) -> dict:
    try:
        changes = payload.model_dump(exclude_none=True)
        return await service.update(document_id, changes)
    except (httpx.RequestError, UpstreamError) as error:
        _raise_upstream_exception(error)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, service: Service) -> Response:
    try:
        await service.delete(document_id)
        return Response(status_code=204)
    except (httpx.RequestError, UpstreamError) as error:
        _raise_upstream_exception(error)


def _raise_upstream_exception(error: Exception) -> None:
    if isinstance(error, UpstreamError):
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    raise HTTPException(
        status_code=502, detail="Upstream service unavailable."
    ) from error
