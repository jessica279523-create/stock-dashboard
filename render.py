#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""將 data.json 轉換成 docs/index.html(靜態網頁,給 GitHub Pages 部署用)。"""

import json

with open("data.json", "r", encoding="utf-8") as f:
    D = json.load(f)


def fmt(n, decimals=2):
    if n is None:
        return "--"
    return f"{n:,.{decimals}f}"


def color_class(n):
    if n is None:
        return "flat"
    if n > 0:
        return "up"
    if n < 0:
        return "down"
    return "flat"


def sign(n):
    if n is None:
        return ""
    return "+" if n >= 0 else ""


HOT_THRESHOLD = D.get("hot_move_threshold", 5.0)


def is_hot(pct):
    return pct is not None and abs(pct) >= HOT_THRESHOLD


def holding_row(h):
    cls = color_class(h["pl"])
    hot = " hot-row" if is_hot(h.get("pct")) else ""
    hot_icon = " 🔥" if is_hot(h.get("pct")) else ""
    return f"""
        <tr class="{hot}">
          <td class="code">{h['code']}<span class="name">{h['name']}</span></td>
          <td>{fmt(h['shares'], 0)}</td>
          <td>{fmt(h['price'])}</td>
          <td class="{color_class(h['change'])}">{sign(h['pct'])}{fmt(h['pct'])}%{hot_icon}</td>
          <td>{fmt(h['market_value'], 0)}</td>
          <td>{fmt(h['cost'])}</td>
          <td class="{cls}">{sign(h['pl'])}{fmt(h['pl'], 0)}</td>
          <td class="{cls}">{sign(h['pl_pct'])}{fmt(h['pl_pct'])}%</td>
        </tr>"""


def watch_card(w):
    cls = color_class(w.get("change"))
    hot = " hot" if is_hot(w.get("pct")) else ""
    hot_icon = "🔥 " if is_hot(w.get("pct")) else ""
    pe_txt = fmt(w.get("pe"), 1) if w.get("pe") is not None else "--"
    yld_txt = f"{fmt(w.get('dividend_yield'), 2)}%" if w.get("dividend_yield") is not None else "--"
    return f"""
        <div class="watch-card {cls}{hot}">
          <div class="watch-name">{hot_icon}{w['name']} <span>{w['code']}</span></div>
          <div class="watch-price {cls}">{fmt(w.get('price'))}</div>
          <div class="watch-change {cls}">{sign(w.get('change'))}{fmt(w.get('change'))} &nbsp; {sign(w.get('pct'))}{fmt(w.get('pct'))}%</div>
          <div class="watch-fund">PE {pe_txt} · 殖利率 {yld_txt}</div>
        </div>"""


def index_card(i):
    cls = color_class(i.get("change"))
    return f"""
        <div class="watch-card index {cls}">
          <div class="watch-name">{i['name']}</div>
          <div class="watch-price {cls}">{fmt(i.get('price'))}</div>
          <div class="watch-change {cls}">{sign(i.get('change'))}{fmt(i.get('change'))} &nbsp; {sign(i.get('pct'))}{fmt(i.get('pct'))}%</div>
        </div>"""


def highlight_card(label, item, cls):
    if item is None:
        return ""
    return f"""
        <div class="hl-card {cls}">
          <div class="hl-label">{label}</div>
          <div class="hl-name">{item['name']} <span>{item['code']}</span></div>
          <div class="hl-pct {cls}">{sign(item['pct'])}{fmt(item['pct'])}%</div>
        </div>"""


def sparkline_svg(history, width=680, height=90):
    """簡單畫一個 SVG 折線圖,顯示總市值歷史走勢,不需要任何外部套件。"""
    if not history or len(history) < 2:
        return '<div class="spark-empty">累積更多天數的資料後,這裡會顯示損益走勢圖</div>'

    values = [h["total_value"] for h in history]
    dates = [h["date"] for h in history]
    vmin, vmax = min(values), max(values)
    vrange = (vmax - vmin) or 1

    pad = 10
    n = len(values)
    step = (width - 2 * pad) / (n - 1) if n > 1 else 0

    points = []
    for idx, v in enumerate(values):
        x = pad + idx * step
        y = height - pad - ((v - vmin) / vrange) * (height - 2 * pad)
        points.append(f"{x:.1f},{y:.1f}")
    points_str = " ".join(points)

    last_up = values[-1] >= values[0]
    line_color = "#1f9254" if last_up else "#d0392b"

    first_date = dates[0]
    last_date = dates[-1]

    return f"""
    <svg viewBox="0 0 {width} {height}" class="spark-svg" preserveAspectRatio="none">
      <polyline fill="none" stroke="{line_color}" stroke-width="2.5" points="{points_str}" />
    </svg>
    <div class="spark-labels"><span>{first_date}</span><span>{last_date}</span></div>
    """


summary = D["summary"]
summary_cls = color_class(summary["total_pl"])
highlight = D.get("highlight", {})

holdings_html = "".join(holding_row(h) for h in D["holdings"])

# 1. 依 sector 分組監控清單
watchlist = D["watchlist"]
sectors = []
seen_sectors = set()
for w in watchlist:
    s = w.get("sector", "其他")
    if s not in seen_sectors:
        seen_sectors.add(s)
        sectors.append(s)

sector_sections_html = ""
for sector in sectors:
    items = [w for w in watchlist if w.get("sector", "其他") == sector]
    cards_html = "".join(watch_card(w) for w in items)
    sector_sections_html += f"""
    <div class="sector-block">
      <div class="sector-title">{sector}</div>
      <div class="watch-grid">{cards_html}
      </div>
    </div>"""

index_html = "".join(index_card(i) for i in D["indices"])

hl_html = (
    highlight_card("今日漲最多", highlight.get("top_gainer"), "up")
    + highlight_card("今日跌最多", highlight.get("top_loser"), "down")
)

spark_html = sparkline_svg(D.get("history", []))

HTML = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>今日台股研究簡報</title>
<style>
  :root {{
    --bg: #f5f0e8;
    --card: #ffffff;
    --ink: #2b2620;
    --sub: #8a8073;
    --accent: #c1622f;
    --up: #1f9254;
    --down: #d0392b;
    --flat: #8a8073;
    --border: #e8e0d3;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: -apple-system, "PingFang TC", "Noto Sans TC", sans-serif;
    padding: 24px 16px 60px;
  }}
  .wrap {{ max-width: 900px; margin: 0 auto; }}
  .eyebrow {{
    color: var(--accent);
    font-size: 12px;
    letter-spacing: 2px;
    font-weight: 700;
    text-transform: uppercase;
  }}
  h1 {{ font-size: 30px; margin: 6px 0 4px; }}
  .subtitle {{ color: var(--sub); font-style: italic; margin-bottom: 14px; }}
  .meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }}
  .pill {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 5px 12px;
    font-size: 12px;
    color: var(--sub);
  }}
  .notice {{
    background: #fbf3ea;
    border-left: 3px solid var(--accent);
    padding: 12px 14px;
    font-size: 12.5px;
    color: #6b5f4f;
    border-radius: 6px;
    margin-bottom: 20px;
  }}
  .section-title {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 17px;
    font-weight: 700;
    margin: 30px 0 12px;
  }}
  .section-title .num {{
    background: var(--ink);
    color: #fff;
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 4px;
  }}
  .hl-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 24px; }}
  .hl-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-left: 4px solid var(--flat);
    border-radius: 10px;
    padding: 12px 14px;
  }}
  .hl-card.up {{ border-left-color: var(--up); }}
  .hl-card.down {{ border-left-color: var(--down); }}
  .hl-label {{ font-size: 11px; color: var(--sub); margin-bottom: 4px; }}
  .hl-name {{ font-size: 14px; font-weight: 700; margin-bottom: 4px; }}
  .hl-name span {{ font-weight: 400; color: var(--sub); font-size: 11px; }}
  .hl-pct {{ font-size: 18px; font-weight: 700; }}
  .summary-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px;
  }}
  @media (min-width: 640px) {{
    .summary-grid {{ grid-template-columns: repeat(5, 1fr); }}
    .hl-row {{ grid-template-columns: 1fr 1fr; }}
  }}
  .summary-item .label {{ font-size: 11.5px; color: var(--sub); margin-bottom: 4px; }}
  .summary-item .value {{ font-size: 22px; font-weight: 700; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--card);
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--border);
    font-size: 13.5px;
  }}
  thead {{ background: #f1ebe0; }}
  th, td {{ padding: 10px 8px; text-align: right; white-space: nowrap; }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{ font-size: 11.5px; color: var(--sub); font-weight: 600; }}
  tr + tr {{ border-top: 1px solid var(--border); }}
  tr.hot-row {{ background: #fff4ec; }}
  .code {{ font-weight: 700; }}
  .code .name {{ display: block; font-weight: 400; color: var(--sub); font-size: 11.5px; }}
  .up {{ color: var(--up); }}
  .down {{ color: var(--down); }}
  .flat {{ color: var(--flat); }}
  .sector-block {{ margin-bottom: 22px; }}
  .sector-title {{
    font-size: 13px;
    font-weight: 700;
    color: var(--accent);
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border);
  }}
  .watch-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }}
  @media (min-width: 640px) {{
    .watch-grid {{ grid-template-columns: repeat(4, 1fr); }}
  }}
  .watch-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-left: 4px solid var(--flat);
    border-radius: 10px;
    padding: 12px 14px;
  }}
  .watch-card.up {{ border-left-color: var(--up); }}
  .watch-card.down {{ border-left-color: var(--down); }}
  .watch-card.hot {{ background: #fff4ec; border-left-width: 6px; }}
  .watch-card.index {{ background: #f1ebe0; }}
  .watch-name {{ font-size: 12.5px; font-weight: 700; margin-bottom: 6px; }}
  .watch-name span {{ font-weight: 400; color: var(--sub); font-size: 11px; }}
  .watch-price {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
  .watch-change {{ font-size: 12px; }}
  .watch-fund {{ font-size: 10.5px; color: var(--sub); margin-top: 4px; }}
  .spark-box {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px;
  }}
  .spark-svg {{ width: 100%; height: 90px; display: block; }}
  .spark-labels {{ display: flex; justify-content: space-between; font-size: 11px; color: var(--sub); margin-top: 4px; }}
  .spark-empty {{ font-size: 12.5px; color: var(--sub); text-align: center; padding: 20px 0; }}
  footer {{ text-align: center; color: var(--sub); font-size: 11.5px; margin-top: 40px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">Daily TW Equity Briefing · 台股每日簡報</div>
  <h1>今日台股研究簡報</h1>
  <div class="subtitle">A daily reading of your Taiwan market watchlist</div>
  <div class="meta">
    <span class="pill">數據日期 {D['data_date']}</span>
    <span class="pill">產生時間 {D['generated_at']} (台北時間)</span>
    <span class="pill">監控標的 {len(D['watchlist'])}</span>
  </div>
  <div class="notice">
    本頁面僅供個人追蹤與學習使用,數據來自台灣證交所/Yahoo Finance(可能有延遲),不構成投資建議。
  </div>

  <div class="section-title"><span class="num">★</span> 今日重點摘要</div>
  <div class="hl-row">{hl_html}
  </div>

  <div class="section-title"><span class="num">01</span> 我的持股</div>
  <div class="summary-grid">
    <div class="summary-item"><div class="label">總市值</div><div class="value">${fmt(summary['total_value'], 0)}</div></div>
    <div class="summary-item"><div class="label">未實現損益</div><div class="value {summary_cls}">{sign(summary['total_pl'])}{fmt(summary['total_pl'], 0)}</div></div>
    <div class="summary-item"><div class="label">損益幅度</div><div class="value {summary_cls}">{sign(summary['total_pl_pct'])}{fmt(summary['total_pl_pct'])}%</div></div>
    <div class="summary-item"><div class="label">持倉數</div><div class="value">{summary['position_count']}</div></div>
    <div class="summary-item"><div class="label">監控近況上漲占比</div><div class="value">{fmt(summary['up_ratio'], 1)}%</div></div>
  </div>

  <table style="margin-top:12px;">
    <thead>
      <tr>
        <th>代碼</th><th>股數</th><th>現價</th><th>當日</th><th>市值</th><th>成本價</th><th>損益</th><th>損益%</th>
      </tr>
    </thead>
    <tbody>{holdings_html}
    </tbody>
  </table>

  <div class="section-title"><span class="num">02</span> 損益走勢圖</div>
  <div class="spark-box">{spark_html}</div>

  <div class="section-title"><span class="num">03</span> 大盤指數</div>
  <div class="watch-grid">{index_html}
  </div>

  <div class="section-title"><span class="num">04</span> 自選監控清單(依產業分類,漲跌幅排序)</div>
  {sector_sections_html}

  <footer>由 GitHub Actions 每日自動更新 · Powered by TWSE + yfinance · 🔥 標示當日漲跌幅 ≥ {HOT_THRESHOLD}%</footer>
</div>
</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print("已產生 docs/index.html")
