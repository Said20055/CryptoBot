"""
Агрегатор всех хендлеров.
Импортируй `router` в main.py и передавай dp.include_router(router).
"""

from aiogram import Router

from .start import router as start_router
from .promo import router as promo_router
from .referral import router as referral_router
from .trade import router as trade_router
from .orders import router as orders_router
from .lottery import router as lottery_router
from .proxy import private_router, group_router
from .admin import router as admin_router

router = Router()
router.include_routers(
    start_router,
    promo_router,
    referral_router,
    trade_router,
    orders_router,
    lottery_router,
    private_router,
    group_router,
    admin_router,
)
