#!/usr/bin/env python3
"""Compare mypy typing coverage between a base branch and a PR branch.

Runs mypy with ``--lineprecision-report`` and ``--linecount-report`` (or reads
pre-generated report directories) for both revisions, produces a Markdown
report suitable for a GitHub PR comment / step summary, and evaluates the
project's two-phase typing coverage policy:

1. While ``base`` precise-line coverage is below ``--threshold`` (default 50%),
   the check is strictly informational and exits 0.
2. Once ``base`` precise-line coverage reaches ``--threshold``, a regression
   greater than ``--max-drop`` percentage points (default 5.0 pp) fails the
   check (exit 1) unless ``--allow-regression`` is passed (for example via the
   ``allow-typing-regression`` PR label).
"""

from __future__ import annotations

import argparse
import dataclasses
import html
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Mapping

COMMENT_MARKER = "<!-- rope-typing-coverage -->"


@dataclasses.dataclass(frozen=True)
class ModulePrecision:
    lines: int
    precise: int
    imprecise: int
    any_lines: int
    empty: int
    unanalyzed: int

    @property
    def non_empty(self) -> int:
        return self.lines - self.empty

    @property
    def precision_pct(self) -> float:
        if self.non_empty <= 0:
            return 100.0
        return 100.0 * self.precise / self.non_empty


@dataclasses.dataclass(frozen=True)
class ModuleFuncCount:
    annotated_funcs: int
    total_funcs: int

    @property
    def annotated_pct(self) -> float:
        if self.total_funcs <= 0:
            return 100.0
        return 100.0 * self.annotated_funcs / self.total_funcs


@dataclasses.dataclass(frozen=True)
class CoverageSnapshot:
    precision_by_module: dict[str, ModulePrecision]
    funcs_by_module: dict[str, ModuleFuncCount]

    @property
    def precise_lines(self) -> int:
        return sum(m.precise for m in self.precision_by_module.values())

    @property
    def non_empty_lines(self) -> int:
        return sum(m.non_empty for m in self.precision_by_module.values())

    @property
    def precision_pct(self) -> float:
        if self.non_empty_lines <= 0:
            return 0.0
        return 100.0 * self.precise_lines / self.non_empty_lines

    @property
    def annotated_funcs(self) -> int:
        return sum(m.annotated_funcs for m in self.funcs_by_module.values())

    @property
    def total_funcs(self) -> int:
        return sum(m.total_funcs for m in self.funcs_by_module.values())

    @property
    def annotated_funcs_pct(self) -> float:
        if self.total_funcs <= 0:
            return 0.0
        return 100.0 * self.annotated_funcs / self.total_funcs


@dataclasses.dataclass(frozen=True)
class PolicyEvaluation:
    enforced: bool
    passed: bool
    bypassed: bool
    delta_pp: float
    status_label: str
    summary_line: str


def parse_lineprecision(path: Path) -> dict[str, ModulePrecision]:
    """Parse mypy's ``lineprecision.txt`` report."""
    modules: dict[str, ModulePrecision] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Name ") or set(stripped) == {"-"}:
            continue
        parts = stripped.split()
        if len(parts) != 7:
            continue
        name = parts[0]
        lines, precise, imprecise, any_lines, empty, unanalyzed = (
            int(v) for v in parts[1:]
        )
        modules[name] = ModulePrecision(
            lines=lines,
            precise=precise,
            imprecise=imprecise,
            any_lines=any_lines,
            empty=empty,
            unanalyzed=unanalyzed,
        )
    return modules


def parse_linecount(path: Path) -> dict[str, ModuleFuncCount]:
    """Parse mypy's ``linecount.txt`` report."""
    modules: dict[str, ModuleFuncCount] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != 5:
            continue
        name = parts[4]
        if name == "total":
            continue
        annotated_funcs = int(parts[2])
        total_funcs = int(parts[3])
        modules[name] = ModuleFuncCount(
            annotated_funcs=annotated_funcs,
            total_funcs=total_funcs,
        )
    return modules


def run_mypy_snapshot(source_root: Path, package: str) -> CoverageSnapshot:
    """Run mypy in ``source_root`` and return a parsed coverage snapshot."""
    with tempfile.TemporaryDirectory(prefix="rope-mypy-") as tmp:
        tmp_path = Path(tmp)
        precision_dir = tmp_path / "lineprecision"
        count_dir = tmp_path / "linecount"
        cmd = [
            sys.executable,
            "-m",
            "mypy",
            "--ignore-missing-imports",
            "--no-error-summary",
            "--no-incremental",
            "--cache-dir=/dev/null",
            "--lineprecision-report",
            str(precision_dir),
            "--linecount-report",
            str(count_dir),
            package,
        ]
        # mypy exits non-zero when type errors exist, which is expected on a
        # partially-typed codebase; we still require both report files to exist.
        proc = subprocess.run(
            cmd,
            cwd=source_root,
            capture_output=True,
            text=True,
            check=False,
        )
        precision_file = precision_dir / "lineprecision.txt"
        count_file = count_dir / "linecount.txt"
        if not precision_file.is_file() or not count_file.is_file():
            raise RuntimeError(
                f"mypy did not produce expected reports in {source_root} "
                f"(exit {proc.returncode}).\nstdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )
        return CoverageSnapshot(
            precision_by_module=parse_lineprecision(precision_file),
            funcs_by_module=parse_linecount(count_file),
        )


def load_snapshot_from_dir(report_dir: Path) -> CoverageSnapshot:
    """Load a snapshot from a directory containing ``lineprecision.txt`` and ``linecount.txt``."""
    return CoverageSnapshot(
        precision_by_module=parse_lineprecision(report_dir / "lineprecision.txt"),
        funcs_by_module=parse_linecount(report_dir / "linecount.txt"),
    )


def evaluate_policy(
    base: CoverageSnapshot,
    pr: CoverageSnapshot,
    threshold: float,
    max_drop: float,
    allow_regression: bool,
    override_label: str,
) -> PolicyEvaluation:
    """Evaluate the two-phase typing coverage policy."""
    delta_pp = pr.precision_pct - base.precision_pct
    enforced = base.precision_pct >= threshold

    if not enforced:
        return PolicyEvaluation(
            enforced=False,
            passed=True,
            bypassed=False,
            delta_pp=delta_pp,
            status_label="Informational",
            summary_line=(
                f"Informational only: base coverage ({base.precision_pct:.2f}%) "
                f"is below the {threshold:.0f}% enforcement threshold."
            ),
        )

    if delta_pp < -max_drop:
        if allow_regression:
            return PolicyEvaluation(
                enforced=True,
                passed=True,
                bypassed=True,
                delta_pp=delta_pp,
                status_label="Approved regression",
                summary_line=(
                    f"Coverage dropped by {abs(delta_pp):.2f} pp "
                    f"(exceeding {max_drop:.1f} pp), explicitly approved via "
                    f"the `{override_label}` label."
                ),
            )
        return PolicyEvaluation(
            enforced=True,
            passed=False,
            bypassed=False,
            delta_pp=delta_pp,
            status_label="Regression",
            summary_line=(
                f"Coverage dropped by {abs(delta_pp):.2f} pp "
                f"(maximum allowed without approval: {max_drop:.1f} pp). "
                f"Add type annotations or request maintainer approval with the "
                f"`{override_label}` label."
            ),
        )

    return PolicyEvaluation(
        enforced=True,
        passed=True,
        bypassed=False,
        delta_pp=delta_pp,
        status_label="Passed",
        summary_line=(
            f"Within policy ({delta_pp:+.2f} pp; maximum allowed drop without "
            f"approval is {max_drop:.1f} pp)."
        ),
    )


def _format_pp(delta: float) -> str:
    if abs(delta) < 0.005:
        return "0.00 pp"
    return f"{delta:+.2f} pp"


def _changed_modules(
    base: Mapping[str, ModulePrecision],
    pr: Mapping[str, ModulePrecision],
) -> list[tuple[str, ModulePrecision | None, ModulePrecision | None, float]]:
    rows: list[tuple[str, ModulePrecision | None, ModulePrecision | None, float]] = []
    for name in sorted(set(base) | set(pr)):
        b = base.get(name)
        p = pr.get(name)
        if b == p:
            continue
        b_pct = b.precision_pct if b is not None else 0.0
        p_pct = p.precision_pct if p is not None else 0.0
        delta = p_pct - b_pct
        rows.append((name, b, p, delta))
    rows.sort(key=lambda item: (item[3], item[0]))
    return rows


def render_markdown(
    base: CoverageSnapshot,
    pr: CoverageSnapshot,
    evaluation: PolicyEvaluation,
    threshold: float,
    max_drop: float,
    override_label: str,
    base_ref: str,
    pr_sha: str,
    max_module_rows: int = 25,
) -> str:
    """Render a concise HTML/Markdown report for PR comments and step summaries."""
    func_delta_pp = pr.annotated_funcs_pct - base.annotated_funcs_pct
    if not evaluation.passed:
        badge = "❌"
    elif evaluation.bypassed:
        badge = "⚠️"
    elif evaluation.delta_pp >= 0.005:
        badge = "✨"
    elif evaluation.delta_pp <= -0.005:
        badge = "📉"
    else:
        badge = "✅"

    progress = (
        min(100.0, 100.0 * pr.precision_pct / threshold) if threshold > 0 else 100.0
    )
    filled_blocks = round(progress / 5)
    progress_bar = "█" * filled_blocks + "░" * (20 - filled_blocks)

    escaped_base_ref = html.escape(base_ref)
    escaped_pr_sha = html.escape(pr_sha[:12]) if pr_sha else "PR"

    lines = [
        COMMENT_MARKER,
        f"### {badge} Typing Coverage Report ({evaluation.status_label})",
        "",
        evaluation.summary_line,
        "",
        "<table>",
        "  <thead>",
        "    <tr>",
        "      <th>Metric</th>",
        f"      <th>Base (<code>{escaped_base_ref}</code>)</th>",
        f"      <th>PR (<code>{escaped_pr_sha}</code>)</th>",
        "      <th>Delta</th>",
        "    </tr>",
        "  </thead>",
        "  <tbody>",
        "    <tr>",
        "      <td><strong>Precise lines</strong> (primary)</td>",
        f"      <td>{base.precision_pct:.2f}% ({base.precise_lines:,} / {base.non_empty_lines:,})</td>",
        f"      <td>{pr.precision_pct:.2f}% ({pr.precise_lines:,} / {pr.non_empty_lines:,})</td>",
        f"      <td><strong>{_format_pp(evaluation.delta_pp)}</strong></td>",
        "    </tr>",
        "    <tr>",
        "      <td>Annotated functions</td>",
        f"      <td>{base.annotated_funcs_pct:.2f}% ({base.annotated_funcs:,} / {base.total_funcs:,})</td>",
        f"      <td>{pr.annotated_funcs_pct:.2f}% ({pr.annotated_funcs:,} / {pr.total_funcs:,})</td>",
        f"      <td>{_format_pp(func_delta_pp)}</td>",
        "    </tr>",
        "  </tbody>",
        "</table>",
        "",
    ]

    if not evaluation.enforced:
        lines.append(
            f"**Progress toward {threshold:.0f}% enforcement threshold:** "
            f"`{progress_bar}` {pr.precision_pct:.2f}% / {threshold:.0f}%"
        )
        lines.append("")

    changed = _changed_modules(base.precision_by_module, pr.precision_by_module)
    if changed:
        lines.extend(
            [
                f"<details><summary>Changed modules ({len(changed)})</summary>",
                "",
                "<table>",
                "  <thead>",
                "    <tr>",
                "      <th>Module</th>",
                "      <th>Base</th>",
                "      <th>PR</th>",
                "      <th>Delta</th>",
                "    </tr>",
                "  </thead>",
                "  <tbody>",
            ]
        )
        for name, b, p, delta in changed[:max_module_rows]:
            b_cell = (
                f"{b.precision_pct:.2f}% ({b.precise}/{b.non_empty})"
                if b is not None
                else "<em>new</em>"
            )
            p_cell = (
                f"{p.precision_pct:.2f}% ({p.precise}/{p.non_empty})"
                if p is not None
                else "<em>removed</em>"
            )
            delta_cell = _format_pp(delta) if (b is not None and p is not None) else "—"
            lines.extend(
                [
                    "    <tr>",
                    f"      <td><code>{html.escape(name)}</code></td>",
                    f"      <td>{b_cell}</td>",
                    f"      <td>{p_cell}</td>",
                    f"      <td>{delta_cell}</td>",
                    "    </tr>",
                ]
            )
        lines.extend(["  </tbody>", "</table>"])
        if len(changed) > max_module_rows:
            lines.append("")
            lines.append(
                f"<em>…and {len(changed) - max_module_rows} more changed modules.</em>"
            )
        lines.extend(["</details>", ""])
    else:
        lines.append("_No per-module typing coverage changes detected._")
        lines.append("")

    lines.append(
        f"<sub>Measured with <code>mypy --lineprecision-report</code> and "
        f"<code>--linecount-report</code>. Policy: informational below "
        f"{threshold:.0f}% precise lines; above {threshold:.0f}%, drops greater "
        f"than {max_drop:.1f} pp require the <code>{html.escape(override_label)}</code> "
        f"label from a maintainer.</sub>"
    )
    return "\n".join(lines) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare mypy typing coverage between base and PR checkouts."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--base-dir",
        type=Path,
        help="Path to base branch checkout (requires --pr-dir).",
    )
    source_group.add_argument(
        "--base-report-dir",
        type=Path,
        help="Path to pre-generated base mypy report dir (requires --pr-report-dir).",
    )
    parser.add_argument(
        "--pr-dir",
        type=Path,
        help="Path to PR branch checkout (used with --base-dir).",
    )
    parser.add_argument(
        "--pr-report-dir",
        type=Path,
        help="Path to pre-generated PR mypy report dir (used with --base-report-dir).",
    )
    parser.add_argument(
        "--package",
        default="rope",
        help="Package directory to pass to mypy (default: rope).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=50.0,
        help="Enforcement threshold in percent of precise lines (default: 50.0).",
    )
    parser.add_argument(
        "--max-drop",
        type=float,
        default=5.0,
        help="Maximum allowed drop in percentage points once enforced (default: 5.0).",
    )
    parser.add_argument(
        "--allow-regression",
        action="store_true",
        help="Allow regressions exceeding --max-drop (maintainer override).",
    )
    parser.add_argument(
        "--override-label",
        default="allow-typing-regression",
        help="PR label name documented for maintainer approval.",
    )
    parser.add_argument(
        "--base-ref",
        default="master",
        help="Base branch name for display.",
    )
    parser.add_argument(
        "--pr-sha",
        default="",
        help="PR head commit SHA for display.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        help="Write the rendered Markdown/HTML report to this path.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Write structured coverage results as JSON to this path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.base_dir is not None:
        if args.pr_dir is None:
            parser.error("--pr-dir is required when --base-dir is provided")
        base_snapshot = run_mypy_snapshot(args.base_dir, args.package)
        pr_snapshot = run_mypy_snapshot(args.pr_dir, args.package)
    else:
        if args.pr_report_dir is None:
            parser.error(
                "--pr-report-dir is required when --base-report-dir is provided"
            )
        base_snapshot = load_snapshot_from_dir(args.base_report_dir)
        pr_snapshot = load_snapshot_from_dir(args.pr_report_dir)

    evaluation = evaluate_policy(
        base=base_snapshot,
        pr=pr_snapshot,
        threshold=args.threshold,
        max_drop=args.max_drop,
        allow_regression=args.allow_regression,
        override_label=args.override_label,
    )

    markdown = render_markdown(
        base=base_snapshot,
        pr=pr_snapshot,
        evaluation=evaluation,
        threshold=args.threshold,
        max_drop=args.max_drop,
        override_label=args.override_label,
        base_ref=args.base_ref,
        pr_sha=args.pr_sha,
    )

    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)

    if args.json_out is not None:
        payload = {
            "base": {
                "precise_lines": base_snapshot.precise_lines,
                "non_empty_lines": base_snapshot.non_empty_lines,
                "precision_pct": round(base_snapshot.precision_pct, 4),
                "annotated_funcs": base_snapshot.annotated_funcs,
                "total_funcs": base_snapshot.total_funcs,
                "annotated_funcs_pct": round(base_snapshot.annotated_funcs_pct, 4),
            },
            "pr": {
                "precise_lines": pr_snapshot.precise_lines,
                "non_empty_lines": pr_snapshot.non_empty_lines,
                "precision_pct": round(pr_snapshot.precision_pct, 4),
                "annotated_funcs": pr_snapshot.annotated_funcs,
                "total_funcs": pr_snapshot.total_funcs,
                "annotated_funcs_pct": round(pr_snapshot.annotated_funcs_pct, 4),
            },
            "policy": {
                "threshold": args.threshold,
                "max_drop": args.max_drop,
                "enforced": evaluation.enforced,
                "passed": evaluation.passed,
                "bypassed": evaluation.bypassed,
                "delta_pp": round(evaluation.delta_pp, 4),
                "status_label": evaluation.status_label,
            },
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return 0 if evaluation.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
