#!/usr/bin/env python3
"""
learn_from_prs.py - Analyze PR history via GitHub API to extract patterns, bugs, conflicts,
and update coding rubric rules automatically.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from collections import defaultdict
import urllib.request
import urllib.error


def fetch_github_api(url: str, token: str = None):
    """Perform GitHub API GET request and return parsed JSON."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "PR-Learnings-Script")
    if token:
        req.add_header("Authorization", f"token {token}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def analyze_pull_requests(repo: str, token: str = None):
    """Fetch and categorize all pull requests for the repository."""
    url = f"https://api.github.com/repos/{repo}/pulls?state=all&per_page=100"
    prs = fetch_github_api(url, token)

    conflict_files = defaultdict(int)
    last_conflict_date = {}
    feature_files = defaultdict(lambda: {"files": set(), "count": 0})
    bug_patterns = defaultdict(lambda: {"count": 0, "fix": ""})
    derived_rules = []

    for pr in prs:
        title = pr.get("title", "")
        body = pr.get("body", "") or ""
        number = pr.get("number")
        created_at = (pr.get("created_at") or "")[:10]
        merged_at = pr.get("merged_at")
        state = pr.get("state")
        mergeable_state = pr.get("mergeable_state", "")

        files_url = pr.get("url", "") + "/files"
        try:
            files_data = fetch_github_api(files_url, token)
            files_changed = [f.get("filename") for f in files_data if f.get("filename")]
        except Exception:
            files_changed = []

        has_conflict = mergeable_state == "dirty" or "conflict" in body.lower() or "conflict" in title.lower()
        if has_conflict:
            for f in files_changed:
                conflict_files[f] += 1
                last_conflict_date[f] = created_at

        if "fix:" in title.lower() or "fix" in title.lower() or "bug" in title.lower():
            pattern_name = title.split(":")[-1].strip() if ":" in title else title
            bug_patterns[pattern_name]["count"] += 1
            bug_patterns[pattern_name]["fix"] = f"PR #{number}: {title}"
            derived_rules.append({
                "rule": f"Prevent regression: {pattern_name}",
                "derived_from": f"PR #{number} ({title})",
                "category": "Reliability"
            })

        if "feat:" in title.lower() or "feat" in title.lower() or "add" in title.lower():
            feat_name = title.split(":")[-1].strip() if ":" in title else title
            feature_files[feat_name]["count"] += 1
            for f in files_changed:
                feature_files[feat_name]["files"].add(f)

        if state == "closed" and not merged_at:
            derived_rules.append({
                "rule": f"Avoid rejected pattern from PR #{number}: {title}",
                "derived_from": f"PR #{number} ({title})",
                "category": "Architecture"
            })

    return {
        "conflict_files": conflict_files,
        "last_conflict_date": last_conflict_date,
        "feature_files": feature_files,
        "bug_patterns": bug_patterns,
        "derived_rules": derived_rules
    }


def generate_learnings_markdown(data: dict) -> str:
    """Generate Markdown report from PR analysis data."""
    lines = [
        "# PR Learnings — Auto-generated",
        "",
        "## Frequently conflicting files",
        "| File | Conflict count | Last conflict |",
        "|------|---------------|---------------|",
    ]
    if data["conflict_files"]:
        for f, count in sorted(data["conflict_files"].items(), key=lambda x: x[1], reverse=True):
            last_date = data["last_conflict_date"].get(f, "N/A")
            lines.append(f"| {f} | {count} | {last_date} |")
    else:
        lines.append("| (none detected) | 0 | - |")

    lines.extend([
        "",
        "## Features and their files",
        "| Feature | Files touched | PR count |",
        "|---------|--------------|----------|",
    ])
    if data["feature_files"]:
        for feat, info in sorted(data["feature_files"].items(), key=lambda x: x[1]["count"], reverse=True):
            files_str = ", ".join(sorted(info["files"])[:3])
            if len(info["files"]) > 3:
                files_str += f" (+{len(info['files'])-3} more)"
            lines.append(f"| {feat[:50]} | {files_str or 'N/A'} | {info['count']} |")
    else:
        lines.append("| (none detected) | - | 0 |")

    lines.extend([
        "",
        "## Common bug patterns",
        "| Pattern | Occurrences | Fix applied |",
        "|---------|-------------|-------------|",
    ])
    if data["bug_patterns"]:
        for pat, info in sorted(data["bug_patterns"].items(), key=lambda x: x[1]["count"], reverse=True):
            lines.append(f"| {pat[:50]} | {info['count']} | {info['fix'][:50]} |")
    else:
        lines.append("| (none detected) | 0 | - |")

    lines.extend([
        "",
        "## Rubric rules derived from PR history",
        "| Rule | Derived from PR | Category |",
        "|------|----------------|----------|",
    ])
    if data["derived_rules"]:
        for r in data["derived_rules"][:10]:
            lines.append(f"| {r['rule'][:60]} | {r['derived_from'][:40]} | {r['category']} |")
    else:
        lines.append("| (none derived) | - | - |")

    lines.append("")
    return "\n".join(lines)


def update_rubric_with_rules(derived_rules: list, rubric_path: str = "docs/CODING_RUBRIC.md"):
    """Append any new rules not already in CODING_RUBRIC.md."""
    if not os.path.exists(rubric_path) or not derived_rules:
        return

    with open(rubric_path, "r") as f:
        content = f.read()

    new_rules_to_add = []
    today_str = datetime.now().strftime("%Y-%m-%d")

    for r in derived_rules:
        rule_text = r["rule"]
        derived_from = r["derived_from"]
        if rule_text not in content:
            new_rules_to_add.append((rule_text, derived_from))

    if new_rules_to_add:
        addition = ["\n## Derived Rules from PR History\n"]
        for rule_text, derived_from in new_rules_to_add:
            addition.append(f"# Derived from PR history {today_str}: {derived_from}")
            addition.append(f"- {rule_text}\n")

        with open(rubric_path, "a") as f:
            f.write("\n".join(addition))


def main():
    """CLI Entry point."""
    parser = argparse.ArgumentParser(description="Analyze GitHub PRs and update coding rubric.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPO", "parth33320/sovereign-supply-chain-meta"),
                        help="GitHub repository (owner/repo)")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"),
                        help="GitHub personal access token")
    parser.add_argument("--output", default="docs/decisions/pr-learnings.md",
                        help="Output path for pr-learnings.md")
    parser.add_argument("--rubric", default="docs/CODING_RUBRIC.md",
                        help="Path to CODING_RUBRIC.md")

    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")
    repo = args.repo

    print(f"Fetching PRs from GitHub repo: {repo}...")
    try:
        data = analyze_pull_requests(repo, token)
        md = generate_learnings_markdown(data)
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            f.write(md)
        print(f"Wrote PR learnings to {args.output}")

        if data["derived_rules"]:
            update_rubric_with_rules(data["derived_rules"], args.rubric)
            print(f"Updated {args.rubric} with {len(data['derived_rules'])} derived rules.")
    except Exception as e:
        print(f"Error analyzing PRs: {e}", file=sys.stderr)
        if not os.path.exists(args.output):
            empty_data = {
                "conflict_files": {},
                "last_conflict_date": {},
                "feature_files": {},
                "bug_patterns": {},
                "derived_rules": []
            }
            with open(args.output, "w") as f:
                f.write(generate_learnings_markdown(empty_data))
            print(f"Created initial placeholder {args.output}")


if __name__ == "__main__":
    main()
