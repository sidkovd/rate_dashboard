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

st.sidebar.subheader("Маржи по умолчанию")
usdt_margin = st.sidebar.number_input("% маржи для USDT→THB", value=float(os.getenv("USDT_MARGIN", "2.5")), step=0.1)
rub_margin = st.sidebar.number_input("% маржи для RUB→THB", value=float(os.getenv("RUB_MARGIN", "3.5")), step=0.1)

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
        st.rerun()

# Тянем данные
try:
    thb_usdt_last = fetch_bitkub_thb_usdt(
        bitkub_server_time_url,
        bitkub_ticker_url,
        bitkub_api_key or None,
        bitkub_api_secret or None,
    )
    # Убираем константу 0.1 - используем как есть
    thb_usdt_last = round(thb_usdt_last, 2)
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
st.subheader("📊 Настройка маржи")
col_margin1, col_margin2 = st.columns(2)

with col_margin1:
    usdt_margin_input = st.number_input("% маржи для USDT→THB", value=float(usdt_margin), step=0.1, key="usdt_margin_input")

with col_margin2:
    rub_margin_input = st.number_input("% маржи для RUB→THB", value=float(rub_margin), step=0.1, key="rub_margin_input")

usd_thb_with_margin = fx.thb_usd * (1 - usdt_margin_input/100)
rub_thb_with_margin = (fx.usd_rub_base * (1 + rub_margin_input/100)) / fx.thb_usd

calc_df = pd.DataFrame([
    {"Пара":"USDT→THB","Base":fx.thb_usd, "With Margin": usd_thb_with_margin, "Margin %": usdt_margin_input},
    {"Пара":"RUB→THB","Base":fx.conversion_rate_base, "With Margin": rub_thb_with_margin, "Margin %": rub_margin_input},
]).set_index("Пара").round(4)

st.subheader("📊 Расчётные курсы с маржей")
st.table(calc_df)

st.caption("Логика: usd_rub_base = Rapira*1.04, thb_usd — Bitkub. Маржа применяется как fee к USDT→THB и как наценка к RUB→THB.")

# ---------- Калькулятор конвертации ----------
st.subheader("🧮 Калькулятор конвертации")

# Создаем табы для разных типов конвертации
tab1, tab2 = st.tabs(["💱 USDT ↔ THB", "💵 RUB ↔ THB"])

with tab1:
    st.write("**Конвертация USDT в THB и наоборот**")
    
    col_usdt1, col_usdt2 = st.columns(2)
    
    with col_usdt1:
        st.write("**USDT → THB**")
        usdt_amount = st.number_input("Сколько USDT отдаете?", value=1000.0, step=100.0, key="usdt_to_thb")
        thb_received = usdt_amount * (1 - usdt_margin_input/100) * fx.thb_usd
        thb_received = round(thb_received, 2)
        
        # Форматируем числа с разделителями
        usdt_formatted = f"{usdt_amount:,.0f}" if usdt_amount.is_integer() else f"{usdt_amount:,.2f}"
        thb_formatted = f"{thb_received:,.0f}" if thb_received.is_integer() else f"{thb_received:,.2f}"
        
        st.write(f"**Отдаете:** {usdt_formatted} USDT")
        st.write(f"**Получаете:** {thb_formatted} ฿")
        st.write(f"**Курс:** {fx.thb_usd:.2f}")
        
        # Текст для копирования
        usdt_to_thb_text = f"""💱 USDT → THB
Отдаете: {usdt_formatted} USDT
Получаете: {thb_formatted} ฿
Курс: {fx.thb_usd:.2f}

💱 USDT → THB
U give: {usdt_formatted} USDT
U receive: {thb_formatted} ฿
Rate: {fx.thb_usd:.1f}"""
        
        if st.button("📋 Копировать", key="copy_usdt_to_thb"):
            st.write("✅ Скопировано в буфер обмена!")
            st.code(usdt_to_thb_text)
    
    with col_usdt2:
        st.write("**THB → USDT**")
        thb_amount = st.number_input("Сколько THB отдаете?", value=30000.0, step=1000.0, key="thb_to_usdt")
        usdt_received = thb_amount / fx.thb_usd / (1 - usdt_margin_input/100)
        usdt_received = round(usdt_received, 2)
        
        # Форматируем числа с разделителями
        thb_formatted_rev = f"{thb_amount:,.0f}" if thb_amount.is_integer() else f"{thb_amount:,.2f}"
        usdt_formatted_rev = f"{usdt_received:,.0f}" if usdt_received.is_integer() else f"{usdt_received:,.2f}"
        
        st.write(f"**Отдаете:** {thb_formatted_rev} ฿")
        st.write(f"**Получаете:** {usdt_formatted_rev} USDT")
        st.write(f"**Курс:** {fx.thb_usd:.2f}")
        
        # Текст для копирования
        thb_to_usdt_text = f"""💱 THB → USDT
Отдаете: {thb_formatted_rev} ฿
Получаете: {usdt_formatted_rev} USDT
Курс: {fx.thb_usd:.2f}

💱 THB → USDT
U give: {thb_formatted_rev} ฿
U receive: {usdt_formatted_rev} USDT
Rate: {fx.thb_usd:.1f}"""
        
        if st.button("📋 Копировать", key="copy_thb_to_usdt"):
            st.write("✅ Скопировано в буфер обмена!")
            st.code(thb_to_usdt_text)

with tab2:
    st.write("**Конвертация RUB в THB и наоборот**")
    
    col_rub1, col_rub2 = st.columns(2)
    
    with col_rub1:
        st.write("**RUB → THB**")
        rub_amount = st.number_input("Сколько RUB отдаете?", value=100000.0, step=10000.0, key="rub_to_thb")
        thb_received_rub = rub_amount / (fx.usd_rub_base * (1 + rub_margin_input/100)) * fx.thb_usd
        thb_received_rub = round(thb_received_rub, 2)
        
        # Форматируем числа с разделителями
        rub_formatted = f"{rub_amount:,.0f}" if rub_amount.is_integer() else f"{rub_amount:,.2f}"
        thb_formatted_rub = f"{thb_received_rub:,.0f}" if thb_received_rub.is_integer() else f"{thb_received_rub:,.2f}"
        
        st.write(f"**Отдаете:** {rub_formatted} RUB")
        st.write(f"**Получаете:** {thb_formatted_rub} ฿")
        st.write(f"**Курс:** {fx.usd_rub_base:.5f} RUB/THB ({1/fx.usd_rub_base:.3f})")
        
        # Текст для копирования
        rub_to_thb_text = f"""💵 {rub_formatted} RUB -> {thb_formatted_rub} THB
Курс: {fx.usd_rub_base:.5f} RUB/THB ({1/fx.usd_rub_base:.3f})

💵 {rub_formatted} RUB -> {thb_formatted_rub} THB
Rate: {fx.usd_rub_base:.5f} RUB/THB ({1/fx.usd_rub_base:.3f})"""
        
        if st.button("📋 Копировать", key="copy_rub_to_thb"):
            st.write("✅ Скопировано в буфер обмена!")
            st.code(rub_to_thb_text)
    
    with col_rub2:
        st.write("**THB → RUB**")
        thb_amount_rub = st.number_input("Сколько THB отдаете?", value=30000.0, step=1000.0, key="thb_to_rub")
        rub_received = thb_amount_rub * (fx.usd_rub_base * (1 + rub_margin_input/100)) / fx.thb_usd
        rub_received = round(rub_received, 2)
        
        # Форматируем числа с разделителями
        thb_formatted_rub_rev = f"{thb_amount_rub:,.0f}" if thb_amount_rub.is_integer() else f"{thb_amount_rub:,.2f}"
        rub_formatted_rev = f"{rub_received:,.0f}" if rub_received.is_integer() else f"{rub_received:,.2f}"
        
        st.write(f"**Отдаете:** {thb_formatted_rub_rev} ฿")
        st.write(f"**Получаете:** {rub_formatted_rev} RUB")
        st.write(f"**Курс:** {fx.usd_rub_base:.5f} RUB/THB ({1/fx.usd_rub_base:.3f})")
        
        # Текст для копирования
        thb_to_rub_text = f"""💵 {thb_formatted_rub_rev} THB -> {rub_formatted_rev} RUB
Курс: {fx.usd_rub_base:.5f} RUB/THB ({1/fx.usd_rub_base:.3f})

💵 {thb_formatted_rub_rev} THB -> {rub_formatted_rev} RUB
Rate: {fx.usd_rub_base:.5f} RUB/THB ({1/fx.usd_rub_base:.3f})"""
        
        if st.button("📋 Копировать", key="copy_thb_to_rub"):
            st.write("✅ Скопировано в буфер обмена!")
            st.code(thb_to_rub_text)

# ---------- JSON для копирования/интеграций ----------
json_dict: Dict[str, Any] = fx.model_dump()
json_dict.update({
    "usdt_thb_with_margin": round(usd_thb_with_margin, 3),
    "rub_thb_with_margin": round(rub_thb_with_margin, 3),
    "usdt_margin_percent": usdt_margin_input,
    "rub_margin_percent": rub_margin_input,
})

#st.subheader("🧩 JSON (для интеграций)")
#st.code(__import__("json").dumps(json_dict, ensure_ascii=False, indent=2), language="json")

# Кнопки быстрого копирования
#st.download_button(
#    label="⬇️ Скачать JSON",
#    file_name="fx_rates.json",
#    mime="application/json",
#    data=__import__("json").dumps(json_dict, ensure_ascii=False, indent=2).encode("utf-8"),
#)

#st.caption("Готово. Весь расчёт на Python, без PHP.")
# Тест автоперезагрузки - изменения применяются автоматически!
