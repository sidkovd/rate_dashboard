# fx_dashboard_app.py — Полный перенос логики из PHP в Python (Streamlit)
# macOS: pip install streamlit requests pandas pydantic python-dotenv
# Запуск: streamlit run main.py

import hmac
import hashlib
import time
import os
from typing import Dict, Any, Optional

import requests
import streamlit as st
import pandas as pd
from pydantic import BaseModel
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

st.set_page_config(page_title="FX Dashboard (Python-only)", layout="wide")
st.title("💱 FX Dashboard — Python only")
st.caption("Курсы из Bitkub + Rapira без PHP, расчёт маржи и производных прямо в Python.")

# ---------- Конфиг в сайдбаре ----------
st.sidebar.header("🔧 Источники API")
rapira_url = st.sidebar.text_input(
    "Rapira rates endpoint",
    value=os.getenv("RAPIRA_URL", "https://api.rapira.net/open/market/rates"),
)

bitkub_server_time_url = st.sidebar.text_input(
    "Bitkub server time",
    value=os.getenv("BITKUB_SERVER_TIME_URL", "https://api.bitkub.com/api/servertime"),
)
bitkub_ticker_url = st.sidebar.text_input(
    "Bitkub ticker (THB_USDT)",
    value=os.getenv("BITKUB_TICKER_URL", "https://api.bitkub.com/api/market/ticker?sym=THB_USDT"),
)

st.sidebar.subheader("Bitkub auth (опционально)")
bitkub_api_key = st.sidebar.text_input("X-BTK-APIKEY", value=os.getenv("BITKUB_API_KEY", ""), type="password")
bitkub_api_secret = st.sidebar.text_input("X-BTK-SECRET", value=os.getenv("BITKUB_API_SECRET", ""), type="password")

st.sidebar.subheader("Нормализация Bitkub")
subtract_const = st.sidebar.number_input("Вычесть константу из THB_USDT", value=float(os.getenv("SUBTRACT_CONST", "0.1")), step=0.01)

st.sidebar.subheader("Маржа по умолчанию")
default_margin = st.sidebar.number_input("% маржи (по умолчанию)", value=float(os.getenv("DEFAULT_MARGIN", "3.5")), step=0.1)

# ---------- Модели и утилиты ----------
class FxResult(BaseModel):
    usd_rub_base: float
    usd_rub_plus_3_5: float
    usd_rub_plus_7: float

    thb_usd: float
    thb_usd_2_5: float
    thb_usd_2_75: float
    thb_usd_3: float

    conversion_rate_base: float  # RUB/THB без маржи
    conversion_rate_plus_3_5: float
    conversion_rate_plus_4: float
    conversion_rate_plus_5: float
    conversion_rate_plus_6: float
    conversion_rate_plus_7: float

    rate: float  # основной (с 3.5%)


def sign_bitkub(timestamp: str, method: str, path_and_query: str, secret: str) -> str:
    payload = f"{timestamp}{method}{path_and_query}"
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def fetch_bitkub_thb_usdt(
    server_time_url: str,
    ticker_url: str,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> float:
    """Возвращает цену THB_USDT['last']. Если не удаётся без подписи, пробует с подписью (если переданы ключи)."""
    # 1) Пытаемся без подписей
    try:
        r = requests.get(ticker_url, timeout=10)
        r.raise_for_status()
        data = r.json()
        last = float(data["THB_USDT"]["last"])  # Bitkub формат как в PHP
        return last
    except Exception:
        pass

    # 2) Если нужен подписанный запрос
    if not api_key or not api_secret:
        raise RuntimeError("Bitkub требует подпись: укажи API KEY и SECRET или сделай endpoint публичным")

    ts = requests.get(server_time_url, timeout=10).text.strip()
    # Вырезаем путь и query из полного URL
    # Например: https://api.bitkub.com/api/market/ticker?sym=THB_USDT -> /api/market/ticker?sym=THB_USDT
    path_and_query = "/" + ticker_url.split("//", 1)[-1].split("/", 1)[-1]
    signature = sign_bitkub(ts, "GET", path_and_query, api_secret)

    headers = {
        "Accept": "application/json",
        "Content-type": "application/json",
        "X-BTK-APIKEY": api_key,
        "X-BTK-TIMESTAMP": ts,
        "X-BTK-SIGN": signature,
    }
    r = requests.get(ticker_url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    last = float(data["THB_USDT"]["last"])  # как в PHP
    return last


def fetch_rapira_usdt_rub(rapira_url: str) -> float:
    r = requests.get(rapira_url, timeout=10)
    r.raise_for_status()
    payload = r.json()
    items = payload.get("data") or []
    for it in items:
        if it.get("symbol") == "USDT/RUB":
            bid = float(it["bidPrice"])  # как в PHP берём bidPrice
            return bid
    raise RuntimeError("USDT/RUB не найден в ответе Rapira")


def compute_rates(rapira_usd_rub: float, thb_usd: float) -> FxResult:
    usd_rub_base = round(rapira_usd_rub * 1.04, 2)  # как в твоём PHP getRapiraUsdRubRate()

    res = FxResult(
        usd_rub_base=round(usd_rub_base, 3),
        usd_rub_plus_3_5=round(usd_rub_base * 1.035, 3),
        usd_rub_plus_7=round(usd_rub_base * 1.07, 3),
        thb_usd=round(thb_usd, 2),
        thb_usd_2_5=round(thb_usd * 0.975, 3),
        thb_usd_2_75=round(thb_usd * 0.9725, 3),
        thb_usd_3=round(thb_usd * 0.97, 3),
        conversion_rate_base=round(usd_rub_base / thb_usd, 3),
        conversion_rate_plus_3_5=round((usd_rub_base * 1.035) / thb_usd, 3),
        conversion_rate_plus_4=round((usd_rub_base * 1.04) / thb_usd, 3),
        conversion_rate_plus_5=round((usd_rub_base * 1.05) / thb_usd, 3),
        conversion_rate_plus_6=round((usd_rub_base * 1.06) / thb_usd, 3),
        conversion_rate_plus_7=round((usd_rub_base * 1.07) / thb_usd, 3),
        rate=round((usd_rub_base * 1.035) / thb_usd, 3),
    )
    return res

# ---------- Загрузка и расчёт ----------
colA, colB, colC = st.columns([1,1,1])
with colA:
    if st.button("🔄 Обновить сейчас", use_container_width=True):
        st.experimental_rerun()

# Тянем данные
try:
    thb_usdt_last = fetch_bitkub_thb_usdt(
        bitkub_server_time_url,
        bitkub_ticker_url,
        bitkub_api_key or None,
        bitkub_api_secret or None,
    )
    thb_usdt_last = round(thb_usdt_last - float(subtract_const), 2)
    rapira_usdt_rub = fetch_rapira_usdt_rub(rapira_url)
    fx = compute_rates(rapira_usdt_rub, thb_usdt_last)
except Exception as e:
    st.error(f"Ошибка загрузки/расчёта: {e}")
    st.stop()

# ---------- Вывод базовых значений ----------
col1, col2, col3 = st.columns(3)
col1.metric("usdt_rub_base (RUB за 1 USDT)", f"{fx.usd_rub_base:.3f}")
col2.metric("thb_usdt (THB за 1 USDT)", f"{fx.thb_usd:.3f}")
col3.metric("RUB→THB (без маржи)", f"{fx.conversion_rate_base:.3f}")

st.divider()

# ---------- Маржа и пересчёт ----------
margin = st.number_input("% маржи (на RUB часть для RUB→THB и как fee для USD→THB)", value=float(default_margin), step=0.1)

usd_thb_with_margin = fx.thb_usd * (1 - margin/100)
rub_thb_with_margin = (fx.usd_rub_base * (1 + margin/100)) / fx.thb_usd

calc_df = pd.DataFrame([
    {"Пара":"USDT→THB","Base":fx.thb_usd, "With Margin": usd_thb_with_margin},
    {"Пара":"RUB→THB","Base":fx.conversion_rate_base, "With Margin": rub_thb_with_margin},
]).set_index("Пара").round(4)

st.subheader("📊 Расчётные курсы с маржей")
st.table(calc_df)

st.caption("Логика идентична PHP: usd_rub_base = Rapira*1.04, thb_usd — Bitkub (минус константа). Маржа применяется как fee к USD→THB и как наценка к RUB→THB.")

# ---------- JSON для копирования/интеграций ----------
json_dict: Dict[str, Any] = fx.model_dump()
json_dict.update({
    "usd_thb_with_margin": round(usd_thb_with_margin, 3),
    "rub_thb_with_margin": round(rub_thb_with_margin, 3),
    "margin_percent": margin,
})

#st.subheader("🧩 JSON (для интеграций)")
#st.code(__import__("json").dumps(json_dict, ensure_ascii=False, indent=2), language="json")

# Кнопки быстрого копирования
st.download_button(
    label="⬇️ Скачать JSON",
    file_name="fx_rates.json",
    mime="application/json",
    data=__import__("json").dumps(json_dict, ensure_ascii=False, indent=2).encode("utf-8"),
)

st.caption("Готово. Весь расчёт на Python, без PHP.")
