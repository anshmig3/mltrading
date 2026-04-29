import json
import logging
import time

import anthropic

from agent.context_builder import build_context
from agent.prompt import SYSTEM_PROMPT, VERSION, build_user_prompt
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, NLP_TIMEOUT_SECONDS
from data.db import db

logger = logging.getLogger(__name__)

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def run_agent(inference_result: dict) -> dict:
    ctx = build_context(inference_result)
    user_prompt = build_user_prompt(ctx)

    start = time.time()
    error = None
    response_raw = None
    decision = None

    try:
        client = get_client()
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=NLP_TIMEOUT_SECONDS,
        )
        response_raw = message.content[0].text
        decision = json.loads(response_raw)
    except anthropic.APITimeoutError:
        error = "timeout"
        logger.warning("NLP agent timed out for %s", inference_result["symbol"])
    except json.JSONDecodeError as e:
        error = f"json_parse_error: {e}"
        logger.error("Failed to parse agent response for %s: %s", inference_result["symbol"], response_raw)
    except Exception as e:
        error = str(e)
        logger.error("Agent error for %s: %s", inference_result["symbol"], e)

    latency_ms = int((time.time() - start) * 1000)

    if decision is None:
        ml_map = {"ML_GREEN": "GREEN", "ML_RED": "RED", "ML_GRAY": "GRAY"}
        decision = {
            "final_signal": ml_map.get(inference_result["ml_signal"], "GRAY"),
            "confidence": inference_result.get("p_up", 0.5),
            "ml_overridden": False,
            "override_reason": None,
            "rationale": "NLP agent unavailable — showing raw ML signal.",
            "flags": ["NLP_UNAVAILABLE"],
        }

    signal_id = _save_signal(inference_result, decision)
    _save_agent_log(signal_id, user_prompt, response_raw, latency_ms, error)

    return {**inference_result, **decision, "signal_id": signal_id}


def _save_signal(inf: dict, decision: dict) -> int:
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO signals
               (symbol, candle_ts, p_up, p_down, p_neutral, ml_signal,
                final_signal, confidence, ml_overridden, override_reason,
                rationale, flags, model_version, agent_prompt_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                inf["symbol"], inf["candle_ts"],
                inf["p_up"], inf["p_down"], inf["p_neutral"],
                inf["ml_signal"],
                decision["final_signal"],
                decision["confidence"],
                int(decision.get("ml_overridden", False)),
                decision.get("override_reason"),
                decision.get("rationale"),
                json.dumps(decision.get("flags", [])),
                inf.get("model_version"),
                VERSION,
            ),
        )
    return cur.lastrowid


def _save_agent_log(signal_id: int, prompt: str, response: str, latency_ms: int, error: str | None) -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO agent_log (signal_id, prompt_sent, response_raw, latency_ms, error)
               VALUES (?, ?, ?, ?, ?)""",
            (signal_id, prompt, response, latency_ms, error),
        )
