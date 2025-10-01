# Файл: handlers/admin/__init__.py

from .panel import panel_router
from .broadcast import broadcast_router
from .promo import promo_router
from .orders import orders_router
from ..router import admin_router

admin_router.include_routers(
    panel_router,
    broadcast_router,
    promo_router,
    orders_router
)