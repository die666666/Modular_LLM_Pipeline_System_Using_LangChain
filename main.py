"""
main.py -- AutoChain v2
Friendly, warm, witty terminal assistant.
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import textwrap
import time
from pathlib import Path

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ── ANSI colors ───────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA= "\033[95m"
    RED    = "\033[91m"
    WHITE  = "\033[97m"
    BLUE   = "\033[94m"

def c(color: str, text: str) -> str:
    return f"{color}{text}{C.RESET}"

def bold(text: str) -> str:
    return f"{C.BOLD}{text}{C.RESET}"


# ── Typing effect ─────────────────────────────────────────────────────

def typewrite(text: str, delay: float = 0.018) -> None:
    """Print text with a typewriter effect."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def think(msg: str = None) -> None:
    """Animated thinking indicator."""
    msgs = msg or random.choice([
        "Let me think about that...",
        "Crunching the numbers...",
        "Reading carefully...",
        "On it...",
        "Give me a sec...",
        "Consulting my inner analyst...",
    ])
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    print()
    for i in range(18):
        frame = frames[i % len(frames)]
        sys.stdout.write(f"\r  {c(C.CYAN, frame)}  {c(C.DIM, msgs)}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()


def say(text: str, color: str = C.WHITE, typing: bool = False) -> None:
    """AutoChain speaks."""
    prefix = c(C.CYAN, "  AutoChain › ")
    if typing:
        sys.stdout.write(prefix)
        sys.stdout.flush()
        typewrite(text, delay=0.015)
    else:
        print(f"{prefix}{color}{text}{C.RESET}")


def whisper(text: str) -> None:
    """Dimmed secondary info."""
    print(c(C.DIM, f"  {text}"))


def success(text: str) -> None:
    print(f"  {c(C.GREEN, '✓')}  {text}")


def warn(text: str) -> None:
    print(f"  {c(C.YELLOW, '⚠')}  {text}")


def err(text: str) -> None:
    print(f"  {c(C.RED, '✗')}  {text}")
    sys.exit(1)


# ── Banner ────────────────────────────────────────────────────────────

def banner(title: str, subtitle: str = "") -> None:
    print()
    print(c(C.CYAN, "  ╭" + "─" * 56 + "╮"))
    print(c(C.CYAN, "  │") + c(C.BOLD + C.WHITE, f"  {title:<54}") + c(C.CYAN, "│"))
    if subtitle:
        print(c(C.CYAN, "  │") + c(C.DIM, f"  {subtitle:<54}") + c(C.CYAN, "│"))
    print(c(C.CYAN, "  ╰" + "─" * 56 + "╯"))
    print()


def result_box(title: str, lines: list[tuple[str, str]]) -> None:
    """Render a labeled result box. lines = [(label, value), ...]"""
    print()
    print(c(C.CYAN,  "  ┌─") + c(C.BOLD, f" {title} ") + c(C.CYAN, "─" * max(0, 50 - len(title)) + "┐"))
    for label, value in lines:
        if value:
            label_str = c(C.DIM, f"  │  {label:<14}")
            value_str = c(C.WHITE, str(value))
            print(f"{label_str}{value_str}")
    print(c(C.CYAN, "  └" + "─" * 54 + "┘"))
    print()


def divider(label: str = "") -> None:
    if label:
        pad = "─" * max(0, 50 - len(label))
        print(c(C.DIM, f"\n  ── {label} {pad}"))
    else:
        print(c(C.DIM, "  " + "─" * 54))


# ── Splash screen ─────────────────────────────────────────────────────

SPLASH = f"""
{C.CYAN}{C.BOLD}
 █████╗ ██╗   ██╗████████╗ ██████╗  ██████╗██╗  ██╗ █████╗ ██╗███╗   ██╗
██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗██╔════╝██║  ██║██╔══██╗██║████╗  ██║
███████║██║   ██║   ██║   ██║   ██║██║     ███████║███████║██║██╔██╗ ██║
██╔══██║██║   ██║   ██║   ██║   ██║██║     ██╔══██║██╔══██║██║██║╚██╗██║
██║  ██║╚██████╔╝   ██║   ╚██████╔╝╚██████╗██║  ██║██║  ██║██║██║ ╚████║
╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝  ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝

{C.RESET}"""

TAGLINES = [
    "Your local AI analyst — no cloud, no drama.",
    "Powered by Ollama. Fueled by curiosity.",
    "Thinks fast. Talks straight. Occasionally funny.",
    "Like having a financial analyst who also does everything else.",
]


def splash() -> None:
    print(SPLASH)
    typewrite(c(C.DIM, f"  {random.choice(TAGLINES)}"), delay=0.02)
    print()


# ── File reading ──────────────────────────────────────────────────────

def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def read_pdf(path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n\n".join(pages).strip()
    except ImportError:
        err("pdfplumber not installed. Run: pip install pdfplumber")


def load_file(path_str: str) -> str:
    path = Path(path_str.strip().strip('"').strip("'"))
    if not path.exists():
        err(f"File not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".txt":
        text = read_txt(path)
    elif suffix == ".pdf":
        text = read_pdf(path)
    else:
        err(f"Unsupported format '{suffix}' — I only speak .txt and .pdf, sorry!")
    if not text:
        err("That file seems empty. Got anything with actual content?")
    success(f"Loaded {c(C.CYAN, path.name)}  {c(C.DIM, f'({len(text):,} chars)')}")
    return text


def prompt_for_file(label: str) -> str:
    say(label, typing=True)
    whisper("Tip: drag and drop the file into the terminal to paste the path")
    print()
    path_str = input(c(C.CYAN, "  › ")).strip()
    return load_file(path_str)


# ── Terminal input helpers ────────────────────────────────────────────

def read_multiline(prompt: str) -> str:
    say(prompt, typing=True)
    whisper("Press Enter twice when you're done\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines).strip()


def read_single(prompt: str) -> str:
    print()
    return input(c(C.CYAN, f"  › {prompt}: ")).strip()


def confirm(question: str) -> bool:
    ans = input(c(C.DIM, f"\n  {question} [y/n] › ")).strip().lower()
    return ans in ("y", "yes")


# ── Mode runners ──────────────────────────────────────────────────────

def run_financial(engine, file: str | None = None) -> None:
    from pipeline.chains import FinancialChain

    banner("Financial Extraction", "Let's see what the numbers say")

    if file:
        text = load_file(file)
    else:
        say("Drop a .txt or .pdf file — earnings report, press release, balance sheet, anything financial.", typing=True)
        print()
        text = prompt_for_file("What's the file path?")

    think("Reading every line like a seasoned analyst...")
    chain = FinancialChain(engine.get_llm())
    report = chain.run(text)

    say("Here's what I found:", color=C.GREEN, typing=True)

    rows = [
        ("Company",    report.company),
        ("Revenue",    report.revenue),
        ("Net Income", report.net_income),
        ("EBITDA",     report.ebitda),
        ("Outlook",    report.outlook),
    ]
    result_box("Extracted Data", [(l, v) for l, v in rows if v])

    if report.key_metrics:
        divider("Key Metrics")
        for m in report.key_metrics:
            print(f"  {c(C.GREEN, '•')} {m}")

    if report.risks:
        divider("Risk Factors")
        for r in report.risks:
            print(f"  {c(C.YELLOW, '•')} {r}")

    print()
    whisper(f"Token usage: {engine.token_usage}")


def run_summarize(engine, file: str | None = None) -> None:
    from pipeline.chains import SummarizationChain

    banner("Document Summarization", "TLDR, but make it intelligent")

    if file:
        doc = load_file(file)
    else:
        say("Hand me a .txt or .pdf — article, report, paper, meeting notes, anything.", typing=True)
        print()
        doc = prompt_for_file("What's the file path?")

    think("Digesting the whole thing so you don't have to...")
    chain = SummarizationChain(engine.get_llm())
    result = chain.run(doc)

    say("Here's the short version:", color=C.GREEN, typing=True)
    divider()
    for line in result.raw_summary.splitlines():
        print(f"  {line}")
    divider()
    print()
    whisper(f"Token usage: {engine.token_usage}")


def run_reason(engine, **_) -> None:
    from pipeline.chains import ReasoningChain

    banner("Multi-step Reasoning", "Let's think this through together")

    say("What's on your mind? Give me a problem, decision, or question.", typing=True)
    whisper("Examples: product prioritization, architecture tradeoffs, market decisions...\n")

    problem = read_multiline("Go ahead —")
    if not problem:
        warn("Nothing to reason about. Try again!")
        return

    think("Breaking it down step by step...")
    chain = ReasoningChain(engine.get_llm())
    result = chain.run(problem)

    say("Alright, here's how I'd think about it:", color=C.GREEN, typing=True)

    divider("Step-by-step Reasoning")
    for line in result.steps.splitlines():
        print(f"  {line}")

    divider("Final Answer")
    for line in result.final_answer.splitlines():
        print(f"  {c(C.WHITE, line)}")

    divider("Devil's Advocate")
    for line in result.critique.splitlines():
        print(f"  {c(C.YELLOW, line)}")

    confidence_color = {
        "High": C.GREEN, "Medium": C.YELLOW, "Low": C.RED
    }.get(result.confidence, C.WHITE)
    print(f"\n  Confidence: {c(confidence_color, bold(result.confidence))}")
    print()
    whisper(f"Token usage: {engine.token_usage}")


def run_chat(engine, **_) -> None:
    banner("Free-form Chat", "Ask me literally anything")

    say("I'm all yours. Finance, code, ideas, questions, random curiosity — bring it.", typing=True)
    whisper("Commands: 'exit' to quit · 'clear' to reset conversation\n")

    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.output_parsers import StrOutputParser

    llm = engine.get_llm()
    parser = StrOutputParser()
    history = [
        SystemMessage(content=(
            "You are AutoChain — a sharp, friendly, and occasionally witty AI assistant. "
            "You're warm and approachable but always professional and accurate. "
            "You give clear, direct answers without being robotic. "
            "If something is funny or worth a light comment, go for it — but always prioritize being genuinely helpful. "
            "You help with finance, coding, reasoning, research, and anything else the user needs."
        ))
    ]

    while True:
        try:
            print()
            user_input = input(c(C.MAGENTA, "  You › ") + C.WHITE).strip()
            print(C.RESET, end="")
        except (EOFError, KeyboardInterrupt):
            print()
            say("Catch you later! 👋", typing=True)
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            say("Later! Come back anytime. 👋", typing=True)
            break
        if user_input.lower() == "clear":
            history = [history[0]]
            say("Fresh start — conversation cleared.", color=C.DIM)
            continue

        history.append(HumanMessage(content=user_input))
        think()

        try:
            response = llm.invoke(history)
            reply = parser.invoke(response)
            print(c(C.CYAN, "  AutoChain › ") + C.WHITE)
            for line in reply.splitlines():
                print(f"  {line}")
            print(C.RESET, end="")
            history.append(AIMessage(content=reply))
            engine._record_tokens(response)
        except Exception as exc:
            warn(f"Something went wrong: {exc}")
            history.pop()


def run_demo_interactive(engine, **_) -> None:
    splash()
    say("Hey! What do you want to work on today?", typing=True)
    print()
    options = [
        ("1", "Financial Extraction",   "upload a .txt or .pdf"),
        ("2", "Document Summarization", "upload a .txt or .pdf"),
        ("3", "Multi-step Reasoning",   "type a problem or question"),
        ("4", "Free-form Chat",         "ask me literally anything"),
    ]
    for num, label, hint in options:
        print(f"  {c(C.CYAN, num + '.')} {bold(label)}  {c(C.DIM, hint)}")

    print()
    choice = input(c(C.CYAN, "  › Pick a mode (1-4): ")).strip()
    mode_map = {
        "1": lambda: run_financial(engine),
        "2": lambda: run_summarize(engine),
        "3": lambda: run_reason(engine),
        "4": lambda: run_chat(engine),
    }
    fn = mode_map.get(choice)
    if not fn:
        warn("That's not one of the options — pick a number from 1 to 4.")
        return
    fn()
    engine.reset_token_usage()
    if confirm("Want to do something else?"):
        run_demo_interactive(engine)


def run_evaluation(engine, file: str | None = None, file2: str | None = None) -> None:
    from pipeline.chains import FinancialChain, SummarizationChain
    from pipeline.evaluators import PipelineEvaluator, EvalSuite

    banner("Evaluation Harness", "temp 0.0 vs 0.7 · default vs alt prompts · 8 calls")

    say("I'll need two files — one financial doc, one document to summarize.", typing=True)
    print()

    fin_text = load_file(file)  if file  else prompt_for_file("Financial file:")
    doc_text = load_file(file2) if file2 else prompt_for_file("Summarization file:")

    think("Running all 8 evaluation calls, this might take a minute...")

    evaluator = PipelineEvaluator(model=engine.primary_model)
    evaluator.register(EvalSuite(
        name="Financial",
        chain_factory=lambda llm, alt: FinancialChain(llm, use_alt_prompt=alt),
        invoke_fn=lambda chain, text: chain.run(text),
        sample_input=fin_text,
    ))
    evaluator.register(EvalSuite(
        name="Summarize",
        chain_factory=lambda llm, alt: SummarizationChain(llm, use_alt_prompt=alt),
        invoke_fn=lambda chain, doc: chain.run(doc),
        sample_input=doc_text,
    ))

    results = evaluator.run_all()
    say("Done! Here's how each run compared:", color=C.GREEN, typing=True)
    print()
    evaluator.print_table(results)


# ── CLI ───────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="AutoChain v2 — your friendly local AI pipeline")
    p.add_argument("--mode", choices=["demo","financial","summarize","reason","chat","eval"], default="demo")
    p.add_argument("--model", default="qwen2.5:3b")
    p.add_argument("--temp",  type=float, default=0.0)
    p.add_argument("--file",  default=None, help=".txt or .pdf for financial/summarize")
    p.add_argument("--file2", default=None, help="Second file for eval mode")
    return p.parse_args()


def main():
    args = parse_args()

    from pipeline.core import PipelineEngine
    engine = PipelineEngine(
        primary_model=args.model,
        fallback_model=args.model,
        temperature=args.temp,
    )

    runners = {
        "demo":      lambda: run_demo_interactive(engine),
        "financial": lambda: run_financial(engine, file=args.file),
        "summarize": lambda: run_summarize(engine, file=args.file),
        "reason":    lambda: run_reason(engine),
        "chat":      lambda: run_chat(engine),
        "eval":      lambda: run_evaluation(engine, file=args.file, file2=args.file2),
    }

    try:
        runners[args.mode]()
    except KeyboardInterrupt:
        print()
        say("Alright, shutting down. See you next time! 👋", typing=True)
        sys.exit(0)


if __name__ == "__main__":
    main()