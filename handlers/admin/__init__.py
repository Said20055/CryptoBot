from aiogram import Router

from .panel import router as panel_router
from .orders import router as orders_router
from .broadcast import router as broadcast_router
from .promo import router as promo_router
from .settings import router as settings_router
from .stats import router as stats_router

router = Router()
router.include_routers(
    panel_router,
    orders_router,
    broadcast_router,
    promo_router,
    settings_router,
    stats_router,
)
