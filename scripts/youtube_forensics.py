#!/usr/bin/env python3
"""Run source-disciplined forensic analysis directly against a public YouTube video via Gemini."""

import argparse
import os
import pathlib
import re
from google import genai

MODEL_DEFAULT = "gemini-3.6-flash"

BASE_RULES = """
Treat the linked YouTube video as the PRIMARY SOURCE. Ignore prior summaries. Preserve speaker terminology. Never invent timestamps, quotes, examples, names, or connections. Label uncertain wording CLOSE PARAPHRASE, not QUOTE. Distinguish spoken content from visible/on-screen content when possible. If evidence is absent, say Not explicitly stated. Do not force a target tool count. Source fidelity is more important than elegance or brevity.
""".strip()

TIMELINE_TEMPLATE = """
PASS 1 — CHRONOLOGICAL SOURCE MAP
Analyze ONLY {start}–{end}. Do not summarize the rest of the video.
For each conceptual interval (normally 2–3 minutes; shorter when the subject changes), report exactly:
Interval:
Main Subject:
New Concepts:
Named Terms:
Questions:
Rules/Instructions:
Examples:
Claims:
Transition:
Candidates:

Capture named and unnamed reusable reasoning devices, diagram notation, diagnostic questions, principles, heuristics, examples, and transitions. Explicitly check for POSIWID/the purpose of a system is what it does; reinforcing/balancing loops; feedback; delays; stocks/flows; constraints; bottlenecks; incentives; unintended consequences; leverage points; local/global optimization; boundaries; outputs; measurement; planning; guilt/blame; adaptation; resilience; and system archetypes. Do not claim a concept appears unless it actually does.
""".strip()

PASSES = [
    (2, "VOCABULARY EXTRACTION", "Extract every phrase used as a named concept, framework, rule, method, system, page, board, list, audit, review, ritual, scan, sort, sweep, ledger, rotation, checklist, loop, archetype, or similar reusable construct. Give term, first timestamp, other timestamps, exact wording, introduction context, recurrence, likely status, confidence."),
    (3, "QUESTION EXTRACTION", "Extract every reusable diagnostic question the speaker teaches or repeatedly uses. Give timestamp, question/close paraphrase, context, decision helped, parent tool if any, and whether it could function independently."),
    (4, "EXAMPLE INVENTORY", "Inventory every substantive example, scenario, demonstration, case study, or recurring character. Give timestamp/range, scenario, what happens, concept demonstrated, what speaker says it proves, whether it introduces a concept, whether it returns, and whether it connects tools."),
    (5, "RECURRING CHARACTER / WORKED EXAMPLE", "Identify any recurring named or unnamed worked example. Trace every appearance chronologically at maximum resolution: starting state, intervention, result, remaining problem, next intervention, explicit lesson, and strongest supported quote/close paraphrase. If no recurring character exists, say so."),
    (6, "CLAIMS AND PRINCIPLES", "Ignore named tools temporarily. Extract reusable general claims about systems, structure, feedback, attention, incentives, constraints, delays, measurement, maintenance, failure, resilience, boundaries, guilt/blame, outputs, and unintended consequences. Classify each as Principle, Mental Model, component, or observation."),
    (7, "POSIWID FORENSIC CHECK", "Search the entire source for POSIWID, 'the purpose of a system is what it does', purpose/output/result-versus-intention language, or equivalent. Report exact term, timestamp, surrounding context, quote/close paraphrase, whether Stafford Beer is named, example, and role in course. Do not equate mere similarity with a match."),
    (8, "GUILT, BLAME, AND COMPLETION", "Find every meaningful discussion of guilt, blame, being behind, completion, permission to stop, motivation, individual failure versus structural failure, and open loops. For each: timestamp, claim, related tool, mechanism/benefit/principle status, quote/close paraphrase."),
    (9, "PLANNING AND REVIEW RITUALS", "Map every daily, weekly, monthly, quarterly, annual, event-triggered, or habit-triggered planning/review cadence. For each: what happens, when, tools involved, inputs, outputs, and where outputs go next."),
    (10, "INPUT PROCESS OUTPUT MAP", "For every confirmed framework, identify INPUT, PROCESS, OUTPUT, and NEXT DESTINATION. Then identify loops where one tool's output becomes another tool's input."),
    (11, "DEPENDENCIES AND BOTTLENECKS", "For each tool ask what must already exist, what happens if the previous system fails, where information/tasks get stuck, where limits/escalation/review/feedback are introduced, and where system failure is addressed. Mark explicit versus inferred."),
    (12, "NUMBERS LIMITS CADENCES RULES", "Extract every operational number, threshold, limit, cadence, duration, count, or hard rule. Give number/rule, timestamp, tool, exact context, and whether hard rule or example."),
    (13, "QUOTE AUDIT", "Identify the strongest quote-worthy lines across the course. For each: timestamp, exact wording if verifiable, otherwise CLOSE PARAPHRASE, concept supported, and why it matters. Never put uncertain wording in quotation marks."),
    (14, "NAME AUDIT", "List every candidate tool/framework name and verify whether it is spoken, displayed on screen, both, or inferred. Give first timestamp, exact wording, and whether normalization would change the source name."),
    (15, "EXAMPLE AUDIT", "Re-check all major examples for exact source support. For each: concept, timestamp, verified scenario, what it proves, and any detail that would be unsafe to infer."),
    (16, "SCREEN VS SPOKEN CONTENT", "Distinguish important content that is SPOKEN, DISPLAYED ON SCREEN, BOTH, or INFERRED FROM VISUAL STRUCTURE. If visual inspection is unreliable, state that limitation."),
    (17, "TRANSITIONS", "Extract transitions between major course sections. Give timestamp, section leaving, section entering, transition language, what is claimed accomplished, and what new problem is introduced."),
    (18, "FINAL TEN MINUTES HIGH RESOLUTION", "Analyze the final ten minutes at especially high conceptual resolution. Break whenever subject changes. For each segment: timestamp range, what is said, what is shown if accessible, new term/rule/example, returning concept, connection to earlier material, possible missed tool/principle."),
    (19, "FAILURE TEST / CONTINUITY", "Investigate whether the course contains any failure-test, continuity, redundancy, resilience, absence-of-owner, or single-point-of-failure reasoning. Report exact source language and timestamps; do not import systems-engineering terms unless labeled inference."),
    (20, "CAPSTONE / INTEGRATION", "Reconstruct any capstone or integration section: what the integrated system is, what components enter it, order, what makes it more than tips, what happens under fatigue/forgetting/busyness/absence, what remains manual, how review changes it, and final success criterion. Give timestamps."),
    (21, "NEGATIVE EVIDENCE", "Create THINGS WE LOOKED FOR BUT THE COURSE DOES NOT ACTUALLY TEACH. Explicitly report requested concepts that were searched for but unsupported."),
    (22, "FINAL RECONCILIATION", "Only now determine the source-supported conceptual inventory. Separate A explicitly named tools/frameworks, B explicitly taught principles/mental models, C capstone/integration mechanisms, D borderline/embedded concepts. State source-supported count without forcing any advertised count."),
    (23, "MASTER EXTRACTION", "Rebuild the complete chronological toolset. For every entry use: TOOL NUMBER; TYPE (Tool/Framework/Diagnostic Question/Mental Model/Principle); EXACT NAME USED; TIMESTAMP; ONE-SENTENCE DEFINITION; PROBLEM; QUESTION; HOW USED; EXAMPLE; WHAT EXAMPLE PROVES; FAILURE MODE; CONNECTION PREVIOUS; CONNECTION NEXT; QUOTE OR CLOSE PARAPHRASE; CONFIDENCE. Same depth for early and late entries."),
    (24, "SELF AUDIT", "Audit the analysis itself. State final timestamp inspected; whether any output compression occurred; uncertain names/quotes/examples; concepts likely to be missed by another pass; and confidence that another independent pass would find no additional reusable concept."),
]


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "youtube-source"


def ask(client, model: str, url: str, prompt: str) -> str:
    interaction = client.interactions.create(
        model=model,
        input=[
            {"type": "text", "text": BASE_RULES + "\n\n" + prompt},
            {"type": "video", "uri": url},
        ],
    )
    return interaction.output_text


def write(outdir: pathlib.Path, name: str, text: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / name).write_text(text.rstrip() + "\n", encoding="utf-8")
    print(f"wrote {outdir / name}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("youtube_url")
    p.add_argument("--slug", default="")
    p.add_argument("--model", default=MODEL_DEFAULT)
    p.add_argument("--mode", choices=["map", "full"], default="full")
    p.add_argument("--minutes", type=int, default=60, help="Approximate video duration; timeline is analyzed in 10-minute windows")
    p.add_argument("--output-root", default="research/youtube")
    args = p.parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is required")

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    slug = slugify(args.slug or args.youtube_url.split("v=")[-1])
    outdir = pathlib.Path(args.output_root) / slug

    # Pass 1 is deliberately chunked to defeat late-answer compression.
    for start_min in range(0, args.minutes, 10):
        end_min = min(start_min + 10, args.minutes)
        prompt = TIMELINE_TEMPLATE.format(start=f"{start_min}:00", end=f"{end_min}:00")
        text = ask(client, args.model, args.youtube_url, prompt)
        write(outdir, f"pass-01-{start_min:02d}-{end_min:02d}.md", text)

    if args.mode == "full":
        for number, title, instruction in PASSES:
            prompt = f"PASS {number} — {title}\n\n{instruction}\n\nAnalyze the ENTIRE source unless this pass explicitly specifies a narrower interval."
            text = ask(client, args.model, args.youtube_url, prompt)
            write(outdir, f"pass-{number:02d}.md", text)

    index = [
        f"# YouTube Forensics: {slug}",
        "",
        f"Source: {args.youtube_url}",
        f"Model: {args.model}",
        f"Mode: {args.mode}",
        "",
        "The source video is primary. Pass files are independent interrogations designed to expose omissions and hallucinated specificity.",
    ]
    write(outdir, "README.md", "\n".join(index))


if __name__ == "__main__":
    main()
