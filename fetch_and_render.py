#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日台股自選 + 持股報告產生器(進階版)
新增功能:
  1. 監控股分類(依產業別分組)
  2. 今日重點摘要(漲最多/跌最多)
  3. 大漲大跌警示(|漲跌幅| >= 5%)
  4. 本益比 / 殖利率(yfinance .info,可能不是每檔都有)
  5. 損益走勢圖(讀寫 history.json,累積每日總市值)
  6. 監控清單依漲跌幅排序

用 yfinance + TWSE 官方 API 抓報價,輸出成 HTML 靜態頁面。
搭配 GitHub Actions 排程執行,自動部署到 GitHub Pages。
"""

import json
import os
from datetime import datetime, timezone, timedelta

import requests
import yfinance as yf

# ---------------------------------------------------------------------------
# 1. 設定區:妳的持股 與 監控清單(含產業分類)
# ---------------------------------------------------------------------------

# 實際持股(會計算損益)
HOLDINGS = [
    {"code": "3231", "name": "緯創",   "shares": 400, "cost": 146.5},
    {"code": "2330", "name": "台積電", "shares": 50,  "cost": 2415.0},
    {"code": "6770", "name": "力積電", "shares": 500, "cost": 61.6},
]

# 純監控清單(只顯示現價與漲跌,不計損益) — 每檔加上 sector 產業分類
WATCHLIST = [
    # 半導體
    {"code": "2344", "name": "華邦電", "sector": "半導體"},
    {"code": "2303", "name": "聯電",   "sector": "半導體"},
    # 航運
    {"code": "2603", "name": "長榮",   "sector": "航運"},
    {"code": "2609", "name": "陽明",   "sector": "航運"},
    {"code": "2615", "name": "萬海",   "sector": "航運"},
    {"code": "2618", "name": "長榮航", "sector": "航運"},
    {"code": "2610", "name": "華航",   "sector": "航運"},
    # 金融
    {"code": "2892", "name": "第一金", "sector": "金融"},
    {"code": "2886", "name": "兆豐金", "sector": "金融"},
    {"code": "2882", "name": "國泰金", "sector": "金融"},
    {"code": "2801", "name": "彰銀",   "sector": "金融"},
    {"code": "2891", "name": "中信金", "sector": "金融"},
    # 面板
    {"code": "6116", "name": "彩晶",   "sector": "面板"},
    {"code": "2409", "name": "友達",   "sector": "面板"},
    {"code": "3481", "name": "群創",   "sector": "面板"},
    # 電子代工/零組件
    {"code": "2324", "name": "仁寶",   "sector": "電子代工/零組件"},
    {"code": "2356", "name": "英業達", "sector": "電子代工/零組件"},
    {"code": "2301", "name": "光寶科", "sector": "電子代工/零組件"},
    {"code": "2327", "name": "國巨",   "sector": "電子代工/零組件"},
    {"code": "2328", "name": "廣宇",   "sector": "電子代工/零組件"},
    {"code": "2317", "name": "鴻海",   "sector": "電子代工/零組件"},
    # 傳產
    {"code": "1101", "name": "台泥",   "sector": "傳產"},
    {"code": "2103", "name": "台橡",   "sector": "傳產"},
    {"code": "1718", "name": "中纖",   "sector": "傳產"},
    # 民生消費
    {"code": "1216", "name": "統一",   "sector": "民生消費"},
    # ETF
    {"code": "00757", "name": "統一FANG+", "sector": "ETF"},
]

# 大盤指數:優先用 TWSE 官方 MIS 特殊代碼,失敗才退回 yfinance
INDICES = [
    {"code": "^TWII",  "name": "加權指數",     "mis_code": "tse_t00.tw"},
    {"code": "^TWOII", "name": "櫃檯指數(OTC)", "mis_code": "otc_o00.tw"},
]

# 大漲大跌警示門檻(百分比,絕對值)
HOT_MOVE_THRESHOLD = 5.0

TAIPEI_TZ = timezone(timedelta(hours=8))
HISTORY_FILE = "history.json"
HISTORY_MAX_DAYS = 90  # 最多保留幾天歷史紀錄


def to_yf_ticker(code: str) -> str:
    return f"{code}.TW"


# ---------------------------------------------------------------------------
# 2. 報價抓取函式
# ---------------------------------------------------------------------------

def fetch_quote(ticker: str):
    """yfinance 備援報價。回傳 dict,失敗回傳 None。"""
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


def fetch_mis_quote(mis_code: str):
    """用 TWSE 官方 MIS API 的完整代碼(例如 tse_2330.tw 或 tse_t00.tw)直接抓一筆。"""
    try:
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={mis_code}&json=1&delay=0"
        resp = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        payload = resp.json()
        arr = payload.get("msgArray") or []
        if not arr:
            return None
        item = arr[0]
        z = item.get("z")
        y = item.get("y")
        if z in (None, "-", ""):
            b = item.get("b", "")
            z = b.split("_")[0] if b else None
        if z in (None, "-", "") or y in (None, "-", ""):
            return None
        price = float(z)
        prev_close = float(y)
        change = price - prev_close
        pct = (change / prev_close * 100) if prev_close else 0.0
        return {"price": price, "change": change, "pct": pct}
    except Exception as e:
        print(f"[警告] MIS API 抓取 {mis_code} 失敗: {e}")
        return None


def fetch_quote_twse(code: str):
    """個股報價:先試上市(tse_),再試上櫃(otc_)。"""
    for market in ("tse", "otc"):
        q = fetch_mis_quote(f"{market}_{code}.tw")
        if q is not None:
            return q
    return None


def fetch_stock_quote(code: str):
    """個股報價:優先 TWSE 官方 API,失敗才退回 yfinance。"""
    q = fetch_quote_twse(code)
    if q is not None:
        return q
    print(f"[提示] {code} 改用 yfinance 備援數據源")
    return fetch_quote(to_yf_ticker(code))


def fetch_fundamentals(code: str):
    """
    抓本益比(PE)與殖利率(Dividend Yield)。
    yfinance 的 .info 有時會抓不到或很慢,失敗就回傳 None,畫面上會顯示 "--"。
    """
    try:
        t = yf.Ticker(to_yf_ticker(code))
        info = t.info or {}
        pe = info.get("trailingPE")
        yield_raw = info.get("dividendYield")
        div_yield = None
        if yield_raw is not None:
            # yfinance 有時回傳 0.03 代表 3%,有時已經是 3 代表 3%,做個保護判斷
            div_yield = yield_raw * 100 if yield_raw < 1 else yield_raw
        return {
            "pe": round(pe, 1) if isinstance(pe, (int, float)) else None,
            "dividend_yield": round(div_yield, 2) if isinstance(div_yield, (int, float)) else None,
        }
    except Exception as e:
        print(f"[警告] 抓取 {code} 基本面資料失敗: {e}")
        return {"pe": None, "dividend_yield": None}


# ---------------------------------------------------------------------------
# 3. 歷史紀錄(損益走勢圖用)
# ---------------------------------------------------------------------------

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def append_history(history, date_str, total_value, total_pl_pct):
    # 同一天執行多次時,更新當天資料而不是重複新增
    history = [h for h in history if h.get("date") != date_str]
    history.append({"date": date_str, "total_value": total_value, "total_pl_pct": total_pl_pct})
    history.sort(key=lambda h: h["date"])
    if len(history) > HISTORY_MAX_DAYS:
        history = history[-HISTORY_MAX_DAYS:]
    return history


# ---------------------------------------------------------------------------
# 4. 主要資料組裝
# ---------------------------------------------------------------------------

def build_data():
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
        fund = fetch_fundamentals(w["code"])
        if q is None:
            watch_out.append({**w, "price": None, "change": None, "pct": None, **fund})
            continue
        valid_count += 1
        if q["change"] > 0:
            up_count += 1
        watch_out.append({**w, **q, **fund})

    # 6. 依漲跌幅排序(有資料的排前面,None 排最後)
    watch_out.sort(key=lambda w: (w["pct"] is None, -(w["pct"] or 0)))

    # 2. 今日重點摘要:漲最多 / 跌最多(涵蓋持股 + 監控清單)
    all_for_highlight = [
        {"code": h["code"], "name": h["name"], "pct": h.get("pct")} for h in holdings_out if h.get("pct") is not None
    ] + [
        {"code": w["code"], "name": w["name"], "pct": w.get("pct")} for w in watch_out if w.get("pct") is not None
    ]
    top_gainer = max(all_for_highlight, key=lambda x: x["pct"]) if all_for_highlight else None
    top_loser = min(all_for_highlight, key=lambda x: x["pct"]) if all_for_highlight else None

    index_out = []
    for idx in INDICES:
        q = fetch_mis_quote(idx["mis_code"])
        if q is None:
            q = fetch_quote(idx["code"])  # yfinance 備援
        if q is None:
            index_out.append({**idx, "price": None, "change": None, "pct": None})
            continue
        index_out.append({**idx, **q})

    total_pl = total_value - total_cost
    total_pl_pct = (total_pl / total_cost * 100) if total_cost else 0.0
    up_ratio = (up_count / valid_count * 100) if valid_count else 0.0

    now = datetime.now(TAIPEI_TZ)
    date_str = now.strftime("%Y-%m-%d")

    # 5. 損益走勢圖:讀取舊歷史 + 加入今天資料
    history = load_history()
    history = append_history(history, date_str, total_value, total_pl_pct)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "data_date": date_str,
        "holdings": holdings_out,
        "watchlist": watch_out,
        "indices": index_out,
        "history": history,
        "highlight": {
            "top_gainer": top_gainer,
            "top_loser": top_loser,
        },
        "hot_move_threshold": HOT_MOVE_THRESHOLD,
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
    print("已產生 data.json 與 history.json")
