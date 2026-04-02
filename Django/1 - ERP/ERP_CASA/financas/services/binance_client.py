# financas/services/binance_client.py

import time
import hmac
import hashlib
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlencode

import requests
from django.conf import settings

logger = logging.getLogger("financas")


def _d(val, default="0") -> Decimal:
    try:
        if val is None:
            return Decimal(default)
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return Decimal(default)


@dataclass
class BinanceAssetConverted:
    asset: str
    asset_base: str
    free: Decimal
    locked: Decimal
    price_brl: Decimal
    total_brl: Decimal
    price_source: str = ""


class BinanceClientService:
    """
    Serviço Binance (Spot).
    - settings:
        BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_BASE_URL
        BINANCE_RECV_WINDOW (ms), BINANCE_PRICE_CACHE_TTL (s)
    - /api/v3/account (signed)
    - conversão para BRL via ticker:
        assetBRL
        assetUSDT * USDTBRL
        assetBUSD * BUSDBRL (fallback)
        assetBTC * BTCUSDT * USDTBRL
    """

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.base_url = getattr(settings, "BINANCE_BASE_URL", "https://api.binance.com").rstrip("/")
        self.api_key = getattr(settings, "BINANCE_API_KEY", "") or ""
        self.api_secret = getattr(settings, "BINANCE_API_SECRET", "") or ""

        self.recv_window = int(getattr(settings, "BINANCE_RECV_WINDOW", 5000) or 5000)

        self._price_cache: Dict[str, Tuple[Decimal, float]] = {}
        self._cache_ttl = int(getattr(settings, "BINANCE_PRICE_CACHE_TTL", 30) or 30)

        self._min_total_brl_for_warning = _d(getattr(settings, "BINANCE_MIN_TOTAL_BRL_FOR_WARNING", "0"))

        self._session = requests.Session()

    # -------------------------
    # Assinatura correta
    # -------------------------

    def _sign(self, params: Dict) -> str:
        # Binance assina exatamente o query string "como enviado".
        # urlencode preserva a ordem de inserção do dict (Python 3.7+).
        query = urlencode(params, doseq=True)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _get(self, path: str, params: Optional[Dict] = None, signed: bool = False) -> Dict:
        if params is None:
            params = {}

        url = f"{self.base_url}{path}"
        headers = {}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key

        if signed:
            params = dict(params)
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = self.recv_window
            params["signature"] = self._sign(params)

            # lista de tuplas preserva a ordem 100% na URL gerada
            params_to_send = list(params.items())
        else:
            params_to_send = params

        resp = self._session.get(url, params=params_to_send, headers=headers, timeout=self.timeout)
        content_type = (resp.headers.get("Content-Type") or "").lower()

        if resp.status_code >= 400:
            txt = (resp.text or "")[:400]
            raise RuntimeError(f"Binance HTTP {resp.status_code}: {txt}")

        try:
            return resp.json()
        except Exception:
            txt = (resp.text or "")[:400]
            raise RuntimeError(f"Resposta não-JSON da Binance em {path}: {txt}")

    # -------------------------
    # Ticker cache
    # -------------------------

    def _get_ticker_price(self, symbol: str) -> Optional[Decimal]:
        now = time.time()
        cached = self._price_cache.get(symbol)
        if cached and (now - cached[1] < self._cache_ttl):
            return cached[0]

        try:
            data = self._get("/api/v3/ticker/price", params={"symbol": symbol}, signed=False)
            price = _d(data.get("price"))
            self._price_cache[symbol] = (price, now)
            return price
        except Exception as e:
            msg = str(e)
            if "Invalid symbol" in msg or "code=-1121" in msg:
                logger.info(f"[BINANCE] símbolo não existe: {symbol}")
            else:
                logger.info(f"[BINANCE] ticker falhou para {symbol}: {e}")
            return None

    # -------------------------
    # Normalização
    # -------------------------

    def _normalize_asset(self, asset: str) -> str:
        a = (asset or "").upper().strip()
        if not a:
            return a
        if a.startswith("LD") and len(a) > 2:
            return a[2:]
        return a

    # -------------------------
    # Conversão
    # -------------------------

    def _price_in_brl(self, asset_base: str) -> Tuple[Decimal, str]:
        asset_base = asset_base.upper().strip()

        if asset_base == "BRL":
            return Decimal("1"), "BRL"

        p = self._get_ticker_price(f"{asset_base}BRL")
        if p is not None and p > 0:
            return p, f"{asset_base}BRL"

        p_usdt_brl = self._get_ticker_price("USDTBRL")

        p_asset_usdt = self._get_ticker_price(f"{asset_base}USDT")
        if p_asset_usdt is not None and p_usdt_brl is not None and p_asset_usdt > 0 and p_usdt_brl > 0:
            return (p_asset_usdt * p_usdt_brl), f"{asset_base}USDT*USDTBRL"

        p_busd_brl = self._get_ticker_price("BUSDBRL")
        p_asset_busd = self._get_ticker_price(f"{asset_base}BUSD")
        if p_asset_busd is not None and p_busd_brl is not None and p_asset_busd > 0 and p_busd_brl > 0:
            return (p_asset_busd * p_busd_brl), f"{asset_base}BUSD*BUSDBRL"

        p_asset_btc = self._get_ticker_price(f"{asset_base}BTC")
        p_btc_usdt = self._get_ticker_price("BTCUSDT")
        if (
            p_asset_btc is not None and p_btc_usdt is not None and p_usdt_brl is not None
            and p_asset_btc > 0 and p_btc_usdt > 0 and p_usdt_brl > 0
        ):
            return (p_asset_btc * p_btc_usdt * p_usdt_brl), f"{asset_base}BTC*BTCUSDT*USDTBRL"

        return Decimal("0"), "NO_PRICE"

    # -------------------------
    # API principal
    # -------------------------

    def get_balances_converted_brl(self) -> Tuple[Decimal, List[BinanceAssetConverted], Dict]:
        meta = {"warnings": [], "info": []}

        if not self.api_key or not self.api_secret:
            meta["warnings"].append("BINANCE_API_KEY/BINANCE_API_SECRET não configuradas no ambiente.")
            return Decimal("0"), [], meta

        _ = self._get_ticker_price("USDTBRL")

        try:
            data = self._get("/api/v3/account", signed=True)
        except Exception as e:
            msg = str(e)
            if "code=-1021" in msg or "Timestamp for this request" in msg:
                meta["warnings"].append(
                    "Erro de timestamp (-1021). Verifique NTP/clock do servidor "
                    f"ou aumente BINANCE_RECV_WINDOW (atual: {self.recv_window}ms)."
                )
            meta["warnings"].append(f"Falha ao consultar /account: {msg}")
            return Decimal("0"), [], meta

        balances = data.get("balances", []) or []

        detalhes: List[BinanceAssetConverted] = []
        total_brl = Decimal("0")

        for b in balances:
            asset = (b.get("asset") or "").upper().strip()
            free = _d(b.get("free"))
            locked = _d(b.get("locked"))
            qty = free + locked
            if qty <= 0:
                continue

            asset_base = self._normalize_asset(asset)

            price_brl, source = self._price_in_brl(asset_base)
            total_asset_brl = (qty * price_brl).quantize(Decimal("0.00000001"))

            if price_brl <= 0:
                if self._min_total_brl_for_warning <= 0 or total_asset_brl >= self._min_total_brl_for_warning:
                    meta["warnings"].append(f"Sem preço para {asset} (base {asset_base}).")
                total_asset_brl = Decimal("0")

            detalhes.append(
                BinanceAssetConverted(
                    asset=asset,
                    asset_base=asset_base,
                    free=free,
                    locked=locked,
                    price_brl=price_brl,
                    total_brl=total_asset_brl,
                    price_source=source,
                )
            )
            total_brl += total_asset_brl

        detalhes.sort(key=lambda x: x.total_brl, reverse=True)
        meta["info"].append(f"Ativos com saldo > 0: {len(detalhes)}")
        meta["info"].append(f"Cache TTL preços: {self._cache_ttl}s")

        return total_brl.quantize(Decimal("0.01")), detalhes, meta
