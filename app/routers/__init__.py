from aiogram import Router

from app.handlers.browse import router as browse_router
from app.handlers.checkdocs import router as checkdocs_router
from app.handlers.client_calc import router as client_calc_router
from app.handlers.menu import menu_router  # Используем новый модульный роутер
from app.handlers.ocr_handler import router as ocr_router
from app.handlers.start import router as start_router
from app.handlers.validate import router as validate_router
from app.middleware.error_handler import ErrorHandlerMiddleware

# Создаем главный роутер
main_router = Router()

# Подключаем middleware для обработки ошибок
main_router.message.middleware(ErrorHandlerMiddleware())
main_router.callback_query.middleware(ErrorHandlerMiddleware())


# Подключаем все роутеры
main_router.include_router(start_router)
main_router.include_router(menu_router)  # Меню должно быть первым для обработки документов
main_router.include_router(ocr_router)
main_router.include_router(validate_router)
main_router.include_router(checkdocs_router)
main_router.include_router(client_calc_router)
main_router.include_router(browse_router)  # Browse должен быть последним как fallback
