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


def holding_row(h):
    cls = color_class(h["pl"])
    return f"""
        <tr>
          <td class="code">{h['code']}<span class="name">{h['name']}</span></td>
          <td>{fmt(h['shares'], 0)}</td>
          <td>{fmt(h['price'])}</td>
          <td class="{color_class(h['change'])}">{sign(h['pct'])}{fmt(h['pct'])}%</td>
          <td>{fmt(h['market_value'], 0)}</td>
          <td>{fmt(h['cost'])}</td>
          <td class="{cls}">{sign(h['pl'])}{fmt(h['pl'], 0)}</td>
          <td class="{cls}">{sign(h['pl_pct'])}{fmt(h['pl_pct'])}%</td>
        </tr>"""


def watch_card(w):
    cls = color_class(w["change"])
    return f"""
        <div class="watch-card {cls}">
          <div class="watch-name">{w['name']} <span>{w['code']}</span></div>
          <div class="watch-price {cls}">{fmt(w['price'])}</div>
          <div class="watch-change {cls}">{sign(w['change'])}{fmt(w['change'])} &nbsp; {sign(w['pct'])}{fmt(w['pct'])}%</div>
        </div>"""


def index_card(i):
    cls = color_class(i["change"])
    return f"""
        <div class="watch-card index {cls}">
          <div class="watch-name">{i['name']}</div>
          <div class="watch-price {cls}">{fmt(i['price'])}</div>
          <div class="watch-change {cls}">{sign(i['change'])}{fmt(i['change'])} &nbsp; {sign(i['pct'])}{fmt(i['pct'])}%</div>
        </div>"""


summary = D["summary"]
summary_cls = color_class(summary["total_pl"])

holdings_html = "".join(holding_row(h) for h in D["holdings"])
watch_html = "".join(watch_card(w) for w in D["watchlist"])
index_html = "".join(index_card(i) for i in D["indices"])

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
    margin-bottom: 26px;
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
  .code {{ font-weight: 700; }}
  .code .name {{ display: block; font-weight: 400; color: var(--sub); font-size: 11.5px; }}
  .up {{ color: var(--up); }}
  .down {{ color: var(--down); }}
  .flat {{ color: var(--flat); }}
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
  .watch-card.index {{ background: #f1ebe0; }}
  .watch-name {{ font-size: 12.5px; font-weight: 700; margin-bottom: 6px; }}
  .watch-name span {{ font-weight: 400; color: var(--sub); font-size: 11px; }}
  .watch-price {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
  .watch-change {{ font-size: 12px; }}
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
    本頁面僅供個人追蹤與學習使用,數據來自 Yahoo Finance(可能有延遲),不構成投資建議。
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

  <div class="section-title"><span class="num">02</span> 大盤指數</div>
  <div class="watch-grid">{index_html}
  </div>

  <div class="section-title"><span class="num">03</span> 自選監控清單</div>
  <div class="watch-grid">{watch_html}
  </div>

  <footer>由 GitHub Actions 每日自動更新 · Powered by yfinance</footer>
</div>
</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print("已產生 docs/index.html")
