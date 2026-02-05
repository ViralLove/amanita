# Routes module for AMANITA API
from .products import router as products_router
from .media import router as media_router
from .description import router as description_router
from .activities import router as activities_router
from .reference import router as reference_router
from . import uploads
