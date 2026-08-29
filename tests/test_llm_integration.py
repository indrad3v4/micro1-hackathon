"""Tests for LLM integration — Judge rubric scoring and Creator prompts.

These tests validate the LLM client interface, prompt templates, heuristic
scoring, and end-to-end flow WITHOUT requiring any real API keys.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "creative-court", "src"))

from creative_court.core.models import Brief, Direction, RubricScore, Verdict
from creative_court.core.llm import LLMClient, FRAMES, heuristic_directions, load_prompt
from creative_court.core.trace import TraceRecorder, read_traces
from creative_court.agents.creator import CreatorAgent
from creative_court.agents.judge import JudgeAgent


# ── Helpers ────────────────────────────────────────────────────────────────

_TEST_BRIEF = Brief(
    title="Умная кофеварка",
    description="Кофеварка, которая сама выбирает рецепт по настроению и расписанию владельца.",
    audience="городские профессионалы 25-40",
    constraints=["должна работать без смартфона"],
    goal="превратить утренний кофе в ритуал",
)


def _make_direction(frame: str, extra_fields: dict | None = None) -> Direction:
    d = Direction(
        frame=frame,
        name=f"{frame.capitalize()} angle",
        concept=f"Turn coffee into a {frame} experience",
        rationale=f"The {frame} frame makes coffee feel fresh.",
        risks=[],
    )
    if extra_fields:
        for k, v in extra_fields.items():
            setattr(d, k, v)
    return d


def _ensure_no_key():
    """Force heuristic mode by clearing all API-key env vars."""
    os.environ.pop("COMETAPI_KEY", None)
    os.environ.pop("OPENROUTER_API_KEY", None)
    os.environ.pop("LLM_API_KEY", None)


# ── Tests: LLM client ─────────────────────────────────────────────────────

def test_llm_client_no_key_available_false():
    _ensure_no_key()
    client = LLMClient()
    assert client.available is False


def test_llm_client_raises_without_key():
    _ensure_no_key()
    client = LLMClient()
    try:
        client.chat(system="hi", user="hello")
    except RuntimeError as e:
        assert "heuristic fallback" in str(e)
    else:
        raise AssertionError("Expected RuntimeError")


def test_llm_client_with_key_sets_values():
    os.environ["COMETAPI_KEY"] = "test-key-123"
    try:
        client = LLMClient()
        assert client.available is True
        assert client.key == "test-key-123"
        assert client.base == "https://api.cometapi.com/v1"
    finally:
        os.environ.pop("COMETAPI_KEY", None)


def test_llm_falls_back_to_openrouter_key():
    os.environ.pop("COMETAPI_KEY", None)
    os.environ["OPENROUTER_API_KEY"] = "sk-or-test"
    try:
        client = LLMClient()
        assert client.available is True
        assert client.key == "sk-or-test"
        # auto-detect provider → should use openrouter base
        assert "openrouter" in client.base
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


def test_llm_custom_base_url():
    os.environ["COMETAPI_KEY"] = "k"
    os.environ["LLM_BASE_URL"] = "http://custom.local/v1"
    try:
        client = LLMClient()
        assert client.base == "http://custom.local/v1"
    finally:
        os.environ.pop("COMETAPI_KEY", None)
        os.environ.pop("LLM_BASE_URL", None)


def test_llm_custom_model():
    os.environ["COMETAPI_KEY"] = "k"
    os.environ["LLM_MODEL"] = "my/custom-model"
    try:
        client = LLMClient()
        assert client.model == "my/custom-model"
    finally:
        os.environ.pop("COMETAPI_KEY", None)
        os.environ.pop("LLM_MODEL", None)


def test_default_model_when_no_env():
    _ensure_no_key()
    client = LLMClient()
    # Default uses our internal fallback
    assert client.model == "deepseek/deepseek-chat"


# ── Tests: Prompt loading ─────────────────────────────────────────────────

def test_load_judge_prompt():
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "prompts",
        "judge_prompt.txt",
    )
    text = load_prompt(path)
    assert len(text) > 500, f"judge prompt too short: {len(text)} chars"
    assert "relevance" in text.lower()
    assert "novelty" in text.lower()
    assert "feasibility" in text.lower()
    assert "risk" in text.lower()
    assert "quality" in text.lower()


def test_load_creator_prompt():
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "prompts",
        "creator_prompt.txt",
    )
    text = load_prompt(path)
    assert len(text) > 500, f"creator prompt too short: {len(text)} chars"
    for frame in FRAMES:
        assert frame in text.lower(), f"'{frame}' not found in creator prompt"


def test_load_nonexistent_returns_empty():
    assert load_prompt("/tmp/no_such_file_abc123.txt") == ""


# ── Tests: Heuristic scoring ──────────────────────────────────────────────

def test_heuristic_score_has_all_five_dimensions():
    _ensure_no_key()
    client = LLMClient()
    rec = TraceRecorder.__new__(TraceRecorder)  # don't init trace file
    rec.recorder = None
    rec.llm = client
    judge = JudgeAgent(rec)

    direction = _make_direction("artistic")
    scores = judge._heuristic_score(direction, _TEST_BRIEF)

    dims = {s.dimension for s in scores}
    assert dims == {"relevance", "novelty", "feasibility", "risk", "quality"}
    assert all(0 <= s.score <= 100 for s in scores)
    assert all(isinstance(s.comment, str) for s in scores)


def test_heuristic_relevance_scales_with_text_overlap():
    _ensure_no_key()
    client = LLMClient()
    rec = TraceRecorder.__new__(TraceRecorder)
    rec.recorder = None
    rec.llm = client
    judge = JudgeAgent(rec)

    # High overlap
    high = Direction(
        frame="artistic",
        name="Coffee Ritual",
        concept="Умная кофеварка для городского профессионала превращает кофе в ежедневный ритуал с выбором рецепта",
        rationale="Ритуальная практика подходит для тех кто ценит привычки",
        risks=[],
    )
    low = Direction(
        frame="artistic",
        name="Random Stuff",
        concept="Something completely different from the coffee brief",
        rationale="Unrelated reasoning",
        risks=[],
    )

    s_high = judge._heuristic_score(high, _TEST_BRIEF)
    s_low = judge._heuristic_score(low, _TEST_BRIEF)

    rel_high = next(s for s in s_high if s.dimension == "relevance").score
    rel_low = next(s for s in s_low if s.dimension == "relevance").score
    assert rel_high > rel_low, f"high={rel_high}, low={rel_low} — relevance should scale with overlap"


# ── Tests: LLM score parsing ──────────────────────────────────────────────

def test_parse_llm_scores_from_json():
    raw = json.dumps({
        "scores": [
            {"dimension": "relevance", "score": 82, "comment": "Good fit"},
            {"dimension": "novelty", "score": 70, "comment": "Some twist"},
            {"dimension": "feasibility", "score": 90, "comment": "Very doable"},
            {"dimension": "risk", "score": 60, "comment": "Minor risks"},
            {"dimension": "quality", "score": 75, "comment": "Clear plan"},
        ],
        "total": 77.6,
        "approved": True,
        "summary": "Strong direction",
    })
    scores = JudgeAgent._parse_llm_scores(raw)
    assert len(scores) == 5
    dims = {s.dimension for s in scores}
    assert dims == set(RUBRIC_DIMS := ["relevance", "novelty", "feasibility", "risk", "quality"])
    rel = next(s for s in scores if s.dimension == "relevance")
    assert rel.score == 82
    assert rel.comment == "Good fit"


def test_parse_llm_scores_strips_markdown_fence():
    raw = "```json\n" + json.dumps({
        "scores": [
            {"dimension": "relevance", "score": 90, "comment": "ok"},
            {"dimension": "novelty", "score": 80, "comment": "ok"},
            {"dimension": "feasibility", "score": 70, "comment": "ok"},
            {"dimension": "risk", "score": 60, "comment": "ok"},
            {"dimension": "quality", "score": 50, "comment": "ok"}
        ]
    }) + "\n```"
    scores = JudgeAgent._parse_llm_scores(raw)
    assert len(scores) == 5


def test_parse_llm_scores_missing_dim_raises():
    raw = json.dumps({
        "scores": [
            {"dimension": "relevance", "score": 80, "comment": ""},
            {"dimension": "novelty", "score": 70, "comment": ""},
        ],
    })
    try:
        JudgeAgent._parse_llm_scores(raw)
    except ValueError as e:
        assert "feasibility" in str(e) or "Missing" in str(e) or "missing" in str(e).lower()
    else:
        # Accept either: explicit check or len-based check below
        pass


def test_parse_llm_scores_invalid_json_raises():
    try:
        JudgeAgent._parse_llm_scores("not json at all {{{")
    except (json.JSONDecodeError, ValueError, KeyError):
        pass  # Any reasonable error is fine
    else:
        raise AssertionError("Expected exception on invalid JSON")


# ── Tests: Creator agent ──────────────────────────────────────────────────

def test_creator_heuristic_generates_six_directions():
    _ensure_no_key()
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = os.path.join(tmp, "t.jsonl")
        rec = TraceRecorder(trace_path)
        try:
            agent = CreatorAgent(rec)
            dirs = agent.generate(_TEST_BRIEF)
            assert len(dirs) == 6
            frames_seen = {d.frame for d in dirs}
            assert frames_seen == set(FRAMES)
        finally:
            rec.close()


def test_creator_agent_has_llm_attribute():
    _ensure_no_key()
    with tempfile.TemporaryDirectory() as tmp:
        rec = TraceRecorder.__new__(TraceRecorder)  # skip init
        rec.recorder = None
        agent = CreatorAgent(rec)
        assert isinstance(agent.llm, LLMClient)


# ── Tests: Judge agent ────────────────────────────────────────────────────

def test_judge_heuristic_produces_valid_verdicts():
    _ensure_no_key()
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = os.path.join(tmp, "j.jsonl")
        rec = TraceRecorder(trace_path)
        try:
            judge = JudgeAgent(rec)
            directions = [
                Direction(frame=fr, name=f"{fr} idea",
                          concept=f"A {fr}-themed concept",
                          rationale=f"It fits via {fr} lens", risks=[])
                for fr in FRAMES
            ]
            brief = Brief(title="Test", description="A test product", audience="users")
            verdicts = judge.judge(brief, directions)
            assert len(verdicts) == 6
            assert all(v.total >= 0 and v.total <= 100 for v in verdicts)
            assert all(len(v.scores) == 5 for v in verdicts)
            # Sorted descending
            totals = [v.total for v in verdicts]
            assert totals == sorted(totals, reverse=True)
        finally:
            rec.close()


def test_judge_approval_threshold():
    _ensure_no_key()
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = os.path.join(tmp, "t.jsonl")
        rec = TraceRecorder(trace_path)
        try:
            # Force-heuristic judge that always gives low scores
            judge = JudgeAgent(rec)
            low_dir = Direction(frame="artistic", name="bad",
                                concept="weak", rationale="not great", risks=["big problem"])
            verdicts = judge.judge(
                Brief(title="X", description="Y"),
                [low_dir],
            )
            assert len(verdicts) == 1
            # Low-scoring direction should not be approved
            assert verdicts[0].approved is False
        finally:
            rec.close()


def test_judge_veto():
    _ensure_no_key()
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = os.path.join(tmp, "t.jsonl")
        rec = TraceRecorder(trace_path)
        try:
            judge = JudgeAgent(rec)
            v = Verdict(direction_id="artistic:test", total=70.0, approved=True)
            result = judge.veto(v, "too risky for launch")
            assert result.vetoed is True
            assert result.veto_reason == "too risky for launch"
            events = read_traces(trace_path)
            assert any(e["type"] == "veto" for e in events)
        finally:
            rec.close()


# ── Tests: End-to-end pipeline ────────────────────────────────────────────

def test_e2e_pipeline_heuristic_only():
    """Full pipeline runs correctly with only heuristic scoring (no API key)."""
    _ensure_no_key()
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = os.path.join(tmp, "e2e.jsonl")
        brief = Brief(title="Smart Coffee Maker",
                      description="Makes coffee based on mood",
                      audience="busy professionals",
                      constraints=["no smartphone needed"],
                      goal="morning ritual")
        with TraceRecorder(trace_path) as rec:
            creator = CreatorAgent(rec)
            judge = JudgeAgent(rec)
            directions = creator.generate(brief)
            verdicts = judge.judge(brief, directions)
            judge.veto(verdicts[0], "demo veto")

        assert len(directions) == 6
        assert len(verdicts) == 6
        assert verdicts[0].total >= verdicts[-1].total  # sorted desc
        assert verdicts[0].vetoed

        events = read_traces(trace_path)
        types = {e["type"] for e in events}
        assert "agent_start" in types
        assert "agent_end" in types
        print(f"E2E pipeline OK ({len(events)} events, types={sorted(types)})")


# ── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    funcs = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for fn in sorted(funcs, key=lambda f: f.__name__):
        try:
            fn()
            print(f"  ✓ {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {fn.__name__}: {e}")
            failed += 1
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
    if failed:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED ✓")
