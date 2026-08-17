#!/usr/bin/env python3
"""采集洛谷存档数量、保存历史记录并生成静态报告。"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "history.csv"
DOCS = ROOT / "docs"
CHARTS = DOCS / "charts"
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.luogu.me").rstrip("/")


def china_date() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()


def extract_count(payload: object) -> int:
    """兼容 {count} 与 {data: {count}} 等常见 API 响应结构。"""
    if isinstance(payload, dict):
        value = payload.get("count")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return int(value)
        data = payload.get("data")
        if isinstance(data, dict):
            value = data.get("count")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return int(value)
    raise ValueError(f"API 响应中未找到数字类型的 count：{payload!r}")


def get_count(path: str) -> int:
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        headers={"Accept": "application/json", "User-Agent": "lgs-history/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return extract_count(json.load(response))


def read_history() -> list[dict[str, int | str]]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open(newline="", encoding="utf-8") as file:
        return [
            {"date": row["date"], "articles": int(row["articles"]), "pastes": int(row["pastes"])}
            for row in csv.DictReader(file)
        ]


def write_history(rows: list[dict[str, int | str]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["date", "articles", "pastes"])
        writer.writeheader()
        writer.writerows(rows)


def svg_document(width: int, height: int, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">\n<style>text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#334155}}.muted{{fill:#64748b;font-size:12px}}.value{{fill:#0f172a;font-size:28px;font-weight:700}}.title{{fill:#0f172a;font-size:16px;font-weight:700}}</style>\n<rect width="100%" height="100%" fill="#ffffff"/>\n{body}\n</svg>'''


def empty_chart(title: str) -> str:
    return svg_document(960, 400, f'<text x="48" y="52" class="title">{title}</text><text x="480" y="210" text-anchor="middle" class="muted">暂无历史数据；下次定时运行将写入首条记录。</text>')


def line_chart(title: str, rows: list[dict[str, int | str]], fields: list[tuple[str, str]], filename: str) -> None:
    if not rows:
        (CHARTS / filename).write_text(empty_chart(title), encoding="utf-8")
        return
    width, height, left, right, top, bottom = 960, 400, 64, 32, 72, 54
    values = [int(row[field]) for row in rows for field, _ in fields]
    low, high = min(values), max(values)
    if low == high:
        low = max(0, low - 1)
        high += 1
    span_x = max(1, len(rows) - 1)
    graph_w, graph_h = width - left - right, height - top - bottom
    def point(index: int, value: int) -> tuple[float, float]:
        return left + graph_w * index / span_x, top + graph_h * (high - value) / (high - low)
    bits = [f'<text x="{left}" y="36" class="title">{title}</text>']
    for tick in range(5):
        value = low + (high - low) * tick / 4
        y = top + graph_h * (4 - tick) / 4
        bits.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e2e8f0"/>')
        bits.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" class="muted">{value:,.0f}</text>')
    label_indices = sorted(set([0, len(rows) - 1, len(rows) // 2]))
    for index in label_indices:
        x, _ = point(index, int(rows[index][fields[0][0]]))
        bits.append(f'<text x="{x:.1f}" y="{height-20}" text-anchor="middle" class="muted">{rows[index]["date"]}</text>')
    colors = ["#2563eb", "#f97316", "#16a34a"]
    for series_index, (field, label) in enumerate(fields):
        color = colors[series_index]
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, int(row[field])) for i, row in enumerate(rows)))
        bits.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" points="{points}"/>')
        lx = left + series_index * 150
        bits.append(f'<rect x="{lx}" y="48" width="10" height="10" fill="{color}" rx="2"/><text x="{lx+16}" y="58" class="muted">{label}</text>')
    (CHARTS / filename).write_text(svg_document(width, height, "".join(bits)), encoding="utf-8")


def delta_rows(rows: list[dict[str, int | str]]) -> list[dict[str, int | str]]:
    result = []
    for previous, current in zip(rows, rows[1:]):
        result.append({
            "date": current["date"],
            "articles": max(0, int(current["articles"]) - int(previous["articles"])),
            "pastes": max(0, int(current["pastes"]) - int(previous["pastes"])),
        })
    return result


def monthly_rows(rows: list[dict[str, int | str]]) -> list[dict[str, int | str]]:
    monthly: dict[str, dict[str, int | str]] = {}
    for row in delta_rows(rows):
        month = str(row["date"])[:7]
        bucket = monthly.setdefault(month, {"date": month, "articles": 0, "pastes": 0})
        bucket["articles"] = int(bucket["articles"]) + int(row["articles"])
        bucket["pastes"] = int(bucket["pastes"]) + int(row["pastes"])
    return list(monthly.values())


def composition_chart(rows: list[dict[str, int | str]]) -> None:
    if not rows:
        (CHARTS / "composition.svg").write_text(empty_chart("当前存档构成"), encoding="utf-8")
        return
    latest = rows[-1]
    articles, pastes = int(latest["articles"]), int(latest["pastes"])
    total = articles + pastes
    angle = 360 * articles / total if total else 0
    end_x = 200 + 120 * math.cos(math.radians(-90 + angle))
    end_y = 210 + 120 * math.sin(math.radians(-90 + angle))
    large_arc = 1 if angle > 180 else 0
    article_arc = f'M 200 90 A 120 120 0 {large_arc} 1 {end_x:.2f} {end_y:.2f}'
    paste_arc = f'M {end_x:.2f} {end_y:.2f} A 120 120 0 {1-large_arc} 1 200 90'
    body = f'''<text x="48" y="36" class="title">当前存档构成</text>
<path d="{article_arc}" fill="none" stroke="#2563eb" stroke-width="40"/><path d="{paste_arc}" fill="none" stroke="#f97316" stroke-width="40"/>
<text x="200" y="205" text-anchor="middle" class="value">{total:,}</text><text x="200" y="226" text-anchor="middle" class="muted">存档总数</text>
<rect x="430" y="130" width="12" height="12" fill="#2563eb" rx="2"/><text x="450" y="141" class="muted">文章：{articles:,}（{articles / total * 100 if total else 0:.1f}%）</text>
<rect x="430" y="175" width="12" height="12" fill="#f97316" rx="2"/><text x="450" y="186" class="muted">剪贴板：{pastes:,}（{pastes / total * 100 if total else 0:.1f}%）</text>
<text x="48" y="360" class="muted">快照日期：{latest["date"]}</text>'''
    (CHARTS / "composition.svg").write_text(svg_document(960, 400, body), encoding="utf-8")


def render_site(rows: list[dict[str, int | str]]) -> None:
    DOCS.mkdir(exist_ok=True)
    CHARTS.mkdir(exist_ok=True)
    line_chart("已存档文章总量变化", rows, [("articles", "文章")], "articles-total.svg")
    line_chart("已存档剪贴板总量变化", rows, [("pastes", "剪贴板")], "pastes-total.svg")
    line_chart("每日新增存档数", delta_rows(rows), [("articles", "文章"), ("pastes", "剪贴板")], "daily-additions.svg")
    line_chart("每月新增存档数", monthly_rows(rows), [("articles", "文章"), ("pastes", "剪贴板")], "monthly-additions.svg")
    composition_chart(rows)
    latest = rows[-1] if rows else {"date": "等待首次采集", "articles": 0, "pastes": 0}
    total = int(latest["articles"]) + int(latest["pastes"])
    html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>洛谷存档历史统计</title><style>
:root{{color-scheme:light;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#172033;background:#f8fafc}}*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1100px;margin:auto;padding:48px 24px 64px}}h1{{font-size:32px;margin:0 0 8px}}p{{color:#526176;line-height:1.55}}.updated{{font-size:14px}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:28px 0}}.metric{{border:1px solid #dbe3ed;background:white;padding:18px;border-radius:6px}}.metric b{{display:block;font-size:30px;color:#172033;margin-top:5px}}.metric span{{color:#64748b;font-size:14px}}section{{margin-top:36px}}h2{{font-size:19px;margin:0 0 12px}}img{{display:block;width:100%;height:auto;border:1px solid #dbe3ed;background:white;border-radius:6px}}footer{{font-size:14px;margin-top:40px}}a{{color:#1d4ed8}}@media(max-width:600px){{main{{padding:32px 16px}}.metrics{{grid-template-columns:1fr}}h1{{font-size:27px}}}}</style></head>
<body><main><h1>洛谷存档历史统计</h1><p>数据每日从 <a href="https://api.luogu.me">api.luogu.me</a> 自动采集。</p><p class="updated">最近采集：{latest["date"]}</p><div class="metrics"><div class="metric"><span>已存档文章</span><b>{int(latest["articles"]):,}</b></div><div class="metric"><span>已存档剪贴板</span><b>{int(latest["pastes"]):,}</b></div><div class="metric"><span>存档总数</span><b>{total:,}</b></div></div>
<section><h2>文章总量变化</h2><img src="charts/articles-total.svg" alt="已存档文章总量变化"></section><section><h2>剪贴板总量变化</h2><img src="charts/pastes-total.svg" alt="已存档剪贴板总量变化"></section><section><h2>每日新增</h2><img src="charts/daily-additions.svg" alt="每日新增存档数"></section><section><h2>每月新增</h2><img src="charts/monthly-additions.svg" alt="每月新增存档数"></section><section><h2>存档构成</h2><img src="charts/composition.svg" alt="当前存档构成"></section><footer>历史数据：<a href="../data/history.csv">CSV 文件</a> · 由 GitHub Actions 自动生成。</footer></main></body></html>'''
    (DOCS / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    rows = read_history()
    if "--render-only" not in sys.argv:
        try:
            articles = get_count("/article/count")
            pastes = get_count("/paste/count")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            print(f"采集失败：{error}", file=sys.stderr)
            return 1
        snapshot = {"date": china_date(), "articles": articles, "pastes": pastes}
        rows = [row for row in rows if row["date"] != snapshot["date"]] + [snapshot]
        rows.sort(key=lambda row: str(row["date"]))
        write_history(rows)
        print(f"已保存 {snapshot['date']}：{articles} 篇文章，{pastes} 条剪贴板")
    render_site(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
