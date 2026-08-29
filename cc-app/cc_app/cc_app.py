"""Creative Court 2.0 - Black Box Unveiled Dashboard.

A Reflex-based interactive frontend for the Creative Court pipeline.
Shows brief input (left panel), generated directions with scores in the Arena
(center panel), and a real-time trace log feed (right panel).

Uses static indexing for direction cards (max 6 frames) to avoid Reflex 0.9
foreach type-system constraints on List[Dict[str,Any]].
"""

import io
import json
import os
import tempfile
import traceback
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import reflex as rx

# ---------------------------------------------------------------------------
# Import creative-court agent modules (copied into this package)
# ---------------------------------------------------------------------------

_CC_TRACES = os.path.join(os.path.dirname(__file__), "..", "traces")

from .creative_court.core.models import Brief, Direction, RubricScore, Verdict
from .creative_court.core.trace import TraceRecorder
from .creative_court.agents.creator import CreatorAgent
from .creative_court.agents.judge import JudgeAgent, RUBRICS

# ---------------------------------------------------------------------------
# App State
# ---------------------------------------------------------------------------


class CCState(rx.State):
    """Main state for the Creative Court dashboard."""

    # -- Brief fields --
    title: str = ""
    description: str = ""
    audience: str = ""
    constraints_raw: str = ""
    creativity: float = 0.5

    # -- Results (up to 6 IKRA frames) --
    direction_0_frame: str = ""
    direction_0_name: str = ""
    direction_0_concept: str = ""
    direction_0_rationale: str = ""
    direction_0_risks: List[str] = []
    direction_0_score: float = 0.0
    direction_0_approved: bool = False
    direction_0_summary: str = ""
    direction_0_veto_frame: str = ""
    direction_0_risks_display: str = ""

    direction_1_frame: str = ""
    direction_1_name: str = ""
    direction_1_concept: str = ""
    direction_1_rationale: str = ""
    direction_1_risks: List[str] = []
    direction_1_score: float = 0.0
    direction_1_approved: bool = False
    direction_1_summary: str = ""
    direction_1_veto_frame: str = ""
    direction_1_risks_display: str = ""

    direction_2_frame: str = ""
    direction_2_name: str = ""
    direction_2_concept: str = ""
    direction_2_rationale: str = ""
    direction_2_risks: List[str] = []
    direction_2_score: float = 0.0
    direction_2_approved: bool = False
    direction_2_summary: str = ""
    direction_2_veto_frame: str = ""
    direction_2_risks_display: str = ""

    direction_3_frame: str = ""
    direction_3_name: str = ""
    direction_3_concept: str = ""
    direction_3_rationale: str = ""
    direction_3_risks: List[str] = []
    direction_3_score: float = 0.0
    direction_3_approved: bool = False
    direction_3_summary: str = ""
    direction_3_veto_frame: str = ""
    direction_3_risks_display: str = ""

    direction_4_frame: str = ""
    direction_4_name: str = ""
    direction_4_concept: str = ""
    direction_4_rationale: str = ""
    direction_4_risks: List[str] = []
    direction_4_score: float = 0.0
    direction_4_approved: bool = False
    direction_4_summary: str = ""
    direction_4_veto_frame: str = ""
    direction_4_risks_display: str = ""

    direction_5_frame: str = ""
    direction_5_name: str = ""
    direction_5_concept: str = ""
    direction_5_rationale: str = ""
    direction_5_risks: List[str] = []
    direction_5_score: float = 0.0
    direction_5_approved: bool = False
    direction_5_summary: str = ""
    direction_5_veto_frame: str = ""
    direction_5_risks_display: str = ""
    direction_5_risks_display: str = ""

    num_directions: int = 0
    verdicts: List[Dict[str, Any]] = []
    all_approved: bool = False

    # -- Orchestration flags --
    is_running: bool = False
    max_retries: int = 3
    retry_count: int = 0
    retry_needed: bool = False

    # -- Trace log (full data for export) --
    trace_log: List[Dict[str, Any]] = []

    # -- Trace display lines (plain strings for reliable UI rendering) --
    # Pre-populated with 100 empty strings so bracket-indexing never fails at compile time
    _trace_lines: List[str] = [""] * 100

    trace_path: Optional[str] = None

    # --- Explicit setters (auto-setters disabled in Reflex 0.9) ---
    def set_title(self, title: str) -> None:
        self.title = title

    def set_description(self, description: str) -> None:
        self.description = description

    def set_audience(self, audience: str) -> None:
        self.audience = audience

    def set_constraints_raw(self, constraints_raw: str) -> None:
        self.constraints_raw = constraints_raw

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    def _log_event(self, ev: Dict[str, Any]) -> None:
        """Append event to both full trace_log and plain-text _trace_lines."""
        self.trace_log.append(ev)
        if len(self.trace_log) > 500:
            self.trace_log = self.trace_log[-500:]
        # Also maintain a plain-string list for reliable UI rendering
        agent_str = str(ev.get("agent", "?"))
        action_str = str(ev.get("action", ""))
        line = f"[{ev.get('ts', '')}] {agent_str}: {action_str}"
        # Write into pre-allocated slots, rotating through them
        slot_idx = len(self.trace_log) % 100
        if hasattr(self, "_trace_lines") and slot_idx < len(self._trace_lines):
            self._trace_lines[slot_idx] = line

    def _build_brief(self) -> Brief:
        constraints = [c.strip() for c in self.constraints_raw.split("\n")
                       if c.strip()]
        return Brief(title=self.title, description=self.description,
                     audience=self.audience, constraints=constraints, goal="")

    def _set_direction(self, idx: int, direction: Direction,
                       verdict: Optional[Verdict]) -> None:
        """Set direction fields for a given index (0-5)."""
        v_score = verdict.total if verdict else 0
        v_approved = verdict.approved if verdict else False
        v_summary = verdict.summary if verdict else "Pending"
        prefix = f"direction_{idx}"
        setattr(self, f"{prefix}_frame", direction.frame)
        setattr(self, f"{prefix}_name", direction.name)
        setattr(self, f"{prefix}_concept", direction.concept)
        setattr(self, f"{prefix}_rationale", direction.rationale)
        setattr(self, f"{prefix}_risks", direction.risks)
        # Store risks as a plain text line for UI display (avoids List indexing at compile time)
        setattr(self, f"{prefix}_risks_display",
                "; ".join(direction.risks) if direction.risks else "")
        setattr(self, f"{prefix}_score", v_score)
        setattr(self, f"{prefix}_approved", v_approved)
        setattr(self, f"{prefix}_summary", v_summary)
        setattr(self, f"{prefix}_veto_frame", direction.frame)

    # --- Orchestration handler ---

    def handle_submit(self) -> rx.event.EventSpec:
        """Run the full Creative Court pipeline."""
        if not self.title.strip():
            self._log_event({"ts": self._now(), "agent": "ui", "type": "error",
                             "action": "Missing brief title"})
            return rx.stop_propagation

        self.is_running = True
        self.retry_count = 0
        self.all_approved = False
        # Clear all direction fields
        for i in range(6):
            for attr in ["_frame", "_name", "_concept", "_rationale",
                         "_risks", "_risks_display", "_score", "_approved", "_summary", "_veto_frame"]:
                setattr(self, f"direction_{i}{attr}", "")

        run_dir = os.path.join(_CC_TRACES, "traces")
        os.makedirs(run_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.trace_path = os.path.join(run_dir, f"dashboard_{ts}.jsonl")
        recorder = TraceRecorder(self.trace_path, meta={
            "title": self.title, "description": self.description})
        brief = self._build_brief()

        self._log_event({"ts": self._now(), "agent": "harness",
                         "type": "agent_start",
                         "instruction": f"Creative Court: {self.title}"})
        recorder.event(agent="harness", type="agent_start",
                        instruction=f"Dashboard initiated: {self.title}")

        try:
            self._log_event({"ts": self._now(), "agent": "harness",
                             "type": "pipeline_step",
                             "action": "Initializing agents..."})
            creator = CreatorAgent(recorder=recorder, llm=None)
            judge = JudgeAgent(recorder=recorder, llm=None)

            while not self.all_approved and self.retry_count < self.max_retries:
                brief = self._build_brief()
                self._log_event({"ts": self._now(), "agent": "creator",
                                 "type": "agent_start",
                                 "instruction": f"Generate for: {self.title}"})
                directions = creator.generate(brief)
                self.num_directions = len(directions)
                for i, d in enumerate(directions):
                    self._set_direction(i, d, None)

                self._log_event({"ts": self._now(), "agent": "creator",
                                 "type": "agent_end",
                                 "action": f"Produced {len(directions)} dirs"})
                self._log_event({"ts": self._now(), "agent": "judge",
                                 "type": "agent_start",
                                 "instruction": f"Judge {len(directions)} directions"})
                verdicts = judge.judge(brief, directions)
                approved_count = 0
                for i, (d, v) in enumerate(zip(directions, verdicts)):
                    self._set_direction(i, d, v)
                    if v.approved:
                        approved_count += 1
                    else:
                        self._log_event({"ts": self._now(), "agent": "judge",
                                         "type": "agent_step",
                                         "action": f"verdict: {v.direction_id}",
                                         "feedback": v.summary})
                self._log_event({"ts": self._now(), "agent": "judge",
                                 "type": "agent_end",
                                 "action": f"Scored {len(verdicts)}"
                                           f" - {approved_count}/{len(verdicts)} ok"})

                if approved_count == len(verdicts):
                    self.all_approved = True
                    self._log_event({"ts": self._now(), "agent": "harness",
                                     "type": "pipeline_complete",
                                     "action": "All directions approved!",
                                     "data": {"total_iterations": self.retry_count + 1}})
                else:
                    self.retry_count += 1
                    self.retry_needed = True
                    self._log_event({"ts": self._now(), "agent": "harness",
                                     "type": "retry_cycle",
                                     "action": (f"{len(verdicts) - approved_count} need"
                                                f" rework (attempt {self.retry_count})")})

        except Exception as exc:
            self._log_event({"ts": self._now(), "agent": "error",
                             "type": "error", "action": str(exc)})
            self._log_event({"ts": self._now(), "agent": "error",
                             "type": "error_detail",
                             "action": traceback.format_exc()[:2000]})
        finally:
            recorder.close()
            self.is_running = False

        return rx.stop_propagation

    # --- Veto handler ---

    def handle_veto(self, frame_name: str, reason: str = "") -> rx.event.EventSpec:
        """Veto a direction by frame name and regenerate it."""
        if not self.title.strip():
            return rx.stop_propagation
        self.retry_needed = True
        self._log_event({"ts": self._now(), "agent": "human", "type": "veto",
                         "action": f"Vetoed: {frame_name}",
                         "feedback": reason or "Rejected during review"})
        brief = self._build_brief()
        parent_dir = os.path.dirname(
            self.trace_path or os.path.join(_CC_TRACES, "traces"))
        veto_path = os.path.join(parent_dir,
                                 f"veto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
        new_rec = TraceRecorder(veto_path, meta={"veto_frame": frame_name})
        creator = CreatorAgent(recorder=new_rec, llm=None)
        judge = JudgeAgent(recorder=new_rec, llm=None)
        directions = creator.generate(brief)
        target_idx = None
        for i, d in enumerate(directions):
            if d.frame == frame_name:
                d.concept = f"[REWORKED per veto] {d.concept} - Address concerns."
                new_rec.event(agent="creator", type="retry",
                              retry_of=f"{frame_name}:{d.name}",
                              feedback=reason or "Rejected")
                target_idx = i
                break
        verdicts = judge.judge(brief, directions)
        if target_idx is not None and target_idx < len(directions):
            self._set_direction(target_idx, directions[target_idx],
                                verdicts[target_idx])
        self._log_event({"ts": self._now(), "agent": "judge",
                         "type": "agent_step",
                         "action": f"Re-scored after veto: {frame_name}"})
        new_rec.close()
        return rx.stop_propagation

    # --- Export handler ---

    def handle_export(self) -> rx.download:
        """Download traces and results as a ZIP artifact."""
        trace_files = []
        trace_dir = os.path.join(_CC_TRACES, "traces")
        if os.path.exists(trace_dir):
            for fn in sorted(os.listdir(trace_dir)):
                if fn.endswith(".jsonl"):
                    trace_files.append(os.path.join(trace_dir, fn))

        export_data = {
            "app": "Creative Court 2.0 - Dashboard Export",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "brief": {"title": self.title, "description": self.description,
                      "audience": self.audience,
                      "constraints": self.constraints_raw,
                      "creativity_level": self.creativity},
            "results": {"num_directions": self.num_directions,
                        "all_approved": self.all_approved,
                        "retry_count": self.retry_count,
                        "directions": [
                            {"frame": getattr(self, f"direction_{i}_frame"),
                             "name": getattr(self, f"direction_{i}_name"),
                             "concept": getattr(self, f"direction_{i}_concept"),
                             "rationale": getattr(self, f"direction_{i}_rationale"),
                             "risks": getattr(self, f"direction_{i}_risks"),
                             "score": getattr(self, f"direction_{i}_score"),
                             "approved": getattr(self, f"direction_{i}_approved"),
                             "summary": getattr(self, f"direction_{i}_summary")}
                            for i in range(self.num_directions)],
                        "trace_log": self.trace_log},
        }
        zip_content = io.BytesIO()
        with zipfile.ZipFile(zip_content, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("creative-court-results.json",
                         json.dumps(export_data, indent=2, ensure_ascii=False))
            for tf in trace_files:
                if os.path.exists(tf):
                    zf.write(tf, os.path.basename(tf))
        zip_content.seek(0)
        tmp = tempfile.NamedTemporaryFile(suffix=".zip",
                                          prefix="cc_export_", delete=False)
        tmp.write(zip_content.read())
        tmp.close()
        return rx.download(tmp.name,
                           f"creative-court-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip")


# ---------------------------------------------------------------------------
# UI Color Constants
# ---------------------------------------------------------------------------

DARK_BG = "#0a0a0f"
DARK_SURFACE = "#12121a"
DARK_ELEVATED = "#1a1a2e"
DARK_BORDER = "#2a2a3e"
DARK_TEXT = "#e0e0e8"
DARK_MUTED = "#8888aa"
GREEN_APPROVED = "#2ecc71"
RED_REJECTED = "#e74c3c"
ACCENT_BLUE = "#3498db"
ACCENT_GOLD = "#f39c12"

FRAME_COLORS = {"artistic": "#9b59b6", "social": "#e67e22",
                "professional": "#1abc9c", "historical": "#3498db",
                "ritual": "#f39c12", "natural": "#2ecc71"}


# ---------------------------------------------------------------------------
# LEFT PANEL - Brief Form
# ---------------------------------------------------------------------------


def brief_form() -> rx.Component:
    """LEFT PANEL: Brief input form with controls."""
    return rx.box(
        rx.flex(
            rx.badge("LEFT PANEL", radius="full", size="1",
                     color_scheme="gray", variant="soft", padding_x="0.75rem"),
            justify="end"),
        rx.divider(border_bottom_color=DARK_BORDER),
        rx.form(
            rx.vstack(
                rx.text("Project Title", size="2", color=DARK_MUTED),
                rx.input(placeholder="Enter project title...",
                         value=CCState.title, on_change=CCState.set_title,
                         width="100%", variant="soft", color_scheme="gray",
                         bg=DARK_SURFACE, border_color=DARK_BORDER,
                         color=DARK_TEXT, font_size="sm"),
                rx.text("Description", size="2", color=DARK_MUTED),
                rx.text_area(
                    placeholder="Describe product/service/brief...",
                    value=CCState.description, on_change=CCState.set_description,
                    rows="4", width="100%", variant="soft", color_scheme="gray",
                    bg=DARK_SURFACE, border_color=DARK_BORDER, color=DARK_TEXT,
                    font_family="monospace"),
                rx.text("Target Audience", size="2", color=DARK_MUTED),
                rx.input(placeholder="e.g. millennials, tech fans...",
                         value=CCState.audience, on_change=CCState.set_audience,
                         width="100%", variant="soft", color_scheme="gray",
                         bg=DARK_SURFACE, border_color=DARK_BORDER,
                         color=DARK_TEXT, font_size="sm"),
                rx.text("Constraints (one per line)", size="2", color=DARK_MUTED),
                rx.text_area(
                    placeholder="Budget cap: $10k\nTimeline: 2 weeks\nPlatform: mobile-first",
                    value=CCState.constraints_raw,
                    on_change=CCState.set_constraints_raw, rows="3",
                    width="100%", variant="soft", color_scheme="gray",
                    bg=DARK_SURFACE, border_color=DARK_BORDER, color=DARK_TEXT,
                    font_family="monospace"),
                rx.vstack(
                    rx.flex(rx.text("Creativity Level:", size="2",
                                    color=DARK_MUTED),
                            rx.text(size="2", color=DARK_MUTED),
                            justify="between", width="100%"),
                    rx.slider(default_value=0.5, min=0, max=1, step=0.05,
                              width="100%", accent_color="blue")),
                rx.divider(border_bottom_color=DARK_BORDER),
                rx.cond(
                    CCState.is_running,
                    rx.button("Running Pipeline...", loading=True, width="100%",
                              variant="surface", color_scheme="gray",
                              bg=DARK_ELEVATED, color=DARK_MUTED,
                              cursor="wait"),
                    rx.button("Run Creative Court", width="100%",
                              variant="solid", color_scheme="blue",
                              bg=ACCENT_BLUE, color="#fff",
                              font_weight="bold", size="3")),
                spacing="4", width="100%"),
            on_submit=CCState.handle_submit, width="100%",
            reset_on_submit=False),
        bg=DARK_SURFACE, border=f"1px solid {DARK_BORDER}",
        border_radius="12px", width="100%", height="100%",
        overflow_y="auto", padding="1rem")


# ---------------------------------------------------------------------------
# Arena Card Component (static, indexed by 0-5)
# ---------------------------------------------------------------------------

_FRAME_NAMES = ("Artistic", "Social", "Professional", "Historical", "Ritual",
                "Natural")


def arena_card(idx: int) -> rx.Component:
    """Render one direction card by index (0-5). Uses static field access."""
    prefix = f"direction_{idx}"
    frame = getattr(CCState, f"{prefix}_frame")
    name = getattr(CCState, f"{prefix}_name")
    concept = getattr(CCState, f"{prefix}_concept")
    rationale = getattr(CCState, f"{prefix}_rationale")
    score = getattr(CCState, f"{prefix}_score")
    approved = getattr(CCState, f"{prefix}_approved")
    summary = getattr(CCState, f"{prefix}_summary")
    veto_frame = getattr(CCState, f"{prefix}_veto_frame")
    risks_display = getattr(CCState, f"{prefix}_risks_display")

    badge_color = FRAME_COLORS.get(str(frame) or "", DARK_MUTED)
    status_color = rx.cond(approved == True, GREEN_APPROVED, RED_REJECTED)
    approval_badge = rx.cond(
        approved == True,
        rx.badge("\u2713 Approved", color_scheme="green", radius="full", size="1"),
        rx.badge("\u2717 Rejected", color_scheme="red", radius="full", size="1"))

    card_label = _FRAME_NAMES[idx] if idx < 6 else f"Frame {idx}"

    return rx.card(
        rx.vstack(
            rx.flex(
                rx.badge(card_label, radius="full", padding_x="0.75rem",
                         padding_y="0.25rem", border=f"1px solid {badge_color}",
                         color=badge_color, font_size="xs",
                         font_weight="semibold"),
                rx.spacer(),
                rx.badge(f"{rx.text(score)}/100", radius="full", padding_x="0.75rem",
                         padding_y="0.3rem", border=f"2px solid {status_color}",
                         color=status_color, font_size="sm", font_weight="bold"),
                align_items="center", width="100%"),
            rx.divider(border_bottom_color=DARK_BORDER),
            rx.heading(name, size="3", color=DARK_TEXT),
            rx.text(concept, size="2", color=DARK_TEXT, line_height="1.5"),
            rx.text(rationale, size="1", color=DARK_MUTED, font_style="italic",
                    margin_top="0.25rem", line_height="1.4"),
            rx.cond(risks_display != "",
                    rx.text(risks_display, size="1", color=RED_REJECTED,
                            font_family="monospace", margin_top="0.25rem")),
            rx.divider(border_bottom_color=DARK_BORDER),
            rx.flex(approval_badge, rx.text(summary, size="2", color=DARK_MUTED),
                    align_items="center", gap="0.5rem", width="100%", flex_wrap="wrap"),
            rx.button("Veto & Redo", size="1", variant="outline", color_scheme="red",
                      border=f"1px solid {RED_REJECTED}", color=RED_REJECTED,
                      on_click=CCState.handle_veto(veto_frame, "Rejected via dashboard"),
                      margin_top="0.5rem", width="100%"),
            spacing="3", width="100%"),
        bg=DARK_ELEVATED, border=f"1px solid {DARK_BORDER}",
        border_left=f"4px solid {GREEN_APPROVED}",
        border_radius="8px", padding="0.75rem", width="100%")


# ---------------------------------------------------------------------------
# CENTER PANEL - The Arena
# ---------------------------------------------------------------------------


def arena_panel() -> rx.Component:
    """CENTER PANEL: Arena showing generated directions."""
    return rx.box(
        rx.flex(rx.badge("CENTER PANEL", radius="full", size="1",
                          color_scheme="gray", variant="soft", padding_x="0.75rem"),
                justify="end"),
        rx.divider(border_bottom_color=DARK_BORDER),
        rx.flex(
            rx.heading("The Arena", size="4", color=DARK_TEXT),
            rx.cond(CCState.all_approved,
                    rx.badge("\u2713 All Approved", color_scheme="green",
                             radius="full", size="1"),
                    rx.badge("Awaiting Review", color_scheme="red",
                             radius="full", size="1")),
            rx.spacer(),
            rx.text(f"{CCState.num_directions} directions", size="2",
                    color=DARK_MUTED),
            align_items="center", width="100%"),
        rx.divider(border_bottom_color=DARK_BORDER),
        # Use flex wrap instead of rx.grid (not available in Reflex 0.9)
        rx.flex(*[arena_card(i) for i in range(6)],
                columns="2", gap="1rem", width="100%", wrap="wrap"),
        bg=DARK_SURFACE, border=f"1px solid {DARK_BORDER}",
        border_radius="12px", width="100%", height="100%",
        overflow_y="auto", padding="1rem", spacing="3")


# ---------------------------------------------------------------------------
# RIGHT PANEL - Terminal Trace Log
# ---------------------------------------------------------------------------


def terminal_log() -> rx.Component:
    """RIGHT PANEL: Terminal-style live trace log feed.

    Renders raw _trace_lines (List[str]) via bracket-indexed state vars.
    Fixed-size loop avoids Reflex Var-length compile-time errors.
    """
    # Build 100 slots; each accesses one string from _trace_lines by index
    _trace_components = []
    for i in range(100):
        line_var = CCState._trace_lines[i]
        _trace_components.append(
            rx.text(line_var, size="1", color=DARK_TEXT, font_family="monospace",
                    white_space="nowrap", overflow_x="hidden", text_overflow="ellipsis",
                    padding_y="0.15rem"))

    return rx.box(
        rx.flex(rx.badge("RIGHT PANEL", radius="full", size="1",
                          color_scheme="gray", variant="soft", padding_x="0.75rem"),
                justify="end"),
        rx.divider(border_bottom_color=DARK_BORDER),
        rx.flex(
            rx.heading("Trace Stream", size="4", color=DARK_TEXT),
            rx.spacer(),
            rx.text(f"events queued", size="2", color=DARK_MUTED),
            align_items="center", width="100%"),
        rx.divider(border_bottom_color=DARK_BORDER),
        rx.box(
            rx.vstack(*_trace_components, spacing="0", width="100%",
                      max_height="30rem", overflow_y="auto",
                      padding="0.75rem", font_family="monospace"),
            bg="#0d0d15", border=f"1px solid {DARK_BORDER}",
            border_radius="6px", padding="0", width="100%"),
        rx.divider(border_bottom_color=DARK_BORDER),
        rx.button("Export Trace Artifact", width="100%",
                  variant="outline", color_scheme="gold",
                  border=f"1px solid {ACCENT_GOLD}",
                  color=ACCENT_GOLD, size="2",
                  on_click=CCState.handle_export),
        bg=DARK_SURFACE, border=f"1px solid {DARK_BORDER}",
        border_radius="12px", width="100%", height="100%",
        overflow_y="auto", padding="1rem", spacing="3")


# ---------------------------------------------------------------------------
# Main Dashboard Layout
# ---------------------------------------------------------------------------


def dashboard() -> rx.Component:
    """Three-panel split-screen layout."""
    return rx.container(
        rx.vstack(
            rx.flex(
                rx.heading("Creative Court 2.0", size="5",
                           color=DARK_TEXT, font_weight="bold"),
                rx.text("Black Box Unveiled", size="3",
                        color=DARK_MUTED, font_style="italic"),
                rx.spacer(),
                rx.cond(
                    CCState.is_running,
                    rx.spinner(size="2", color=ACCENT_BLUE),
                    rx.cond(CCState.all_approved,
                            rx.badge("Complete", color_scheme="green",
                                     radius="full", size="1"),
                            rx.badge("Ready", color_scheme="gray",
                                     radius="full", size="1"))),
                align_items="center", width="100%", padding_y="0.75rem"),
            rx.flex(
                brief_form(), arena_panel(), terminal_log(),
                flex_grow="1", min_width="0", gap="1rem",
                width="100%", wrap="wrap"),
            spacing="0", width="100%", height="100vh"),
        background_color=DARK_BG, padding="0")


# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------

app = rx.App()

app.add_page(dashboard, route="/",
             title="Creative Court 2.0 - Black Box Unveiled")
