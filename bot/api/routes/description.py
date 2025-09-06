from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse
from services.product.storage import ProductStorageService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/description", tags=["description"])

MAX_JSON_SIZE = 128 * 1024  # 128 КБ

@router.post("/upload")
async def upload_description(request: Request):
    # Проверка размера тела запроса
    body = await request.body()
    if len(body) > MAX_JSON_SIZE:
        logger.warning(f"Превышен размер JSON: {len(body)} байт")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Превышен максимальный размер JSON: {MAX_JSON_SIZE // 1024} КБ"
        )
    # Проверка структуры JSON
    try:
        json_data = await request.json()
    except Exception as e:
        logger.warning(f"Невалидный JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный JSON в теле запроса"
        )
    # Загрузка в IPFS/Arweave
    storage_service = ProductStorageService()
    cid = storage_service.upload_json(json_data)
    if not cid:
        logger.error("Ошибка загрузки JSON в IPFS/Arweave")
        raise HTTPException(status_code=500, detail="Ошибка загрузки JSON в хранилище")
    logger.info(f"JSON-описание успешно загружено, CID: {cid}")
    return JSONResponse({
        "cid": cid,
        "status": "success"
    }) 