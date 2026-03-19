# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Telegram cryptocurrency exchange bot built with Python + Aiogram 3.x. Users can buy/sell BTC, TRX, and USDT for Russian Rubles (RUB) via SBP. Includes admin panel, referral system, promo codes, and a daily lottery.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py

# Run in Docker (dev — live code reload via volume mount)
docker-compose up --build

# Inspect the database
python dump_db.py
```

There are no build steps, linters, or automated tests configured.

## Architecture

### Entry Point & Routing

`main.py` initializes the Aiogram `Dispatcher` with `MemoryStorage` (for FSM), registers a **single top-level router** from `handlers`, starts polling, and runs background loops (auto-close stale orders, admin night reminders).

```python
from handlers import router
dp.include_router(router)
```

`handlers/__init__.py` aggregates all sub-routers. **When adding a new handler module, create a `router = Router()` in that module and add it to `handlers/__init__.py`.**

### Handler Modules

| Module | Responsibility |
|---|---|
| `handlers/start.py` | `/start` (incl. referral payload), `back_to_main_menu`, `/profile` |
| `handlers/promo.py` | `/promo`, `activate_promo` callback, FSM promo input (user side) |
| `handlers/referral.py` | Referral earnings history, withdrawal request FSM |
| `handlers/trade.py` | Full buy/sell FSM: crypto selection → amount → requisites → order creation |
| `handlers/orders.py` | Order history with pagination (`OrdersPage` CallbackData) |
| `handlers/lottery.py` | Daily lottery ticket and prize logic |
| `handlers/proxy.py` | Message forwarding: user ↔ operator (two routers: `private_router`, `group_router`) |
| `handlers/admin/panel.py` | `/admin` command, admin panel entry |
| `handlers/admin/orders.py` | Admin confirms/rejects orders via `AdminOrderAction` CallbackData |
| `handlers/admin/broadcast.py` | Broadcast messages to all users |
| `handlers/admin/promo.py` | Create promo codes (admin side) |
| `handlers/admin/settings.py` | Modify bot settings stored in DB |
| `handlers/admin/stats.py` | Statistics dashboard |

### CallbackData classes (`utils/callbacks.py`)

| Class | Prefix | Fields | Usage |
|---|---|---|---|
| `CryptoSelection` | `crypto_select` | `action`, `crypto` | Select BTC/TRX/USDT |
| `RubInputSwitch` | `rub_switch` | `action`, `crypto` | Switch to RUB input |
| `CryptoInputSwitch` | `crypto_switch` | `action`, `crypto` | Switch to crypto input |
| `OrdersPage` | `orders_page` | `page` | Pagination buttons |
| `AdminOrderAction` | `ao` | `action`, `order_id`, `user_id` | Admin confirm/reject |
| `CancelOrder` | `cancel_order` | `order_id` | User cancels own order |

### FSM States (`utils/states.py`)

- `TransactionStates` — buy/sell crypto flow + operator chat mode
- `PromoStates` — promo code input (shared between user activation and admin creation)
- `BroadcastStates` — admin broadcast confirmation
- `ReferralStates` — withdrawal details input

### Database (`utils/database/`)

PostgreSQL accessed via `asyncpg`. Pattern: all handlers use context managers from `db_helpers.py`.

- `connection.py` — asyncpg pool singleton (`init_pool`, `close_pool`, `get_pool`)
- `db_connector.py` — runs Alembic migrations at startup (`run_migrations()`)
- `db_helpers.py` — two context managers only: `transaction()` (write ops, auto-rollback) and `acquire()` (read-only)
- `db_queries.py` — all query functions (parameterized with `$1..$N`)

**Schema tables:** `users`, `orders`, `promo_codes`, `used_promo_codes`, `settings`, `referral_earnings`, `withdrawal_requests`, `lottery_plays`

Migrations live in `migrations/versions/`.

### Utilities

- `config.py` — all env vars; `ORDER_NUMBER_OFFSET = 9999` for display numbers
- `utils/texts.py` — **text only** (Russian). No keyboard builders here.
- `utils/keyboards.py` — **all** inline keyboard builders using `InlineKeyboardBuilder`
- `utils/crypto_rates.py` — live crypto prices with 120s cache and backoff
- `utils/filters.py` — `AdminFilter` checks `from_user.id` against `ADMIN_CHAT_IDS`
- `utils/helpers.py` — `calculate_lottery_win()`, `format_timedelta()`

### Configuration (`.env`)

Key variables (see `config.py` for full list):
```
TELEGRAM_BOT_TOKEN
ADMIN_CHAT_IDS              # comma-separated
SUPPORT_GROUP_ID            # group where order topics are created
DATABASE_URL                # postgresql://user:pass@host:5432/db
WALLET_BTC / WALLET_TRX / WALLET_USDT
NETWORK_FEE_RUB             # default 300
SERVICE_COMMISSION_PERCENT  # default 15
SBP_PHONE / SBP_BANK
ORDER_AUTO_CLOSE_MINUTES    # default 15
```

## Key Patterns

- **DB access**: always `async with transaction() as conn:` for writes, `async with acquire() as conn:` for reads. Pass `conn` to `db_queries` functions.
- **Admin check**: `AdminFilter` applied per-router in each `handlers/admin/*.py` file.
- **Referral payouts**: triggered in `handlers/admin/orders.py` on order confirmation.
- **Auto-close loop**: runs in `main.py`, warns users 5 min before, closes at timeout.
- **Forum topics**: each order and each withdrawal request gets its own topic in `SUPPORT_GROUP_ID`.
- **Promo types**: `discount_type = 'percent'` or `'fixed'` (RUB). Logic in `handlers/trade.py`.
