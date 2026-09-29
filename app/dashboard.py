"""Read-only lab dashboard backed by the application's structured JSONL logs."""

from __future__ import annotations

import html
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from .challenge import load_challenge
from .metrics import percentile

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = Path(os.getenv("LOG_PATH", str(ROOT / "data" / "logs.jsonl")))
CONTRACT = yaml.safe_load((ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8"))["dashboard"]
PANELS = {panel["id"]: panel for panel in CONTRACT["panels"]}

app = FastAPI(title="Day 13 LLMOps Dashboard")


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _records() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    result = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
            record["_when"] = _timestamp(record["ts"])
        except (ValueError, KeyError, TypeError):
            continue
        result.append(record)
    return result


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _minute_points(rows: list[dict[str, Any]], field: str | None, output_key: str) -> list[dict[str, Any]]:
    totals: dict[datetime, float] = {}
    for row in rows:
        minute = row["_when"].replace(second=0, microsecond=0)
        totals[minute] = totals.get(minute, 0.0) + (_number(row.get(field)) if field else 1.0)
    return [{"_when": minute, output_key: value} for minute, value in sorted(totals.items())]


def _page(title: str, content: str, *, subtitle: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{CONTRACT['refresh_seconds']}">
<title>{html.escape(title)}</title><style>
:root{{--ink:#edf2fb;--muted:#a7b7c9;--line:#34465a;--card:#182a3e;--teal:#50d3c2;--orange:#f5b764;--red:#ee8378}}
*{{box-sizing:border-box}}body{{margin:0;background:#0b1727;color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}}
main{{max-width:1580px;margin:auto;padding:28px 36px 34px}}header{{display:flex;justify-content:space-between;align-items:end;gap:24px;margin-bottom:22px}}
h1{{font-size:30px;line-height:1.1;margin:4px 0 8px}}h2{{font-size:18px;margin:0 0 4px}}p{{margin:0}}.kicker{{color:var(--teal);letter-spacing:.14em;text-transform:uppercase;font-size:12px;font-weight:800}}
.subtitle,.muted{{color:var(--muted)}}.range{{text-align:right;font-variant-numeric:tabular-nums}}.range strong{{display:block;font-size:15px}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;min-height:255px;overflow:hidden}}
.card.wide{{grid-column:span 2}}.value{{font-size:30px;font-weight:750;font-variant-numeric:tabular-nums;line-height:1.15;margin:12px 0 8px}}
.unit{{font-size:13px;color:var(--muted);font-weight:500}}.details{{display:flex;flex-wrap:wrap;gap:6px 18px;margin:9px 0 13px;color:var(--muted);font-size:13px}}
.details strong{{color:var(--ink)}}.chart{{width:100%;height:116px;margin-top:6px}}.threshold{{margin-top:11px;border-top:1px dashed var(--line);padding-top:8px;color:var(--muted);font-size:12px}}
.pill{{display:inline-block;border:1px solid #3b8a81;color:#7be0d3;border-radius:20px;padding:4px 10px;font-size:12px;font-weight:700}}
.incident-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px}}.incident-grid .card{{min-height:118px}}
.incident-grid .value{{font-size:25px}}.focus-chart{{height:380px}}pre{{white-space:pre-wrap;word-break:break-word;background:#08111e;padding:24px;border-radius:12px;border:1px solid var(--line);font:15px/1.55 Consolas,monospace}}
footer{{color:var(--muted);font-size:12px;margin-top:18px}}a{{color:var(--teal)}}
</style></head><body><main><header><div><div class="kicker">K4-L3A / Monitoring &amp; LLMOps</div><h1>{html.escape(title)}</h1><p class="subtitle">{html.escape(subtitle)}</p></div>
<div class="range"><span class="pill">60m window · 30s refresh</span></div></header>{content}</main></body></html>"""


def _chart(rows: list[dict[str, Any]], field: str, start: datetime, end: datetime,
           *, threshold: float | None = None, secondary: float | None = None,
           height: int = 116) -> str:
    width = 1400 if height >= 300 else 900
    pad = 24
    values = [(row["_when"], _number(row.get(field))) for row in rows if row.get(field) is not None]
    ceiling = max([1.0, *(value for _, value in values), threshold or 0, secondary or 0]) * 1.12
    span = max((end - start).total_seconds(), 1.0)
    def xy(when: datetime, value: float) -> tuple[float, float]:
        x = pad + (when - start).total_seconds() / span * (width - 2 * pad)
        y = height - pad - value / ceiling * (height - 2 * pad)
        return x, y
    parts = [f'<svg class="chart" style="height:{height}px" viewBox="0 0 {width} {height}" preserveAspectRatio="none" role="img" aria-label="{html.escape(field)} over time">',
             f'<line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="#34465a"/>']
    for limit, color, label in ((threshold, "#f5b764", "Threshold"), (secondary, "#ee8378", "Challenge")):
        if limit is None:
            continue
        _, y = xy(start, limit)
        parts.append(f'<line x1="{pad}" y1="{y:.1f}" x2="{width-pad}" y2="{y:.1f}" stroke="{color}" stroke-dasharray="8 5"/>')
        parts.append(f'<text x="{width-pad-4}" y="{max(y-5,11):.1f}" text-anchor="end" fill="{color}" font-size="12">{label} {limit:g}</text>')
    for when, value in values:
        x, y = xy(when, value)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.3" fill="#50d3c2"/>')
    if not values:
        parts.append(f'<text x="{width/2}" y="{height/2}" text-anchor="middle" fill="#a7b7c9">No events in selected window</text>')
    if height >= 300:
        parts.append(f'<text x="{pad}" y="{height-4}" fill="#a7b7c9" font-size="12">{start:%H:%M} UTC</text>')
        parts.append(f'<text x="{width-pad}" y="{height-4}" text-anchor="end" fill="#a7b7c9" font-size="12">{end:%H:%M} UTC</text>')
    parts.append("</svg>")
    return "".join(parts)


def _card(title: str, value: str, details: str, chart: str, threshold: str) -> str:
    return f'<section class="card"><h2>{html.escape(title)}</h2><div class="value">{value}</div><div class="details">{details}</div>{chart}<div class="threshold">{html.escape(threshold)}</div></section>'


def _window(records: list[dict[str, Any]], end_text: str | None, minutes: int) -> tuple[datetime, datetime, list[dict[str, Any]]]:
    if end_text == "latest" and records:
        end = max(row["_when"] for row in records) + timedelta(seconds=15)
    elif end_text:
        try:
            end = _timestamp(end_text)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="end must be an ISO timestamp or latest") from exc
    else:
        end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    return start, end, [row for row in records if start <= row["_when"] <= end]


@app.get("/", response_class=HTMLResponse)
def dashboard(end: str | None = None, minutes: int = Query(60, ge=5, le=1440)) -> str:
    start, window_end, rows = _window(_records(), end, minutes)
    requests = [row for row in rows if row.get("event") == "request_received"]
    responses = [row for row in rows if row.get("event") == "response_sent"]
    failures = [row for row in rows if row.get("event") == "request_failed"]
    latencies = [int(_number(row.get("latency_ms"))) for row in responses]
    ttfts = [int(_number(row.get("ttft_ms"))) for row in responses]
    traffic_by_minute = Counter(row["_when"].strftime("%H:%M") for row in requests)
    traffic_points = _minute_points(requests,None,"rate_per_minute")
    failure_by_minute = Counter(row["_when"].replace(second=0,microsecond=0) for row in failures)
    error_points = [{"_when": point["_when"], "error_rate_pct": 100 * failure_by_minute[point["_when"]] / point["rate_per_minute"]} for point in traffic_points]
    error_rate = 100 * len(failures) / len(requests) if requests else 0.0
    retrieval = [row for row in responses + failures if row.get("tool_success") is not None]
    retrieval_success = 100 * sum(row.get("tool_success") is True for row in retrieval) / len(retrieval) if retrieval else 0.0
    total_cost = sum(_number(row.get("cost_usd")) for row in responses)
    tokens_in = sum(int(_number(row.get("tokens_in"))) for row in responses)
    tokens_out = sum(int(_number(row.get("tokens_out"))) for row in responses)
    qualities = [_number(row.get("quality_score")) for row in responses if row.get("quality_score") is not None]
    subtitle = f'{start:%Y-%m-%d %H:%M}–{window_end:%H:%M} UTC · Source: data/logs.jsonl · {minutes} minute window'
    cards = [
        _card(PANELS["latency"]["title"], f'{percentile(latencies,95):.0f} <span class="unit">ms P95</span>',
              f'<span>P50 <strong>{percentile(latencies,50):.0f} ms</strong></span><span>P99 <strong>{percentile(latencies,99):.0f} ms</strong></span><span>TTFT P95 <strong>{percentile(ttfts,95):.0f} ms</strong></span>',
              _chart(responses,"latency_ms",start,window_end,threshold=3000),"SLO line: latency P95 ≤ 3000 ms"),
        _card(PANELS["traffic"]["title"], f'{len(requests)} <span class="unit">requests</span>',
              f'<span>Peak <strong>{max(traffic_by_minute.values(),default=0)} req/min</strong></span><span>Average <strong>{len(requests)/minutes:.2f} req/min</strong></span>',
              _chart(traffic_points,"rate_per_minute",start,window_end),"Count of request_received, grouped by minute"),
        _card(PANELS["errors"]["title"], f'{error_rate:.1f}<span class="unit">% errors</span>',
              f'<span>Failed <strong>{len(failures)}</strong></span><span>Retrieval success <strong>{retrieval_success:.1f}%</strong></span>',
              _chart(error_points,"error_rate_pct",start,window_end,threshold=2),"Error-rate threshold ≤ 2%; retrieval success target ≥ 90%"),
        _card(PANELS["cost"]["title"], f'${total_cost:.4f} <span class="unit">total USD</span>',
              f'<span>Responses <strong>{len(responses)}</strong></span><span>Daily guardrail <strong>$2.50</strong></span>',
              _chart(_minute_points(responses,"cost_usd","cost_per_minute"),"cost_per_minute",start,window_end),"Cost sum by minute and full window; guardrail $2.50/day"),
        _card(PANELS["tokens"]["title"], f'{tokens_in+tokens_out:,} <span class="unit">tokens</span>',
              f'<span>Input <strong>{tokens_in:,}</strong></span><span>Output <strong>{tokens_out:,}</strong></span>',
              _chart(responses,"tokens_out",start,window_end),"Input/output totals; window guardrail 50,000 tokens"),
        _card(PANELS["quality"]["title"], f'{mean(qualities) if qualities else 0:.2f} <span class="unit">mean score</span>',
              f'<span>Scored responses <strong>{len(qualities)}</strong></span><span>Scale <strong>0–1</strong></span>',
              _chart(responses,"quality_score",start,window_end,threshold=.75),"Quality proxy target ≥ 0.75"),
    ]
    content = '<div class="grid">' + "".join(cards) + '</div><footer>Auto-refresh every 30 seconds. Values are computed from structured logs when this page is requested.</footer>'
    return _page("Operations dashboard", content, subtitle=subtitle)


@app.get("/incident", response_class=HTMLResponse)
def incident(end: str | None = None, minutes: int = Query(60, ge=5, le=1440)) -> str:
    start, window_end, rows = _window(_records(), end, minutes)
    responses = [row for row in rows if row.get("event") == "response_sent"]
    challenge_rows = [row for row in responses if "challenge" in str(row.get("session_id", ""))]
    challenge_start = min((row["_when"] for row in challenge_rows), default=window_end)
    earlier = sorted((row for row in responses if row not in challenge_rows and row["_when"] < challenge_start), key=lambda row: row["_when"])
    batches: list[list[dict[str, Any]]] = []
    for row in earlier:
        if not batches or row["_when"] - batches[-1][-1]["_when"] > timedelta(seconds=60):
            batches.append([])
        batches[-1].append(row)
    baseline_rows = next((batch for batch in reversed(batches) if len(batch) >= 5), [])
    baseline_p95 = percentile([int(_number(row.get("latency_ms"))) for row in baseline_rows],95)
    challenge_p95 = percentile([int(_number(row.get("latency_ms"))) for row in challenge_rows],95)
    try:
        challenge = load_challenge(ROOT / "config" / "challenge.json")
        challenge_limit = challenge.latency_threshold_ms
        challenge_id = challenge.challenge_id
    except (FileNotFoundError, ValueError):
        challenge_limit = None
        challenge_id = "No official challenge loaded"
    metrics = [
        ("Baseline P95",f"{baseline_p95:.0f} ms"),
        ("Challenge P95",f"{challenge_p95:.0f} ms"),
        ("Official threshold",f"{challenge_limit} ms" if challenge_limit else "N/A"),
        ("Affected responses",str(len(challenge_rows))),
    ]
    cards = "".join(f'<section class="card"><h2>{html.escape(label)}</h2><div class="value">{html.escape(value)}</div></section>' for label,value in metrics)
    chart = _chart(baseline_rows+challenge_rows,"latency_ms",start,window_end,threshold=3000,secondary=challenge_limit,height=380)
    content = f'<div class="incident-grid">{cards}</div><section class="card" style="min-height:460px"><h2>Latency timeline · response_sent</h2><p class="muted">Comparison: latest earlier workload batch ({len(baseline_rows)} responses) and official challenge ({len(challenge_rows)} responses). Isolated requests are excluded from this comparison. Orange: SLO 3000 ms. Red: challenge threshold.</p>{chart}</section><footer>Source: data/logs.jsonl · Challenge ID: {html.escape(challenge_id)} · {start:%Y-%m-%d %H:%M}–{window_end:%H:%M} UTC</footer>'
    return _page("Incident metric", content, subtitle=f"{start:%Y-%m-%d %H:%M}–{window_end:%H:%M} UTC · {minutes} minute window")


@app.get("/log/{correlation_id}", response_class=HTMLResponse)
def log_record(correlation_id: str) -> str:
    allowed = {"ts","level","service","event","correlation_id","env","user_id_hash","session_id","feature","model","latency_ms","ttft_ms","tokens_in","tokens_out","cost_usd","quality_score","tool_name","tool_success"}
    record = next((row for row in _records() if row.get("correlation_id") == correlation_id and row.get("event") == "response_sent"),None)
    if record is None:
        raise HTTPException(status_code=404,detail="No response_sent log for correlation ID")
    safe = {key:value for key,value in record.items() if key in allowed}
    content = f'<section class="card" style="min-height:400px"><h2>response_sent · {html.escape(correlation_id)}</h2><p class="muted">Selected fields from the application-generated data/logs.jsonl record</p><pre>{html.escape(json.dumps(safe,indent=2,ensure_ascii=False))}</pre></section><footer>Use the same correlation ID to find the matching Langfuse trace.</footer>'
    return _page("Incident structured log",content,subtitle=f'Correlation ID {correlation_id}')
