#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日台股自選 + 持股報告產生器
用 yfinance 抓即時(延遲)報價,計算持股損益,輸出成 HTML 靜態頁面。
搭配 GitHub Actions 排程執行,自動部署到 GitHub Pages。
"""

import json
from datetime import datetime, timezone, timedelta

import requests
import yfinance as yf

# ---------------------------------------------------------------------------
# 1. 設定區:妳的持股 與 監控清單
# ---------------------------------------------------------------------------

# 實際持股(會計算損益)
HOLDINGS = [
    {"code": "3231", "name": "緯創",   "shares": 400, "cost": 146.5},
    {"code": "2330", "name": "台積電", "shares": 50,  "cost": 2415.0},
]

# 純監控清單(只顯示現價與漲跌,不計損益)
WATCHLIST = [
    {"code": "2603",  "name": "長榮"},
    {"code": "2609",  "name": "陽明"},
    {"code": "2615",  "name": "萬海"},
    {"code": "1101",  "name": "台泥"},
    {"code": "2892",  "name": "第一金"},
    {"code": "2618",  "name": "長榮航"},
    {"code": "2610",  "name": "華航"},
    {"code": "2103",  "name": "台橡"},
    {"code": "6116",  "name": "彩晶"},
    {"code": "2324",  "name": "仁寶"},
    {"code": "2356",  "name": "英業達"},
    {"code": "2409",  "name": "友達"},
    {"code": "6770",  "name": "力積電"},
    {"code": "2301",  "name": "光寶科"},
    {"code": "1718",  "name": "中纖"},
    {"code": "2327",  "name": "國巨"},
    {"code": "2344",  "name": "華邦電"},
    {"code": "2886",  "name": "兆豐金"},
    {"code": "2882",  "name": "國泰金"},
    {"code": "2801",  "name": "彰銀"},
    {"code": "2303",  "name": "聯電"},
    {"code": "2328",  "name": "廣宇"},
    {"code": "2317",  "name": "鴻海"},
    {"code": "3481",  "name": "群創"},
    {"code": "00757", "name": "統一FANG+"},
    {"code": "1216",  "name": "統一"},
    {"code": "2891",  "name": "中信金"},
]

# 大盤指數(Yahoo Finance 代碼)
INDICES = [
    {"code": "^TWII",  "name": "加權指數"},
    {"code": "^TWOII", "name": "櫃檯指數(OTC)"},
]

TAIPEI_TZ = timezone(timedelta(hours=8))


def to_yf_ticker(code: str) -> str:
    """將台股代碼轉成 yfinance 的股票代碼(預設加 .TW,上櫃股票可能需要 .TWO)。"""
    return f"{code}.TW"


def fetch_quote(ticker: str):
    """抓取單一標的的現價、漲跌、漲跌幅(yfinance,備援用)。回傳 dict,失敗回傳 None。"""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty or len(hist) < 1:
            return None
        last_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else last_close
        change = last_close - prev_close
        pct = (change / prev_close * 100) if prev_close else 0.0
        return {"price": last_close, "change": change, "pct": pct}
    except Exception as e:
        print(f"[警告] yfinance 抓取 {ticker} 失敗: {e}")
        return None


def fetch_quote_twse(code: str):
    """
    優先數據源:台灣證券交易所官方即時報價 API(mis.twse.com.tw)。
    免費、不需金鑰,是交易所官網本身在用的資料源,比 yfinance 穩定。
    會先試上市(tse_),再試上櫃(otc_)。失敗回傳 None,讓外層改用 yfinance 備援。
    """
    for market in ("tse", "otc"):
        try:
            url = (
                "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
                f"?ex_ch={market}_{code}.tw&json=1&delay=0"
            )
            resp = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
            payload = resp.json()
            arr = payload.get("msgArray") or []
            if not arr:
                continue
            item = arr[0]

            z = item.get("z")  # 成交價(當盤沒成交時可能是 "-")
            y = item.get("y")  # 昨收

            if z in (None, "-", ""):
                # 還沒開盤成交時,退而求其次用最佳買價
                b = item.get("b", "")
                z = b.split("_")[0] if b else None

            if z in (None, "-", "") or y in (None, "-", ""):
                continue

            price = float(z)
            prev_close = float(y)
            change = price - prev_close
            pct = (change / prev_close * 100) if prev_close else 0.0
            return {"price": price, "change": change, "pct": pct}
        except Exception as e:
            print(f"[警告] TWSE 官方 API 抓取 {market}_{code} 失敗: {e}")
            continue
    return None


def fetch_stock_quote(code: str):
    """個股報價:優先用 TWSE 官方 API,失敗才退回 yfinance。"""
    q = fetch_quote_twse(code)
    if q is not None:
        return q
    print(f"[提示] {code} 改用 yfinance 備援數據源")
    return fetch_quote(to_yf_ticker(code))


def build_data():
    """抓取所有持股、監控清單、指數的數據,回傳整理好的 dict。"""
    holdings_out = []
    total_value = 0.0
    total_cost = 0.0

    for h in HOLDINGS:
        q = fetch_stock_quote(h["code"])
        if q is None:
            holdings_out.append({**h, "price": None, "change": None, "pct": None,
                                  "market_value": None, "pl": None, "pl_pct": None})
            continue
        market_value = q["price"] * h["shares"]
        cost_value = h["cost"] * h["shares"]
        pl = market_value - cost_value
        pl_pct = (pl / cost_value * 100) if cost_value else 0.0
        total_value += market_value
        total_cost += cost_value
        holdings_out.append({
            **h,
            "price": q["price"], "change": q["change"], "pct": q["pct"],
            "market_value": market_value, "pl": pl, "pl_pct": pl_pct,
        })

    watch_out = []
    up_count = 0
    valid_count = 0
    for w in WATCHLIST:
        q = fetch_stock_quote(w["code"])
        if q is None:
            watch_out.append({**w, "price": None, "change": None, "pct": None})
            continue
        valid_count += 1
        if q["change"] > 0:
            up_count += 1
        watch_out.append({**w, **q})

    index_out = []
    for idx in INDICES:
        q = fetch_quote(idx["code"])
        if q is None:
            index_out.append({**idx, "price": None, "change": None, "pct": None})
            continue
        index_out.append({**idx, **q})

    total_pl = total_value - total_cost
    total_pl_pct = (total_pl / total_cost * 100) if total_cost else 0.0
    up_ratio = (up_count / valid_count * 100) if valid_count else 0.0

    now = datetime.now(TAIPEI_TZ)
    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "data_date": now.strftime("%Y-%m-%d"),
        "holdings": holdings_out,
        "watchlist": watch_out,
        "indices": index_out,
        "summary": {
            "total_value": total_value,
            "total_cost": total_cost,
            "total_pl": total_pl,
            "total_pl_pct": total_pl_pct,
            "position_count": len(holdings_out),
            "up_ratio": up_ratio,
        },
    }


if __name__ == "__main__":
    data = build_data()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("已產生 data.json")
