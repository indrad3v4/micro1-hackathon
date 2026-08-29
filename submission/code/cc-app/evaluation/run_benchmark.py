#!/usr/bin/env python3
"""Creator Court 2.0 — measured-improvement benchmark (micro1 Agentic Workflows Hackathon).

Compares two systems on the SAME 10 demo briefs (creative-court/demo_briefs/*.json):

  BASELINE  "one-shot heuristic judge" — the deterministic JudgeAgent._heuristic_score
            path (word-overlap / frame-table scoring, zero reasoning). No LLM calls.
            This is the fair simple baseline defined for this hackathon.

  ADVANCED  "full Creator->Judge pipeline" — CreatorAgent generates 6 ИКРА-frame
            directions via the LLM, JudgeAgent scores every direction with the
            LLM rubric prompt (relevance/novelty/feasibility/risk/quality),
            rejected drift directions are vetoed and replaced via a retry loop.
            Every step lands in a TraceRecorder JSONL trajectory.

Fairness: each brief gets ONE hand-written "drift probe" — a confident-sounding
direction that violates an explicit hard constraint of the brief, but is lexically
saturated with brief keywords (its worst-case for the overlap heuristic). The probe
text is IDENTICAL in both conditions, so the drift-catch comparison is apples-to-apples.

Primary outcome per brief:
  * mean verdict score over the 6 generated directions (judge output quality signal)
  * drift-catch: was the probe rejected (total < 60) or vetoed? (0/1; aggregate = rate)

Secondary outcomes per task:
  * human-time proxy (MODELLED minutes, constants documented below — not measured)
  * wall-clock runtime per task (measured, seconds)
  * token cost per task (measured from API `usage` incl. authoritative `usage.cost`
    when present; chars/4 estimate fallback), advanced LLM path only.

Human-time proxy model (documented assumptions, minutes):
  baseline  = 2.0 (read brief)
            + 4.0 * N_directions_written_by_hand (ideation)
            + 1.0 * N_directions_scored (one-shot scoring)
  advanced  = 0.5 * N_verdicts_reviewed
            + 1.5 * N_vetoes
            + 1.0 * N_replacement_checks
            + 1.0 (final sign-off)

Known pitfalls handled:
  * agents resolve prompts relative to __file__ (creative-court/prompts, which does
    not exist) -> this harness injects the repo prompt text explicitly.
  * deepseek-v4-flash-vision-exp is a reasoning model: can finish with empty
    content when max_tokens is exhausted -> chat wrapper clamps max_tokens and
    retries with a bigger budget.
  * JudgeAgent.judge() has no per-direction try/except -> harness wraps it and
    falls back to per-direction scoring with heuristic on parse failure
    (recorded as retry events, so the numbers stay honest).

Usage:
  /opt/hermes/venv/bin/python /root/.hermes/micro1-hackathon/cc-app/evaluation/run_benchmark.py [--limit N] [--no-llm]

Outputs (created next to this file):
  results/final_report.json   full machine-readable evidence
  results/final_report.csv    one row per brief + totals
  results/per_brief/<id>.json incremental per-brief results (crash-safe)
  results/traces/*.jsonl      trajectory files (TraceRecorder format)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics
import sys
import time
import urllib.request
from pathlib import Path

# --- repo wiring -------------------------------------------------------------
HERE = Path(__file__).resolve().parent                       # cc-app/evaluation
ROOT = HERE.parent.parent                                    # micro1-hackathon/
CC = ROOT / "creative-court"
sys.path.insert(0, str(CC / "src"))

from creative_court.core.models import Brief, Direction, Verdict  # noqa: E402
from creative_court.core.trace import TraceRecorder, export_trace_metrics  # noqa: E402
from creative_court.core.llm import LLMClient, heuristic_directions  # noqa: E402
import creative_court.agents.creator as creator_mod  # noqa: E402
from creative_court.agents.creator import CreatorAgent  # noqa: E402
from creative_court.agents.judge import JudgeAgent, RUBRICS  # noqa: E402

CREATOR_PROMPT = (ROOT / "prompts" / "creator_prompt.txt").read_text(encoding="utf-8").strip()
JUDGE_PROMPT = (ROOT / "prompts" / "judge_prompt.txt").read_text(encoding="utf-8").strip()


def _format_safe(prompt: str) -> str:
    """JudgeAgent._llm_score runs str.format() over the prompt, but the prompt
    contains literal JSON braces in its OUTPUT FORMAT section -> .format() dies.
    Double every brace that is not part of a known {placeholder}."""
    keys = ("brief_title", "brief_description", "brief_audience", "brief_constraints",
            "direction_frame", "direction_name", "direction_concept",
            "direction_rationale", "direction_risks")
    out = prompt.replace("{", "{{").replace("}", "}}")
    for k in keys:
        out = out.replace("{{" + k + "}}", "{" + k + "}")
    return out


JUDGE_PROMPT = _format_safe(JUDGE_PROMPT)
# Inject prompts where agents would have looked (their __file__-relative path
# points at a non-existent creative-court/prompts dir).
creator_mod._CREATOR_SYSTEM = CREATOR_PROMPT

BRIEFS_DIR = CC / "demo_briefs"
RESULTS_DIR = HERE / "results"
TRACES_DIR = RESULTS_DIR / "traces"
PER_BRIEF_DIR = RESULTS_DIR / "per_brief"

REJECT_THRESHOLD = 60.0  # same threshold the production JudgeAgent uses

# --- human-time proxy constants (MODELLED, see docstring) --------------------
MIN_READ_BRIEF = 2.0
MIN_WRITE_DIRECTION = 4.0
MIN_SCORE_DIRECTION = 1.0
MIN_REVIEW_VERDICT = 0.5
MIN_VETO_REVIEW = 1.5
MIN_RETRY_CHECK = 1.0
MIN_SIGN_OFF = 1.0

# chars/4 token estimate fallback (only used if API omits usage)
CHARS_PER_TOKEN = 4.0

MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash-vision-exp")
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.cometapi.com/v1")

# --- drift probes ------------------------------------------------------------
# One per brief: sounds like a strong pitch, repeats brief vocabulary (worst
# case for keyword-overlap heuristics), but blatantly violates a HARD
# constraint of that brief. Russian, matching brief language. Identical text is
# fed to both conditions.
DRIFT_PROBES: dict[str, dict] = {
    "eval_01_coffee": {
        "frame": "professional", "name": "Кофейный сомелье в смартфоне",
        "concept": "Умная кофеварка работает ТОЛЬКО в связке с обязательным премиум-приложением: "
                   "настроение владельца считывается с большого сенсорного экрана смартфона, рецепт "
                   "синхронизируется с календарём и доставляется push-уведомлением. Персональный "
                   "кофейный сомелье подбирает рецепт по привычкам — подписка на приложение 990 руб/мес, "
                   "сама кофеварка с экраном — 45 000 руб.",
        "rationale": "Максимальная интеграция смартфона и умного дома превращает утренний кофе "
                     "в ритуал, ради которого встают раньше: городские профессионалы 25-40 живут в телефоне.",
        "risks": [],
    },
    "eval_02_perfume": {
        "frame": "social", "name": "Телевизионная премьера «Северного света»",
        "concept": "Запуск аромата «Северный свет» через выкуп prime-time рейтингов: серия из 12 "
                   "тридцатисекундных телевизионных роликов о полярной ночи и первом снеге на федеральных "
                   "каналах в декабре, плюс наружная реклама на щитах 3х6 у метро. История аромата "
                   "рассказывается диктором за кадром без единого слова от самого бренда.",
        "rationale": "Телевидение даёт мгновенный охват 500 флаконам за 2 недели: нишевый парфюмерный "
                     "бренд заявляет о себя громче всех в соцсетях и офлайн-ивентах.",
        "risks": [],
    },
    "eval_03_sleep_app": {
        "frame": "ritual", "name": "Спальня как герой кампании",
        "concept": "Ключевой визуал «Дрёмы» — уютная спальня: мягкая кровать, светлый матрас, засыпающая "
                   "пара под голос диктора и звуки природы. Медиаплан: таргетированная реклама с бюджетом "
                   "3 млн руб на баннеры «засыпай в этой спальне за 10 000 установок».",
        "rationale": "Образ спальни и кровати — прямая ассоциация со сном, а платный трафик быстро "
                     "приведёт 10 000 установок в первый месяц среди тех, кто конкурирует с десятками похожих приложений.",
        "risks": [],
    },
    "eval_04_bike_delivery": {
        "frame": "natural", "name": "Зелёная волна курьеров",
        "concept": "Фирменный стиль «Зелёный курьер»: кислотный зелёный Pantone на форме, рюкзаках и "
                   "электровелосипедах, а в рекламе — крупные фото реальных курьеров-героев в историческом "
                   "центре города: тихая и чистая быстрая доставка еды лицами людей.",
        "rationale": "Зелёный цвет — очевидная метафора экологичности электровелосипедов, а лица курьеров "
                     "вызывают доверие к первым 1000 заказам за квартал.",
        "risks": [],
    },
    "eval_05_art_expo": {
        "frame": "historical", "name": "Энциклопедия выставки",
        "concept": "«Горизонт событий» — трёхчасовой экскурс по всем залам с развёрнутыми текстовыми "
                   "пояснениями на стенах у каждой работы: история скорости, теория выгорания, биографии "
                   "художников. Посетители читают и выходят с ощущением глубокой тревоги и понимания темы.",
        "rationale": "Текстовые пояснения гарантируют, что 60% посетителей дойдут до финального зала, "
                     "вооружившись знаниями о времени.",
        "risks": [],
    },
    "eval_06_bakery": {
        "frame": "professional", "name": "Крафтовый громкий старт",
        "concept": "«Тёплый мякиш» громко заявляет о себе словом «крафтовый» на вывеске, упаковке и в "
                   "каждом посте: крафтовая пекарня для крафтовых людей. Медиакампания на 3 млн руб "
                   "запускается через полгода, к старому фонду рецептов прабабушки это отношения не имеет.",
        "rationale": "Слово «крафтовый» сразу позиционирует семейную пекарню в новом квартале как "
                     "центр притяжения с очередью у двери.",
        "risks": [],
    },
    "eval_07_kids_coding": {
        "frame": "social", "name": "Программист к 14 — миллион в кармане",
        "concept": "Кампания обещает родителям: ваш ребёнок к 14 годам станет профессиональным "
                   "программистом и будет зарабатывать на разработке больше вас — будущая профессия и "
                   "высокий доход гарантированы методикой. Размещение — закупка у блогеров в TikTok и "
                   "YouTube, дети 9-14 создают игры за экранами по 6 часов в день.",
        "rationale": "Обещание дохода — самый сильный аргумент в родительских сообществах Telegram.",
        "risks": [],
    },
    "eval_08_cheese": {
        "frame": "artistic", "name": "Максимальная сырная фотосетка",
        "concept": "Упаковка «Луговой»: гиперреалистичные фотографии продукта крупным планом — сыр с "
                   "дырками на трёхметровом баннере и на каждом фэйсе. Для чистоты минималистичного "
                   "дизайна состав, ГОСТ и штрихкод вынесены в QR-код на крышке — на полке федеральной "
                   "сети узнаваемость обеспечена.",
        "rationale": "Фотографии продукта — прямой путь к аппетиту: сыр узнают с трёх метров.",
        "risks": [],
    },
    "eval_09_food_fest": {
        "frame": "ritual", "name": "Пивная легенда Перекрёстка",
        "concept": "«Перекрёсток» остаётся до финала, потому что в центре парка ставим большой "
                   "спонсорский шатёр с крафтовым разливным алкоголем: дегустации 20 корнеров, бар работает "
                   "весь вечер — гости не уйдут. Спонсор покрывает весь дополнительный бюджет фестиваля "
                   "и ещё 2 сцены.",
        "rationale": "Алкоголь — ритуал городской вечерней еды, 80% гостей останутся на финальный концерт.",
        "risks": [],
    },
    "eval_10_edge_hotel": {
        "frame": "professional", "name": "Идеальный баланс: детокс без ограничений",
        "concept": "Тихий отель для выгоревших полностью решает противоречие: гости живут в полном "
                   "цифровом отдыхе без экранов и интернета, при этом получают push-уведомления о каждом "
                   "активити, все общие пространства ведут непрерывную livestream-трансляцию в соцсети, "
                   "умные номера управляются голосовым ассистентом 24/7, а доступ к рабочей почте и "
                   "созвонам открыт из каждой точки отеля. Высокая заполняемость и полная цифровая "
                   "тишина одновременно — инфлюенсеры и цифровые детоксы счастливы.",
        "rationale": "Одновременное удовлетворение всех требований брифа: никаких экранов, но все экраны.",
        "risks": [],
    },
}


# --- metered LLM client ------------------------------------------------------
class MeteredLLM(LLMClient):
    """LLMClient with real token accounting + reasoning-model hardening.

    Overrides chat() to call the OpenAI-compatible endpoint directly so we can
    capture `usage` (prompt/completion tokens and the authoritative `cost`
    field the API returns). Retries on empty content (reasoning model can
    burn the whole budget thinking) and scales max_tokens up per attempt.
    """

    def __init__(self, model: str | None = None):
        super().__init__(model=model or MODEL)
        self.base = BASE_URL
        self.usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                      "total_tokens": 0, "cost_usd": 0.0, "estimated": 0, "failures": 0}

    def snapshot(self) -> dict:
        return json.loads(json.dumps(self.usage))

    @staticmethod
    def _estimate(text: str) -> int:
        return max(1, round(len(text) / CHARS_PER_TOKEN))

    def chat(self, system: str, user: str, max_tokens: int = 4096, temperature: float = 0.7) -> str:
        if not self.available:
            raise RuntimeError("no LLM key configured — use heuristic fallback")
        # reasoning models burn tokens before answering: never let the caller
        # starve the budget, and grow it on retries.
        budget = max(max_tokens, 8192)
        last_err: Exception | None = None
        for attempt in range(3):
            body = json.dumps({
                "model": self.model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "max_tokens": budget,
                "temperature": temperature,
            }).encode()
            req = urllib.request.Request(f"{self.base}/chat/completions", data=body,
                                         headers={"Content-Type": "application/json",
                                                  "Authorization": f"Bearer {self.key}"})
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode())
                choice = data["choices"][0]
                content = (choice["message"].get("content") or "").strip()
                usage = data.get("usage") or {}
                self.usage["calls"] += 1
                if usage.get("prompt_tokens") is not None:
                    self.usage["prompt_tokens"] += int(usage["prompt_tokens"])
                    self.usage["completion_tokens"] += int(usage.get("completion_tokens", 0))
                    self.usage["total_tokens"] += int(usage.get("total_tokens", 0))
                    self.usage["cost_usd"] += float(usage.get("cost", 0.0) or 0.0)
                else:  # no usage in response -> chars/4 estimate
                    self.usage["estimated"] += 1
                    self.usage["prompt_tokens"] += self._estimate(system + user)
                    self.usage["completion_tokens"] += self._estimate(content)
                    self.usage["total_tokens"] = (self.usage["prompt_tokens"]
                                                  + self.usage["completion_tokens"])
                if content:
                    return content
                # empty content with finish_reason=length: retry with bigger budget
                last_err = RuntimeError(f"empty content (finish={choice.get('finish_reason')})")
                budget = min(budget * 2, 32768)
            except Exception as exc:  # network/HTTP errors
                self.usage["failures"] += 1
                last_err = exc
                time.sleep(2.0 * (attempt + 1))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    def stage(self) -> dict:
        """Cost/token delta bookkeeping helper."""
        snap = self.snapshot()
        cost = snap["cost_usd"]
        if snap["estimated"] and not cost:
            # price only known via API cost field; conservative public deepseek
            # list price used when API omitted it ($0.064/$0.129 per 1M in/out)
            cost = (snap["prompt_tokens"] / 1e6 * 0.064
                    + snap["completion_tokens"] / 1e6 * 0.129)
        return {"calls": snap["calls"], "prompt_tokens": snap["prompt_tokens"],
                "completion_tokens": snap["completion_tokens"],
                "total_tokens": snap["total_tokens"], "cost_usd": round(cost, 6),
                "usage_estimated": snap["estimated"], "api_failures": snap["failures"]}


def _delta(before: dict, after: dict) -> dict:
    return {k: (round(after[k] - before[k], 6) if k == "cost_usd"
                else after[k] - before[k]) for k in after}


# --- shared helpers ----------------------------------------------------------
def load_brief(path: Path) -> Brief:
    d = json.loads(path.read_text(encoding="utf-8"))
    return Brief(title=d["title"], description=d["description"],
                 audience=d.get("audience", ""), constraints=d.get("constraints", []),
                 goal=d.get("goal", ""))


def probe_for(brief_id: str) -> Direction:
    return Direction(**DRIFT_PROBES[brief_id])


def verdicts_payload(directions: list[Direction], verdicts: list[Verdict]) -> list[dict]:
    by_id = {v.direction_id: v for v in verdicts}
    out = []
    for d in directions:
        vid = f"{d.frame}:{d.name}"
        v = by_id.get(vid)
        if not v:
            continue
        out.append({
            "direction_id": vid,
            "total": v.total,
            "approved": v.approved,
            "vetoed": v.vetoed,
            "veto_reason": v.veto_reason,
            "scores": {s.dimension: s.score for s in v.scores},
            "comments": {s.dimension: s.comment for s in v.scores},
        })
    return out


def robust_judge(judge: JudgeAgent, rec: TraceRecorder, brief: Brief,
                 directions: list[Direction], llm_mode: bool) -> tuple[list[Verdict], int]:
    """Judge all directions. On LLM-mode failure, retry once, then degrade to
    per-direction scoring (heuristic fallback recorded as retry). Returns
    (verdicts, fallback_count)."""
    try:
        return judge.judge(brief, directions), 0
    except Exception as exc:
        if not llm_mode:
            raise
        rec.retry("judge", "judge_batch", f"batch judging failed ({exc}); retrying")
        try:
            return judge.judge(brief, directions), 0
        except Exception as exc2:
            rec.retry("judge", "judge_batch_retry",
                      f"retry failed ({exc2}); per-direction heuristic fallback")
            # per-direction, isolating parse failures
            verdicts = []
            fallbacks = 0
            good = []
            for d in directions:
                try:
                    scores = judge._llm_score(d, brief)
                except Exception:
                    scores = judge._heuristic_score(d, brief)
                    fallbacks += 1
                total = round(sum(s.score * w for (_, w, _), s in zip(RUBRICS, scores)), 1)
                good.append(Verdict(direction_id=f"{d.frame}:{d.name}", total=total,
                                    scores=scores,
                                    summary=f"{d.name}: {total}/100 — "
                                            f"{'approved' if total >= REJECT_THRESHOLD else 'rejected'}",
                                    approved=total >= REJECT_THRESHOLD))
            good.sort(key=lambda v: v.total, reverse=True)
            return good, fallbacks


def human_time_baseline(n_directions: int, n_scored: int) -> float:
    return (MIN_READ_BRIEF + MIN_WRITE_DIRECTION * n_directions
            + MIN_SCORE_DIRECTION * n_scored)


def human_time_advanced(n_verdicts: int, n_vetoes: int, n_replacements: int) -> float:
    return (MIN_REVIEW_VERDICT * n_verdicts + MIN_VETO_REVIEW * n_vetoes
            + MIN_RETRY_CHECK * n_replacements + MIN_SIGN_OFF)


# --- conditions --------------------------------------------------------------
def run_baseline(brief: Brief, brief_id: str, no_llm: bool) -> dict:
    """Heuristic one-shot judge over template directions + the shared probe.
    Zero LLM calls, deterministic."""
    trace_path = TRACES_DIR / f"bench_{brief_id}_baseline.jsonl"
    t0 = time.perf_counter()
    with TraceRecorder(str(trace_path), meta={"mode": "baseline", "brief": brief_id}) as rec:
        directions = [Direction(**d) for d in heuristic_directions(brief)]
        probe = probe_for(brief_id)
        directions.append(probe)
        rec.event(agent="creator", type="agent_step",
                  action=f"one-shot heuristics produced {len(directions) - 1} template directions")
        judge = JudgeAgent(rec, llm=LLMClient())  # fresh client, key forced off
        judge.llm.key = None                      # heuristic path guaranteed
        judge._prompt_text = ""
        verdicts, _ = robust_judge(judge, rec, brief, directions, llm_mode=False)
        probe_id = f"{probe.frame}:{probe.name}"
        pv = next(v for v in verdicts if v.direction_id == probe_id)
        caught = pv.total < REJECT_THRESHOLD
        rec.event(agent="judge", type="agent_end",
                  action=f"one-shot heuristic verdicts issued; probe caught={caught}")
    wall = time.perf_counter() - t0

    real = [v for v in verdicts if v.direction_id != probe_id]
    totals = [v.total for v in real]
    return {
        "mode": "baseline",
        "llm_used": False,
        "wall_clock_s": round(wall, 3),
        "llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
        "total_tokens": 0, "cost_usd": 0.0,
        "n_directions": len(real),
        "mean_score": round(statistics.mean(totals), 1) if totals else None,
        "score_spread": round(max(totals) - min(totals), 1) if totals else None,
        "probe_total": pv.total,
        "drift_caught": bool(caught),
        "vetoes": 0, "replacements": 0, "judge_fallbacks": 0,
        "human_time_min": round(human_time_baseline(len(real), len(directions)), 1),
        "verdicts": verdicts_payload(directions, verdicts),
        "trace": export_trace_metrics(str(trace_path)) if trace_path.exists() else {},
    }


def run_advanced(brief: Brief, brief_id: str, no_llm: bool) -> dict:
    """Full Creator -> Judge pipeline with LLM rubric scoring + veto/retry loop."""
    trace_path = TRACES_DIR / f"bench_{brief_id}_advanced.jsonl"
    t0 = time.perf_counter()
    llm = MeteredLLM()
    replacements = 0
    vetoes = 0
    fallbacks = 0
    with TraceRecorder(str(trace_path), meta={"mode": "advanced", "brief": brief_id,
                                              "model": llm.model}) as rec:
        creator = CreatorAgent(rec, llm=llm)
        judge = JudgeAgent(rec, llm=llm)
        judge._prompt_text = JUDGE_PROMPT  # same __file__ pitfall as creator
        if no_llm:
            offline = LLMClient()
            offline.key = None  # force the heuristic path everywhere
            creator.llm = offline
            judge.llm = offline
            judge._prompt_text = ""

        # 1) Creator: 6 ИКРА-frame directions (LLM-backed when key present)
        directions = creator.generate(brief)
        probe = probe_for(brief_id)
        probe_id = f"{probe.frame}:{probe.name}"
        # drop any creator direction that collides with the probe id (shouldn't happen)
        directions = [d for d in directions if f"{d.frame}:{d.name}" != probe_id]
        scored_directions = list(directions) + [probe]

        # 2) Judge: rubric verdicts for all directions
        llm_mode = not no_llm
        verdicts, fb = robust_judge(judge, rec, brief, scored_directions, llm_mode)
        fallbacks += fb
        by_id = {v.direction_id: v for v in verdicts}
        pv = by_id.get(probe_id)
        if pv is None:  # probe lost in a fallback round — re-judge it alone
            one, fb2 = robust_judge(judge, rec, brief, [probe], llm_mode)
            fallbacks += fb2
            pv = one[0]
            verdicts.append(pv)

        # 3) Veto/retry loop: drift caught by the judge is vetoed and the
        #    Creator must replace it within constraints.
        caught = bool(pv.total < REJECT_THRESHOLD)
        if caught:
            judge.veto(pv, "Court veto: direction violates an explicit hard "
                           "constraint of the brief (drift from brief).")
            vetoes += 1
            replacement = _regenerate_replacement(rec, llm if llm_mode else None, brief, probe)
            scored_directions.append(replacement)
            rvs, fb3 = robust_judge(judge, rec, brief, [replacement], llm_mode)
            fallbacks += fb3
            replacements += 1
            verdicts.extend(rvs)

        rec.event(agent="pipeline", type="agent_end",
                  action=f"advanced pipeline finished: verdicts={len(verdicts)}, "
                         f"vetoes={vetoes}, replacements={replacements}")
    wall = time.perf_counter() - t0

    real = [v for v in verdicts
            if v.direction_id != probe_id and not v.vetoed]
    totals = [v.total for v in real]
    stage = llm.stage()
    return {
        "mode": "advanced",
        "llm_used": not no_llm and stage["calls"] > 0,
        "wall_clock_s": round(wall, 2),
        "llm_calls": stage["calls"], "prompt_tokens": stage["prompt_tokens"],
        "completion_tokens": stage["completion_tokens"],
        "total_tokens": stage["total_tokens"], "cost_usd": round(stage["cost_usd"], 5),
        "usage_estimated": stage["usage_estimated"], "api_failures": stage["api_failures"],
        "n_directions": len(totals),
        "mean_score": round(statistics.mean(totals), 1) if totals else None,
        "score_spread": round(max(totals) - min(totals), 1) if totals else None,
        "probe_total": pv.total,
        "drift_caught": caught,
        "vetoes": vetoes, "replacements": replacements, "judge_fallbacks": fallbacks,
        "human_time_min": round(human_time_advanced(len(verdicts), vetoes, replacements), 1),
        "verdicts": verdicts_payload(scored_directions, verdicts),
        "trace": export_trace_metrics(str(trace_path)) if trace_path.exists() else {},
    }


def _regenerate_replacement(rec: TraceRecorder, llm: MeteredLLM | None,
                            brief: Brief, vetoed: Direction) -> Direction:
    """One-shot Creator retry: single replacement direction for the vetoed
    frame, explicitly instructed to respect constraints."""
    agent = "creator"
    rec.retry(agent, vetoed.name, f"vetoed direction replaced (frame: {vetoed.frame})")
    constraints = "\n".join(f"- {c}" for c in brief.constraints) or "(none)"
    if llm is not None and llm.available:
        try:
            user = (f"{CREATOR_PROMPT}\n\n---\n"
                    f"BRIEF:\nTitle: {brief.title}\nDescription: {brief.description}\n"
                    f"Audience: {brief.audience}\nGoal: {brief.goal}\n"
                    f"HARD CONSTRAINTS (a previous direction was VETOED for violating these):\n{constraints}\n\n"
                    f"TASK: produce exactly ONE replacement direction with frame=\"{vetoed.frame}\" "
                    f"that strictly respects every hard constraint above. "
                    f"Output ONLY JSON: {{\"directions\": [{{\"frame\":..., \"name\":..., \"concept\":..., "
                    f"\"rationale\":..., \"risks\":[]}}]}}")
            raw = llm.chat(system="", user=user, max_tokens=8192)
            payload = creator_mod._parse_json(raw)
            d = payload["directions"][0]
            rep = Direction(**{**d, "frame": vetoed.frame,
                               "risks": d.get("risks", [])})
            rec.tool_response(agent, "llm_retry", f"replacement: {rep.name}")
            return rep
        except Exception as exc:
            rec.retry(agent, "replacement_call", f"replacement LLM failed ({exc}); heuristic")
    return Direction(frame=vetoed.frame, name=f"{vetoed.frame.capitalize()} replacement",
                     concept=f"Constraint-respecting redo of «{brief.title}» through the "
                             f"{vetoed.frame} frame.",
                     rationale="Regenerated after veto; must respect all hard constraints.",
                     risks=[])


# --- aggregation / reporting --------------------------------------------------
def analyse_edge_case(rows: dict[str, dict]) -> dict:
    """Data-driven narrative for eval_10_edge_hotel (contradictory brief)."""
    r = rows.get("eval_10_edge_hotel")
    if not r:
        return {"brief": "eval_10_edge_hotel", "error": "not run"}
    adv, base = r["advanced"], r["baseline"]
    probe_v = next((v for v in adv["verdicts"]
                    if v["direction_id"] == f"{DRIFT_PROBES['eval_10_edge_hotel']['frame']}:"
                                            f"{DRIFT_PROBES['eval_10_edge_hotel']['name']}"), None)
    rel_comment = (probe_v or {}).get("comments", {}).get("relevance", "")
    tot_comment = (probe_v or {}).get("comments", {}).get("quality", "")
    return {
        "brief": "eval_10_edge_hotel",
        "why_hard": "Brief is intentionally self-contradictory: full digital detox AND push "
                    "notifications, livestreams, voice assistants and work e-mail at once; "
                    "audience is both detoxers and influencers. A 'solution' that satisfies "
                    "everything is logically impossible.",
        "baseline": {
            "mean_score": base["mean_score"],
            "probe_total": base["probe_total"],
            "drift_caught": base["drift_caught"],
        },
        "advanced": {
            "mean_score": adv["mean_score"],
            "probe_total": adv["probe_total"],
            "drift_caught": adv["drift_caught"],
            "probe_relevance_comment": rel_comment,
            "probe_quality_comment": tot_comment,
            "vetoes": adv["vetoes"],
        },
        "finding": (
            f"Heuristic one-shot judge scored the contradiction-absorbing probe "
            f"{base['probe_total']}/100 (caught={base['drift_caught']}) because lexical overlap "
            f"is blind to logical conflict; the LLM rubric judge scored it {adv['probe_total']}/100 "
            f"(caught={adv['drift_caught']}) and named the contradiction, triggering the veto/retry "
            f"loop. Judge discrimination (score spread) on this brief: baseline "
            f"{base['score_spread']} vs advanced {adv['score_spread']}."
        ),
    }


CSV_COLS = [
    "brief_id", "title", "baseline_mean_score", "advanced_mean_score",
    "baseline_probe_total", "advanced_probe_total",
    "baseline_drift_caught", "advanced_drift_caught",
    "baseline_human_min", "advanced_human_min",
    "baseline_wall_s", "advanced_wall_s",
    "advanced_llm_calls", "advanced_total_tokens", "advanced_cost_usd",
    "advanced_vetoes", "advanced_replacements",
]


def write_outputs(rows: dict[str, dict], meta: dict) -> tuple[Path, Path]:
    order = sorted(rows.keys())
    n = len(order)
    base_catch = sum(1 for k in order if rows[k]["baseline"]["drift_caught"])
    adv_catch = sum(1 for k in order if rows[k]["advanced"]["drift_caught"])
    bm = [rows[k]["baseline"]["mean_score"] for k in order if rows[k]["baseline"]["mean_score"] is not None]
    am = [rows[k]["advanced"]["mean_score"] for k in order if rows[k]["advanced"]["mean_score"] is not None]
    human_saved = sum(rows[k]["baseline"]["human_time_min"] - rows[k]["advanced"]["human_time_min"]
                      for k in order)
    tot_tokens = sum(rows[k]["advanced"]["total_tokens"] for k in order)
    tot_cost = round(sum(rows[k]["advanced"]["cost_usd"] for k in order), 5)

    summary = {
        "n_briefs": n,
        "drift_catch_rate_baseline": round(base_catch / n, 3) if n else None,
        "drift_catch_rate_advanced": round(adv_catch / n, 3) if n else None,
        "drift_caught_counts": {"baseline": base_catch, "advanced": adv_catch},
        "mean_verdict_score_baseline": round(statistics.mean(bm), 1) if bm else None,
        "mean_verdict_score_advanced": round(statistics.mean(am), 1) if am else None,
        "human_time_min_baseline_total": round(sum(rows[k]["baseline"]["human_time_min"] for k in order), 1),
        "human_time_min_advanced_total": round(sum(rows[k]["advanced"]["human_time_min"] for k in order), 1),
        "human_time_min_saved_total": round(human_saved, 1),
        "advanced_wall_clock_total_s": round(sum(rows[k]["advanced"]["wall_clock_s"] for k in order), 1),
        "advanced_llm_calls_total": sum(rows[k]["advanced"]["llm_calls"] for k in order),
        "advanced_total_tokens": tot_tokens,
        "advanced_cost_usd_total": tot_cost,
        "advanced_cost_usd_per_task": round(tot_cost / n, 5) if n else None,
        "vetoes_total": sum(rows[k]["advanced"]["vetoes"] for k in order),
        "replacements_total": sum(rows[k]["advanced"]["replacements"] for k in order),
        "mean_probe_total_baseline": round(statistics.mean(
            [rows[k]["baseline"]["probe_total"] for k in order]), 1),
        "mean_probe_total_advanced": round(statistics.mean(
            [rows[k]["advanced"]["probe_total"] for k in order]), 1),
    }
    meta["interpretation_notes"] = [
        "Drift-catch rate is the primary, apples-to-apples metric: the SAME constraint-"
        "violating drift probe (identical text, saturated with brief keywords) is judged by "
        "both systems on every brief; catch = probe rejected (total < threshold) or vetoed.",
        "Mean verdict scores are NOT cross-condition comparable as a quality scale: baseline "
        "scores come from the lenient lexical heuristic and advanced from the strict LLM "
        "rubric. Within-condition signal is the discrimination (score_spread, max-min verdict "
        f"total): the heuristic cluster is a constant {min(rows[k]['baseline']['score_spread'] for k in order):.1f} "
        f"pts on every brief, the LLM judge {min(rows[k]['advanced']['score_spread'] for k in order):.1f}-"
        f"{max(rows[k]['advanced']['score_spread'] for k in order):.1f} pts.",
        "human_time_min is a MODELLED proxy (constants in run_benchmark.py), not measured; "
        "wall_clock_s and token/cost figures ARE measured (real API usage incl. usage.cost).",
        "advanced llm_calls include retries of the reasoning model's empty-content answers.",
    ]

    report = {
        "meta": meta,
        "summary": summary,
        "per_brief": {k: rows[k] for k in order},
        "challenging_case": analyse_edge_case(rows),
    }
    jp = RESULTS_DIR / "final_report.json"
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    cp = RESULTS_DIR / "final_report.csv"
    with cp.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLS + ["mean_score_delta"])
        for k in order:
            b, a = rows[k]["baseline"], rows[k]["advanced"]
            w.writerow([
                k, rows[k]["title"][:60],
                b["mean_score"], a["mean_score"],
                b["probe_total"], a["probe_total"],
                b["drift_caught"], a["drift_caught"],
                b["human_time_min"], a["human_time_min"],
                b["wall_clock_s"], a["wall_clock_s"],
                a["llm_calls"], a["total_tokens"], a["cost_usd"],
                a["vetoes"], a["replacements"],
                round((a["mean_score"] or 0) - (b["mean_score"] or 0), 1),
            ])
        w.writerow([])
        w.writerow(["TOTAL/AVG", f"{n} briefs",
                    summary["mean_verdict_score_baseline"], summary["mean_verdict_score_advanced"],
                    "", "", summary["drift_catch_rate_baseline"], summary["drift_catch_rate_advanced"],
                    summary["human_time_min_baseline_total"], summary["human_time_min_advanced_total"],
                    "", summary["advanced_wall_clock_total_s"],
                    summary["advanced_llm_calls_total"], tot_tokens, tot_cost,
                    summary["vetoes_total"], summary["replacements_total"], ""])
    return jp, cp


def main() -> int:
    ap = argparse.ArgumentParser(description="Creator Court measured-improvement benchmark")
    ap.add_argument("--limit", type=int, default=0, help="run only first N briefs (smoke)")
    ap.add_argument("--only", type=str, default="", help="comma-separated brief ids to run")
    ap.add_argument("--no-llm", action="store_true",
                    help="force heuristic mode everywhere (CI/offline)")
    ap.add_argument("--fresh", action="store_true",
                    help="wipe previous results before running")
    args = ap.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    PER_BRIEF_DIR.mkdir(parents=True, exist_ok=True)

    brief_files = sorted(BRIEFS_DIR.glob("eval_*.json"))
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        brief_files = [f for f in brief_files if f.stem in wanted]
    if args.limit:
        brief_files = brief_files[: args.limit]
    if not brief_files:
        print("no briefs found", file=sys.stderr)
        return 2

    if args.fresh:
        # scope the wipe to the briefs actually selected for this run
        selected = {bf.stem for bf in brief_files}
        for f in (list(TRACES_DIR.glob("bench_*.jsonl"))
                  + list(PER_BRIEF_DIR.glob("*.json"))):
            stem = f.stem
            bid = stem[len("bench_"):] if stem.startswith("bench_") else stem
            if any(bid == s or bid == s + "_baseline" or bid == s + "_advanced"
                   for s in selected):
                f.unlink(missing_ok=True)

    llm = LLMClient()
    meta = {
        "benchmark": "creator-court-measured-improvement-v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version.split()[0],
        "model": "heuristic-only" if args.no_llm or not llm.available else MeteredLLM().model,
        "llm_key_present": llm.available and not args.no_llm,
        "threshold": REJECT_THRESHOLD,
        "human_time_proxy": {
            "note": "MODELLED minutes from constants in run_benchmark.py, not measured",
            "baseline_formula": "read_brief + write_direction*6 + score_direction*7",
            "advanced_formula": "review_verdict*V + veto*vetoes + retry_check*replacements + sign_off",
        },
    }

    rows: dict[str, dict] = {}
    for i, bf in enumerate(brief_files, 1):
        bid = bf.stem
        brief = load_brief(bf)
        cache = PER_BRIEF_DIR / f"{bid}.json"
        if cache.exists() and not args.fresh:
            rows[bid] = json.loads(cache.read_text(encoding="utf-8"))
            print(f"[{i}/{len(brief_files)}] {bid} (cached)")
            continue
        t0 = time.time()
        base = run_baseline(brief, bid, args.no_llm)
        adv = run_advanced(brief, bid, args.no_llm)
        row = {"title": brief.title, "constraints": brief.constraints,
               "baseline": base, "advanced": adv}
        rows[bid] = row
        cache.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{i}/{len(brief_files)}] {bid}: base mean={base['mean_score']} "
              f"catch={base['drift_caught']} probe={base['probe_total']} | "
              f"adv mean={adv['mean_score']} catch={adv['drift_caught']} probe={adv['probe_total']} "
              f"calls={adv['llm_calls']} ${adv['cost_usd']:.4f} | "
              f"wall adv={adv['wall_clock_s']}s ({time.time() - t0:.0f}s)", flush=True)

    # Never let a partial run clobber the full table: merge any cached briefs
    # that were not part of this run (fresh results win).
    for cf in PER_BRIEF_DIR.glob("*.json"):
        if cf.stem not in rows:
            try:
                rows[cf.stem] = json.loads(cf.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

    jp, cp = write_outputs(rows, meta)
    rep = json.loads(jp.read_text(encoding="utf-8"))
    print("\n=== SUMMARY ===")
    print(json.dumps(rep["summary"], indent=2))
    print(f"\nreport: {jp}\ncsv:    {cp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
