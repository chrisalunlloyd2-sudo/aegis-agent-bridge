"""Parse Aegis Machine 1 daily foundry/soak email."""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DailyReport:
    date: Optional[str] = None
    projects_count: Optional[int] = None
    recently_active_repos: List[str] = field(default_factory=list)
    open_tasks: Optional[int] = None
    services_up: List[str] = field(default_factory=list)
    autonomy_status: Optional[str] = None
    disk_free_gb: Optional[float] = None
    ollama_status: Optional[str] = None
    brain_status: Optional[str] = None
    soak_rounds: Optional[int] = None
    fastest_models: Dict[str, float] = field(default_factory=dict)
    budget_user_llm_hr: Optional[str] = None
    game_leaders: List[dict] = field(default_factory=list)
    certified_gates: Optional[int] = None
    economy_wallets: Optional[int] = None
    moe_gate_pending: Optional[int] = None
    moe_gate_approved: Optional[int] = None
    moe_gate_rejected: Optional[int] = None
    nmct_sealed_valid: Optional[int] = None
    nmct_unsealed: Optional[int] = None
    nmct_tampered: Optional[int] = None
    correctness_approved_blocks: Optional[int] = None
    mined_all_time: Optional[int] = None
    gated_all_time: Optional[int] = None
    trust: Dict[str, Any] = field(default_factory=dict)
    mail_worth_a_look: List[str] = field(default_factory=list)
    health: Dict[str, str] = field(default_factory=dict)
    competition_leaderboard: List[dict] = field(default_factory=list)
    arena_champions: Dict[str, str] = field(default_factory=dict)
    dmaic_black_belts: Optional[int] = None
    logical_inconsistencies: List[dict] = field(default_factory=list)
    dmaic_pending_suggestions: Optional[int] = None
    model_behaviors_observations_24h: Optional[int] = None
    graduation_gate: Dict[str, float] = field(default_factory=dict)
    pull_leash_queue: Optional[int] = None
    soak_recent: Optional[str] = None
    data_guardian: Dict[str, Any] = field(default_factory=dict)
    attention: Optional[str] = None


def _decode_quoted_printable(body: str) -> str:
    # Minimal QP cleanup for Gmail IMAP plaintext
    body = body.replace("=\n", "")
    body = body.replace("=3D", "=")
    body = body.replace("=E2=80=A2", "•")
    body = body.replace("=E2=80=94", "—")
    body = body.replace("=E2=86=91", "↑")
    body = body.replace("=E2=9C=85", "✅")
    body = body.replace("=F0=9F=9F=A2", "🟢")
    body = body.replace("=F0=9F=8F=86", "🏆")
    return body


def _split_sections(body: str) -> tuple[str, str]:
    body = _decode_quoted_printable(body)
    parts = re.split(r"\n=+\n", body, maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    m = re.search(r"# Viper Soak — Daily Check-in", body)
    if m:
        return body[:m.start()], body[m.start():]
    return body, ""


def _extract_bullet_key_value(text: str, keys: List[str]) -> Dict[str, str]:
    out = {}
    lines = text.splitlines()
    for key in keys:
        for i, line in enumerate(lines):
            # Match bullet or markdown bold bullet, case-insensitive
            if re.match(rf"^\s*(?:\u2022|-\s*\*\*)\s*{re.escape(key)}\s*\*?\*?\s*[:：]", line, re.IGNORECASE):
                value = re.sub(rf"^\s*(?:\u2022|-\s*\*\*)\s*{re.escape(key)}\s*\*?\*?\s*[:：]\s*", "", line, flags=re.IGNORECASE)
                # Append continuation lines until next bullet or blank header
                for j in range(i + 1, len(lines)):
                    next_line = lines[j]
                    if re.match(r"^\s*(?:\u2022|-\s*\*\*)\s*\w", next_line):
                        break
                    if next_line.strip().startswith("#"):
                        break
                    value += " " + next_line.strip()
                out[key] = value.strip()
                break
    return out


def _extract_number_after_label(text: str, label: str) -> Optional[int]:
    pattern = re.compile(rf"{re.escape(label)}[:\s]+(\d+)", re.IGNORECASE)
    m = pattern.search(text)
    return int(m.group(1)) if m else None


def parse_daily_email(body: str) -> DailyReport:
    report = DailyReport()
    top, bottom = _split_sections(body)

    kv = _extract_bullet_key_value(
        top,
        ["projects", "system", "performance", "foundry", "Since yesterday", "Trust ledger", "Mail worth a look"],
    )

    if "projects" in kv:
        m = re.search(r"(\d+) projects", kv["projects"])
        if m:
            report.projects_count = int(m.group(1))
        m = re.search(r"Recently-active:\s*([^.]+)", kv["projects"])
        if m:
            report.recently_active_repos = [r.strip() for r in m.group(1).split(",") if r.strip()]
        m = re.search(r"Open tasks:\s*(\d+)", kv["projects"])
        if m:
            report.open_tasks = int(m.group(1))

    if "system" in kv:
        sys = kv["system"]
        m = re.search(r"Services UP:\s*([^.]+)", sys)
        if m:
            report.services_up = [s.strip() for s in m.group(1).split(",") if s.strip()]
        m = re.search(r"Aegis autonomy\s+(\S+)", sys)
        if m:
            report.autonomy_status = m.group(1)
        m = re.search(r"Disk free\s+(\d+(?:\.\d+)?)\s*GB", sys)
        if m:
            report.disk_free_gb = float(m.group(1))
        m = re.search(r"Ollama\s+(\S+)", sys)
        if m:
            report.ollama_status = m.group(1)
        m = re.search(r"brain\s+(\S+)", sys)
        if m:
            report.brain_status = m.group(1)

    if "performance" in kv:
        perf = kv["performance"]
        m = re.search(r"Soak\s+(\d+)", perf)
        if m:
            report.soak_rounds = int(m.group(1))
        report.budget_user_llm_hr = perf

    if "foundry" in kv:
        fnd = kv["foundry"]
        for m in re.finditer(r"([\w\.\-:]+)\((\d+)w\)", fnd):
            report.game_leaders.append({"model": m.group(1), "wins": int(m.group(2))})
        m = re.search(r"Certified gates:\s*(\d+)", fnd)
        if m:
            report.certified_gates = int(m.group(1))
        m = re.search(r"Economy wallets:\s*(\d+)", fnd)
        if m:
            report.economy_wallets = int(m.group(1))

    if "Since yesterday" in kv:
        sy = kv["Since yesterday"]
        m = re.search(r"Moe gate:\s*(\d+)\s+pending,\s*(\d+)\s+approved,\s*(\d+)\s+rejected", sy)
        if m:
            report.moe_gate_pending = int(m.group(1))
            report.moe_gate_approved = int(m.group(2))
            report.moe_gate_rejected = int(m.group(3))
        m = re.search(r"(\d+) sealed-valid,\s*(\d+) unsealed,\s*(\d+) tampered", sy)
        if m:
            report.nmct_sealed_valid = int(m.group(1))
            report.nmct_unsealed = int(m.group(2))
            report.nmct_tampered = int(m.group(3))
        m = re.search(r"Correctness audit:\s*OK\s*(\d+)\s+approved", sy)
        if m:
            report.correctness_approved_blocks = int(m.group(1))
        m = re.search(r"Soak foundry:\s*(\d+)\s+mined,\s*(\d+)\s+gated", sy)
        if m:
            report.mined_all_time = int(m.group(1))
            report.gated_all_time = int(m.group(2))

    if "Trust ledger" in kv:
        report.trust["raw"] = kv["Trust ledger"]

    if "Mail worth a look" in kv:
        raw = kv["Mail worth a look"]
        report.mail_worth_a_look = [line.strip("- ").strip() for line in raw.split("\n") if line.strip().startswith("-")]

    m = re.search(r"Viper Soak — Daily Check-in —\s*(.+)", bottom)
    if m:
        report.date = m.group(1).strip()

    health_section = re.search(r"Health\s*\n(.*?)(?:\n#|\n\*\*)", bottom, re.DOTALL)
    if health_section:
        for line in health_section.group(1).split("\n"):
            m = re.search(r"- \*\*([^*]+)\*\*:\s*(.+)", line)
            if m:
                report.health[m.group(1).strip()] = m.group(2).strip()

    lb_match = re.search(r"Competition leaderboard\s*\n\| model \| wins \| rounds \| win% \|\s*\n\|[-\| ]+\|\s*\n(.*?)(?:\n\n|\n#)", bottom, re.DOTALL)
    if lb_match:
        for line in lb_match.group(1).strip().split("\n"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[1]:
                report.competition_leaderboard.append({
                    "model": parts[1],
                    "wins": int(parts[2]),
                    "rounds": int(parts[3]),
                    "win_pct": parts[4].rstrip("%"),
                })

    dg = re.search(r"Data guardian\s*\n(.*?)(?:\n#|\n\*\*Attention|\Z)", bottom, re.DOTALL)
    if dg:
        report.data_guardian["raw"] = dg.group(1).strip()

    attn = re.search(r"Attention\s*\n(.+)", bottom)
    if attn:
        report.attention = attn.group(1).strip()

    return report
