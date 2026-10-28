import hashlib

from app.domain.errors import PdfValidationError


def validate_pdf(data: bytes, filename: str, max_size: int) -> None:
    if not filename.lower().endswith(".pdf"):
        raise PdfValidationError("File name must end in .pdf.")
    if not data:
        raise PdfValidationError("The uploaded PDF is empty.")
    if len(data) > max_size:
        raise PdfValidationError("PDF exceeds maximum allowed size.")
    if not data.startswith(b"%PDF-"):
        raise PdfValidationError("Invalid PDF signature.")


def calculate_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
