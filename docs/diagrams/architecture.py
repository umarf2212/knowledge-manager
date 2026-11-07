#!/usr/bin/env python3
"""Render the current architecture with mingrammer/diagrams (authoring only).

Run from any directory: python docs/diagrams/architecture.py
Use --dot-only to emit Graphviz sources without a native dot executable.
"""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

from diagrams import Cluster, Diagram, Edge, Node

INK = "#182B43"
MUTED = "#53677F"
BLUE = "#2865A8"
TEAL = "#087E83"
AMBER = "#A66618"
PURPLE = "#7652AD"
RED = "#B44A4A"


def label(eyebrow: str, title: str, lines: list[str], color: str = BLUE) -> str:
    """HTML labels keep component names distinct from explanatory text."""
    rows = [
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{color}" POINT-SIZE="10"><B>{escape(eyebrow)}</B></FONT></TD></TR>',
        f'<TR><TD ALIGN="LEFT" CELLPADDING="7"><FONT COLOR="{INK}" POINT-SIZE="17"><B>{escape(title)}</B></FONT></TD></TR>',
    ]
    rows.extend(
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{MUTED}" POINT-SIZE="12">{escape(line)}</FONT></TD></TR>'
        for line in lines
    )
    return '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3">' + "".join(rows) + "</TABLE>>"


def card(key: str, eyebrow: str, title: str, *lines: str, color: str = BLUE, fill: str = "#FFFFFF") -> Node:
    return Node(label(eyebrow, title, list(lines), color), nodeid=key,
                color=color, fillcolor=fill, tooltip=" | ".join((title, *lines)))


def group(title: str, *, color: str = "#CAD6E2", fill: str = "#F4F7FA") -> Cluster:
    return Cluster(title, graph_attr={
        "style": "rounded,filled", "bgcolor": fill, "fillcolor": fill, "color": color,
        "penwidth": "1.1", "fontname": "Helvetica", "fontsize": "12",
        "fontcolor": MUTED, "labeljust": "l", "labelloc": "t", "margin": "22",
    })


def link(text: str = "", color: str = BLUE, **attrs: str) -> Edge:
    return Edge(label=text, color=color, fontcolor=color,
                fontname="Helvetica", fontsize="10", **attrs)


class ArchitectureDiagram(Diagram):
    """Also support source-only generation for alternate Graphviz renderers."""
    def __init__(self, title: str, subtitle: str, path: Path, *, dot_only: bool, direction: str = "LR"):
        self.dot_only = dot_only
        heading = (
            '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5">'
            f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="27" COLOR="{INK}"><B>{escape(title)}</B></FONT></TD></TR>'
            f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="13" COLOR="{MUTED}">{escape(subtitle)}</FONT></TD></TR>'
            '<TR><TD HEIGHT="15"></TD></TR></TABLE>>'
        )
        super().__init__(title, filename=str(path), show=False, direction=direction,
                         outformat=["svg", "png"], graph_attr={
            "label": heading, "labelloc": "t", "labeljust": "l",
            "bgcolor": "#FFFFFF", "pad": "0.4", "nodesep": "0.40", "ranksep": "0.65",
            "splines": "spline", "fontname": "Helvetica", "dpi": "160", "newrank": "true",
        }, node_attr={
            "shape": "box", "style": "rounded,filled", "fixedsize": "false",
            "width": "0", "height": "0", "margin": "0.18,0.16",
            "labelloc": "c", "penwidth": "1.25", "fontname": "Helvetica",
        }, edge_attr={
            "fontname": "Helvetica", "fontsize": "10", "penwidth": "1.6", "arrowsize": "0.7",
        })

    def render(self) -> None:
        if self.dot_only:
            Path(self.filename + ".gv").write_text(self.dot.source, encoding="utf-8")
            # Diagram.__exit__ removes this intermediate filename after rendering.
            self.dot.save()
        else:
            super().render()


def overview(output: Path, dot_only: bool) -> None:
    with ArchitectureDiagram(
        "Personal memory, with a durable source of truth",
        "01 / SYSTEM VIEW     One shared Python runtime  ·  local SQLite  ·  1,000–10,000 active facts",
        output / "architecture-system", dot_only=dot_only,
    ) as diagram:
        with group("CALLER / CONVERSATIONAL LAYER", fill="#F7F9FC"):
            assistant = card("assistant", "USER INTENT", "Assistant or application",
                             "User supplies facts and questions",
                             "An LLM may propose typed operations",
                             "and phrase the returned evidence")
            result = card("result", "RETURN CONTRACT", "Small, explainable results",
                          "Matching facts + why_matched",
                          "Source, confidence, status and dates",
                          "Search rank is separate from confidence", color=TEAL)

        with group("LOCAL EXECUTION / no memory server", fill="#F7FAFC"):
            with group("ENTRY POINTS / both reach the same package"):
                entry = card("entry", "PYTHON + MMS SKILLS", "One shared runtime",
                             "Python API: MemoryEngine",
                             "MMS skills → memory.py launcher",
                             "→ memory_engine.cli (JSON interface)")
            with group("MEMORY ENGINE / memory_engine/", fill="#F0F5FB"):
                engine = card("engine", "ENGINE.PY + RESOLUTION.PY", "Resolve, validate, dispatch",
                              "Entity UUID, normalized name or alias",
                              "Unknown / ambiguous → explicit error",
                              "Validate predicate, value and UTC time")
                writes = card("writes", "MUTATION PATH", "Preserve fact history",
                              "remember · correct · lifecycle",
                              "Repeat → observation; change → supersede",
                              "Archive / forget: caller confirmation", color=AMBER, fill="#FFFBF3")
                exact = card("exact", "DETERMINISTIC READ PATH", "Retrieve precise facts",
                             "lookup · history · at · related_to",
                             "changed_between · narrow answer()",
                             "Explicit subject / predicate / context", color=TEAL, fill="#F2FAF9")
                search = card("search", "SEARCH.PY / EXPLICIT OPT-IN", "Rank existing candidates",
                              "Keyword: FTS5 / BM25 (default)",
                              "Optional local vectors / cosine",
                              "Hybrid: reciprocal rank fusion",
                              "Re-read SQLite with final filters", color=PURPLE, fill="#F8F5FC")
            with group("STORAGE.PY / one versioned SQLite database", fill="#EDF5F8"):
                store = card("store", "AUTHORITATIVE RECORDS", "SQLiteStore · schema v1",
                             "entities + aliases: stable identity",
                             "facts + observations: values / evidence",
                             "Validity, provenance, supersession links",
                             "BEGIN IMMEDIATE · WAL · foreign keys",
                             "Unique current subject/predicate/context", color=BLUE)
                derived = card("derived", "REBUILDABLE / SAME DATABASE", "Search indexes & cache",
                               "fact_search: trigger-synchronized FTS5",
                               "embeddings: fact + model + text digest",
                               "Local model files loaded separately", color=PURPLE, fill="#F8F5FC")
                recovery = card("recovery", "PORTABILITY & RECOVERY", "Back up, export, migrate",
                                "SQLite backup / restore to a new file",
                                "JSONL export / import into empty DB",
                                "Legacy layouts → backed-up migration",
                                "Exports omit derived search data", color=MUTED)

        assistant >> link("typed call") >> entry
        entry >> link() >> engine
        engine >> link("write", AMBER) >> writes
        engine >> link("exact", TEAL) >> exact
        engine >> link("search", PURPLE, style="dashed") >> search
        writes >> link("atomic mutation", AMBER) >> store
        exact >> link("indexed SQL", TEAL, dir="both") >> store
        search >> link("verify fact IDs", PURPLE, style="dashed") >> store
        search >> link("rank candidates", PURPLE, style="dashed", dir="both") >> derived
        store >> link("backup / export", MUTED, style="dotted", constraint="false") >> recovery
        engine >> link("facts / search hits", TEAL, constraint="false") >> result
        # Keep storage facilities in one column, rather than extending the canvas.
        with diagram.dot.subgraph() as rank:
            rank.attr(rank="same")
            for node in (derived, store, recovery):
                rank.node(node.nodeid)
            rank.edge(recovery.nodeid, derived.nodeid, style="invis")
            rank.edge(derived.nodeid, store.nodeid, style="invis")
        with diagram.dot.subgraph() as rank:
            rank.attr(rank="same")
            for node in (writes, exact, search):
                rank.node(node.nodeid)
            rank.edge(search.nodeid, exact.nodeid, style="invis")
            rank.edge(exact.nodeid, writes.nodeid, style="invis")
        with diagram.dot.subgraph() as rank:
            rank.attr(rank="same")
            rank.node(assistant.nodeid)
            rank.node(result.nodeid)
            rank.edge(result.nodeid, assistant.nodeid, style="invis")


def flows(output: Path, dot_only: bool) -> None:
    with ArchitectureDiagram(
        "How facts are written, recalled and checked",
        "02 / REQUEST FLOWS     Amber = writes  ·  teal = exact reads  ·  purple dashed = ranked candidates",
        output / "architecture-flows", dot_only=dot_only,
    ) as diagram:
        # Diagrams / dot place independent clusters in reverse declaration
        # order. Declare D through A so the reader sees A through D.
        with group("D / USER-FACING LIFECYCLE GUARDRAILS", color="#E3C8C8", fill="#FFF8F7"):
            display = card("display", "1 / DISPLAY EXACT FACT", "Obtain confirmation",
                           "Show the value, provenance and fact ID",
                           "Require ARCHIVE <id> or DELETE <id>",
                           "Skill / application owns this interaction", color=RED)
            operation = card("operation", "2 / EXECUTE EXACT OPERATION", "Archive or forget",
                             "CLI requires --fact-id and --confirm",
                             "API caller must obtain consent first",
                             "Ordinary correction preserves history", color=RED)
            outcome = card("outcome", "3 / DISTINCT OUTCOMES", "Hide or permanently delete",
                           "Archive: hidden from current lookup",
                           "Forget: remove fact, evidence + caches",
                           "Earlier backups / exports retain copies", color=RED)
            display >> link("confirmed ID", RED) >> operation
            operation >> link("exact fact only", RED) >> outcome

        with group("C / KEYWORD, SEMANTIC OR HYBRID SEARCH", color="#D5C5E9", fill="#F8F5FC"):
            request = card("request", "1 / BOUNDED SEARCH", "Query + explicit filters",
                           "Default: keyword, current, 5 results",
                           "Subject, predicate, context, time scope",
                           "Semantic mode needs a local provider", color=PURPLE)
            ranking = card("ranking", "2 / SEARCH.PY", "Generate ranked fact IDs",
                           "FTS5 BM25 and/or local cosine scores",
                           "Reuse or refresh cached embeddings",
                           "Hybrid merges ranks: RRF, k = 60",
                           "Vectors propose; they do not assert", color=PURPLE)
            verified = card("verified", "3 / RE-READ SQLITE", "Verify, filter, limit",
                            "Reapply subject / lifecycle / time filters",
                            "Return SearchHit with full fact evidence",
                            "score + methods + semantic similarity",
                            "Caller checks relevance before answering", color=PURPLE)
            request >> link("eligible facts", PURPLE, style="dashed") >> ranking
            ranking >> link("candidate IDs", PURPLE, style="dashed") >> verified

        with group("B / EXACT RECALL", color="#B8DAD8", fill="#F2FAF9"):
            query = card("query", "1 / EXPLICIT QUERY", "Resolve the identity",
                         "UUID / normalized canonical name / alias",
                         "Type may disambiguate a known entity",
                         "Unknown or ambiguous: stop and clarify", color=TEAL)
            sql = card("sql", "2 / INDEXED SQL", "Apply exact constraints",
                       "Subject + predicate + optional context",
                       "Current, history or validity at a time",
                       "answer(): known rules or explicit error", color=TEAL)
            facts = card("facts", "3 / RETRIEVEDFACT", "Return the evidence",
                         "Value / relationship + context",
                         "Source, confidence, status and dates",
                         "why_matched + supersession linkage", color=TEAL)
            query >> link("exact entity", TEAL) >> sql
            sql >> link("matching rows", TEAL) >> facts

        with group("A / REMEMBER OR CORRECT", color="#E5D2AE", fill="#FFFBF3"):
            write = card("write", "1 / STRUCTURED INPUT", "Resolve & validate",
                         "Stable entity + snake_case predicate",
                         "JSON value + context + source",
                         "Timezone-aware validity / observation", color=AMBER)
            transaction = card("transaction", "2 / BEGIN IMMEDIATE", "Compare the current slot",
                               "Same assertion: add observation",
                               "Different value: close + supersede old",
                               "Insert replacement + observation", color=AMBER)
            commit = card("commit", "3 / COMMIT TO SQLITE", "One current fact per slot",
                          "(subject, predicate, context)",
                          "Unique index + interval validation",
                          "History and provenance remain intact", color=AMBER)
            write >> link("resolved fields", AMBER) >> transaction
            transaction >> link("one transaction", AMBER) >> commit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "assets")
    parser.add_argument("--dot-only", action="store_true", help="emit .gv files; no native Graphviz required")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    overview(args.output_dir, args.dot_only)
    flows(args.output_dir, args.dot_only)


if __name__ == "__main__":
    main()
