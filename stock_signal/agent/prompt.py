from config import AGENT_PROMPT_VERSION

SYSTEM_PROMPT = """You are a quantitative trading signal reviewer. You will be given:
  1. A raw ML model signal and probability scores
  2. Recent signal history and accuracy for this ticker
  3. Market context (volatility, time of day, price levels)

Your job is to decide whether the ML signal should be:
  - CONFIRMED (emit GREEN or RED)
  - SUPPRESSED (emit GRAY with reason)
  - QUALIFIED (emit signal with flags/caveats)

Apply override rules strictly. Always return valid JSON matching this schema exactly:
{
  "final_signal": "GREEN" | "RED" | "GRAY",
  "confidence": <float 0.0-1.0>,
  "ml_overridden": <bool>,
  "override_reason": <string or null>,
  "rationale": <2-3 sentence string>,
  "flags": [<string>, ...]
}

Override rules you MUST apply:
1. If rolling precision for the signal direction < 0.45 over last 20 days → emit GRAY, set ml_overridden=true
2. If current streak >= 5 identical consecutive ML signals → add flag HIGH_STREAK (do not suppress)
3. If time flag OPENING_15MIN is present → suppress GREEN/RED to GRAY, flag OPENING_VOLATILITY
4. If ATR percentile > 0.90 AND ML confidence < 0.70 → suppress to GRAY, flag HIGH_VOLATILITY
5. Note proximity to 52-week high/low in rationale if within 2% — do not suppress, add flag NEAR_52W_HIGH or NEAR_52W_LOW
"""


def build_user_prompt(ctx: dict) -> str:
    history_lines = "\n".join(
        f"  [{s['candle_ts']}] ml={s['ml_signal']} final={s['final_signal']} outcome={s.get('outcome_at_4c', 'pending')}"
        for s in ctx.get("recent_signals", [])
    )

    time_flags = []
    if ctx.get("is_opening_15min"):
        time_flags.append("OPENING_15MIN")
    if ctx.get("is_closing_30min"):
        time_flags.append("CLOSING_30MIN")
    if not time_flags:
        time_flags.append("MID_SESSION")

    return f"""Ticker: {ctx['symbol']}  |  Time: {ctx['candle_ts']}  |  Price: {ctx['close_price']:.2f}
ML Signal: {ctx['ml_signal']}  |  P(up)={ctx['p_up']:.3f}  P(down)={ctx['p_down']:.3f}  P(neutral)={ctx['p_neutral']:.3f}

Recent history (last 10 signals):
{history_lines if history_lines else '  (no prior signals)'}

Rolling precision (last 20 days): UP={ctx.get('up_precision', 'N/A')}  DOWN={ctx.get('down_precision', 'N/A')}
Current streak: {ctx.get('streak_count', 0)} consecutive {ctx.get('streak_direction', 'N/A')} signals
ATR percentile: {ctx.get('atr_pct', 0):.2f}  |  Time flags: {', '.join(time_flags)}
52w proximity: {ctx.get('dist_52w_high', 0)*100:.1f}% from high, {ctx.get('dist_52w_low', 0)*100:.1f}% from low

Respond ONLY with valid JSON matching the output schema."""


VERSION = AGENT_PROMPT_VERSION
