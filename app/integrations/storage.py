import psycopg2
from psycopg2.extensions import lobject
from app.config import get_settings
import structlog

settings = get_settings()
logger = structlog.get_logger()

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
FILE_SIGNATURES = {
    b"%PDF":       "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG":    "image/png"
}


def validate_file_signature(content: bytes, claimed_type: str) -> bool:
    """Verify file bytes match the claimed MIME type (magic bytes check)."""
    for sig, mime in FILE_SIGNATURES.items():
        if content.startswith(sig) and mime == claimed_type:
            return True
    return False


def store_prescription(
    file_bytes: bytes,
    filename: str,
    content_type: str
) -> int:
    """
    Store file as PostgreSQL large object.
    Returns the OID (integer) to save in blood_requests.prescription_oid.
    """
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"File type {content_type} not allowed")

    if not validate_file_signature(file_bytes, content_type):
        raise ValueError("File content does not match declared type")

    conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
    conn.autocommit = False
    try:
        lobj = conn.lobject(0, "wb")
        lobj.write(file_bytes)
        oid = lobj.oid
        lobj.close()
        conn.commit()
        logger.info("file_stored", oid=oid, filename=filename, size=len(file_bytes))
        return oid
    except Exception as e:
        conn.rollback()
        logger.error("file_store_failed", error=str(e))
        raise
    finally:
        conn.close()


def retrieve_prescription(oid: int) -> bytes:
    """Read a stored large object by OID."""
    conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
    try:
        lobj = conn.lobject(oid, "rb")
        data = lobj.read()
        lobj.close()
        return data
    except Exception as e:
        logger.error("file_retrieve_failed", oid=oid, error=str(e))
        raise
    finally:
        conn.close()


def delete_prescription(oid: int):
    """Permanently delete a large object."""
    conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
    conn.autocommit = False
    try:
        conn.lobject(oid).unlink()
        conn.commit()
        logger.info("file_deleted", oid=oid)
    except Exception as e:
        conn.rollback()
        logger.error("file_delete_failed", oid=oid, error=str(e))
    finally:
        conn.close()
