from aiogram import Router

from .overview import router as overview_router
from .upload import router as upload_router
from .ocr import router as ocr_router
from .client_calc import router as client_calc_router
from .cbr_rates import router as cbr_rates_router
from .help import router as help_router
from .main import router as main_router


# Создаем главный роутер для меню
menu_router = Router()

# Подключаем все подмодули
menu_router.include_router(overview_router)
menu_router.include_router(ocr_router)  # OCR должен быть перед upload
menu_router.include_router(upload_router)  # Загрузка после OCR
menu_router.include_router(client_calc_router)
menu_router.include_router(cbr_rates_router)
menu_router.include_router(help_router)
menu_router.include_router(main_router) 