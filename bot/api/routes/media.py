from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from bot.services.product.storage import ProductStorageService
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["media"])

# Допустимые типы файлов и максимальный размер (10 МБ)
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ

@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...)
):
    # Проверка типа файла
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(f"Недопустимый тип файла: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Недопустимый тип файла: {file.content_type}. Разрешены: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )
    # Проверка размера файла
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        logger.warning(f"Превышен размер файла: {len(contents)} байт")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Превышен максимальный размер файла: {MAX_FILE_SIZE // (1024*1024)} МБ"
        )
    # Сохраняем файл во временный файл для передачи в сервисный слой
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)
    try:
        storage_service = ProductStorageService()
        cid = storage_service.upload_media_file(temp_path)
        if not cid:
            logger.error("Ошибка загрузки файла в IPFS/Arweave")
            raise HTTPException(status_code=500, detail="Ошибка загрузки файла в хранилище")
        logger.info(f"Файл {file.filename} успешно загружен, CID: {cid}")
        return JSONResponse({
            "cid": cid,
            "filename": file.filename,
            "status": "success"
        })
    finally:
        # Удаляем временный файл
        try:
            os.remove(temp_path)
        except Exception:
            pass 