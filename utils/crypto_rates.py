import aiohttp
import asyncio
import time
import ssl
from typing import Dict, Optional
from utils.logging_config import logger

class CryptoRates:
    def __init__(self):
        self.rates = {}
        self.rate_cache = {}  # Кэш курсов с временными метками
        self.cache_duration = 120  # Кэш на 2 минуты
        self.network_fees = {
            'BTC': 0.000057,  # BTC
            'LTC': 0.001,     # LTC
            'TRX': 1.0,       # TRX
            'USDT': 1.0       # USDT (TRC20)
        }
        self.network_fee_rub = 290  # Комиссия сети в рублях
        self.service_commission = 12  # Комиссия сервиса в процентах
    
    def _is_cache_valid(self, crypto: str) -> bool:
        """Проверяет, действителен ли кэш для криптовалюты"""
        if crypto not in self.rate_cache:
            return False
        cache_time = self.rate_cache[crypto]['timestamp']
        return time.time() - cache_time < self.cache_duration
    
    def _get_cached_rate(self, crypto: str) -> Optional[float]:
        """Получает курс из кэша"""
        if self._is_cache_valid(crypto):
            return self.rate_cache[crypto]['rate']
        return None
    
    def _cache_rate(self, crypto: str, rate: float):
        """Сохраняет курс в кэш"""
        self.rate_cache[crypto] = {
            'rate': rate,
            'timestamp': time.time()
        }
    
    async def _make_api_request(self, url: str, crypto: str, max_retries: int = 3) -> Optional[float]:
        """Делает запрос к API с повторными попытками"""
        # Создаем SSL контекст без проверки сертификатов
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        try:
            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession(connector=connector) as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            if response.status == 200:
                                data = await response.json()
                                return data
                            elif response.status == 429:
                                # Rate limit - ждем и повторяем
                                wait_time = (2 ** attempt) * 2  # Экспоненциальная задержка
                                logger.warning(f"Rate limit for {crypto}, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                logger.error(f"API error for {crypto}: {response.status}")
                                if attempt == max_retries - 1:
                                    return None
                                await asyncio.sleep(2)
                                continue
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.error(f"Network error for {crypto} (attempt {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        return None
                    await asyncio.sleep(2)
                    continue
        finally:
            await connector.close()
        
        return None
    
    async def get_btc_rate(self) -> Optional[float]:
        """Получает курс BTC в рублях"""
        # Проверяем кэш
        cached_rate = self._get_cached_rate('BTC')
        if cached_rate is not None:
            logger.info(f"BTC rate from cache: {cached_rate} RUB")
            return cached_rate
        
        # Делаем запрос к API
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=rub"
        data = await self._make_api_request(url, 'BTC')
        
        if data and 'bitcoin' in data and 'rub' in data['bitcoin']:
            rate = data['bitcoin']['rub']
            self._cache_rate('BTC', rate)
            self.rates['BTC'] = rate
            logger.info(f"BTC rate updated: {rate} RUB")
            return rate
        else:
            logger.error("Failed to get BTC rate from API")
            return None
    
    async def get_ltc_rate(self) -> Optional[float]:
        """Получает курс LTC в рублях"""
        # Проверяем кэш
        cached_rate = self._get_cached_rate('LTC')
        if cached_rate is not None:
            logger.info(f"LTC rate from cache: {cached_rate} RUB")
            return cached_rate
        
        # Делаем запрос к API
        url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=rub"
        data = await self._make_api_request(url, 'LTC')
        
        if data and 'litecoin' in data and 'rub' in data['litecoin']:
            rate = data['litecoin']['rub']
            self._cache_rate('LTC', rate)
            self.rates['LTC'] = rate
            logger.info(f"LTC rate updated: {rate} RUB")
            return rate
        else:
            logger.error("Failed to get LTC rate from API")
            return None
    
    async def get_trx_rate(self) -> Optional[float]:
        """Получает курс TRX в рублях"""
        # Проверяем кэш
        cached_rate = self._get_cached_rate('TRX')
        if cached_rate is not None:
            logger.info(f"TRX rate from cache: {cached_rate} RUB")
            return cached_rate
        
        # Делаем запрос к API
        url = "https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=rub"
        data = await self._make_api_request(url, 'TRX')
        
        if data and 'tron' in data and 'rub' in data['tron']:
            rate = data['tron']['rub']
            self._cache_rate('TRX', rate)
            self.rates['TRX'] = rate
            logger.info(f"TRX rate updated: {rate} RUB")
            return rate
        else:
            logger.error("Failed to get TRX rate from API")
            return None
    
    async def get_usdt_rate(self) -> Optional[float]:
        """Получает курс USDT в рублях"""
        # Проверяем кэш
        cached_rate = self._get_cached_rate('USDT')
        if cached_rate is not None:
            logger.info(f"USDT rate from cache: {cached_rate} RUB")
            return cached_rate
        
        # Делаем запрос к API
        url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub"
        data = await self._make_api_request(url, 'USDT')
        
        if data and 'tether' in data and 'rub' in data['tether']:
            rate = data['tether']['rub']
            self._cache_rate('USDT', rate)
            self.rates['USDT'] = rate
            logger.info(f"USDT rate updated: {rate} RUB")
            return rate
        else:
            logger.error("Failed to get USDT rate from API")
            return None
    
    async def get_rate(self, crypto: str) -> Optional[float]:
        """Получает курс указанной криптовалюты"""
        crypto = crypto.upper()
        if crypto == 'BTC':
            return await self.get_btc_rate()
        elif crypto == 'LTC':
            return await self.get_ltc_rate()
        elif crypto == 'TRX':
            return await self.get_trx_rate()
        elif crypto == 'USDT':
            return await self.get_usdt_rate()
        else:
            logger.error(f"Unknown cryptocurrency: {crypto}")
            return None
    
    def calculate_network_fee_rub(self, crypto: str, rate: float) -> float:
        """Рассчитывает комиссию сети в рублях"""
        crypto = crypto.upper()
        if crypto in self.network_fees:
            return self.network_fees[crypto] * rate
        return self.network_fee_rub  # Fallback к фиксированной сумме
    
    def calculate_service_commission(self, amount_rub: float) -> float:
        """Рассчитывает комиссию сервиса"""
        return amount_rub * (self.service_commission / 100)
    
    def calculate_total_amount(self, crypto_amount: float, rate: float) -> Dict[str, float]:
        """Рассчитывает итоговую сумму с учетом всех комиссий"""
        amount_rub = crypto_amount * rate
        service_commission = self.calculate_service_commission(amount_rub)
        network_fee_rub = self.network_fee_rub  # Фиксированная комиссия сети
        
        return {
            'crypto_amount': crypto_amount,
            'rate': rate,
            'amount_rub': amount_rub,
            'service_commission': service_commission,
            'network_fee_rub': network_fee_rub,
            'total_to_pay': amount_rub - service_commission - network_fee_rub
        }

# Глобальный экземпляр для использования в боте
crypto_rates = CryptoRates()

