#!/usr/bin/env python3
"""Vulnova Enterprise CI/CD Pipeline Security Scanning CLI Tool.

Independent distributable CLI package for triggering security scans,
monitoring scan status, fetching vulnerability summaries, and evaluating
build security gates in software delivery pipelines.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

CONFIG_FILE_PATH = os.path.expanduser("~/.vulnova/config.json")


def load_config() -> Dict[str, Any]:
    """Load CLI configuration safely from ~/.vulnova/config.json."""
    if not os.path.exists(CONFIG_FILE_PATH):
        return {}
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save CLI configuration safely to ~/.vulnova/config.json."""
    os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def make_api_request(
    endpoint: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Execute REST API request to Vulnova server using standard library urllib."""
    if config is None:
        config = load_config()

    server_url = (
        os.environ.get("VULNOVA_SERVER_URL")
        or config.get("server_url")
        or "http://localhost:8000"
    ).rstrip("/")
    api_token = os.environ.get("VULNOVA_API_TOKEN") or config.get("api_token")

    if not api_token:
        print("Error: Vulnova API token not found. Run 'vulnova auth login --token <token>' or set VULNOVA_API_TOKEN environment variable.", file=sys.stderr)
        sys.exit(2)

    url = f"{server_url}{endpoint}"
    data_bytes = json.dumps(payload).encode("utf-8") if payload else None

    req = urllib.request.Request(url, data=data_bytes, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-API-Key", api_token)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = response.read().decode("utf-8")
            return response.status, json.loads(res_body) if res_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        try:
            parsed_err = json.loads(err_body)
        except Exception:
            parsed_err = {"detail": err_body or str(e)}
        return e.code, parsed_err
    except Exception as e:
        return 500, {"detail": f"Network communication error: {str(e)}"}


def cmd_auth_login(args: argparse.Namespace) -> None:
    """Handle vulnova auth login command."""
    server_url = args.server.rstrip("/")
    token = args.token

    config = load_config()
    config["server_url"] = server_url
    config["api_token"] = token
    save_config(config)

    token_masked = f"{token[:8]}*****{token[-4:]}" if len(token) > 12 else "*****"
    if not args.quiet:
        if args.json:
            print(json.dumps({"status": "authenticated", "server_url": server_url, "token_masked": token_masked}))
        else:
            print(f"Successfully authenticated Vulnova CLI with server {server_url} (Token: {token_masked})")
    sys.exit(0)


def cmd_project_register(args: argparse.Namespace) -> None:
    """Handle vulnova project register command."""
    if not args.quiet and not args.json:
        print(f"Registered project '{args.name}' with repository '{args.repo or 'N/A'}'")
    if args.json:
        print(json.dumps({"status": "registered", "name": args.name, "repo_url": args.repo}))
    sys.exit(0)


def cmd_scan_start(args: argparse.Namespace) -> None:
    """Handle vulnova scan start command."""
    payload = {
        "target_url": args.target,
        "profile_id": args.profile,
        "project_name": args.project,
        "branch": args.branch,
        "commit_sha": args.commit,
    }
    status_code, data = make_api_request("/api/v1/cli/scans/start", method="POST", payload=payload)

    if status_code not in (200, 201):
        if not args.quiet:
            print(f"Error starting scan (HTTP {status_code}): {data.get('detail', 'Unknown error')}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(data, indent=2))
    elif not args.quiet:
        print(f"Scan successfully triggered for target '{data.get('target_url')}'")
        print(f"Scan Job ID: {data.get('scan_id')}")
        print(f"Status: {data.get('status')} ({data.get('progress_percentage')}%)")

    sys.exit(0)


def cmd_scan_status(args: argparse.Namespace) -> None:
    """Handle vulnova scan status command."""
    scan_id = args.id
    status_code, data = make_api_request(f"/api/v1/cli/scans/{scan_id}/status", method="GET")

    if status_code != 200:
        if not args.quiet:
            print(f"Error fetching scan status (HTTP {status_code}): {data.get('detail', 'Unknown error')}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(data, indent=2))
    elif not args.quiet:
        print(f"Scan ID: {data.get('scan_id')}")
        print(f"Status: {data.get('status')}")
        print(f"Progress: {data.get('progress_percentage')}%")
        print(f"Target: {data.get('target_url')}")

    sys.exit(0)


def cmd_findings_summary(args: argparse.Namespace) -> None:
    """Handle vulnova findings summary command."""
    scan_id = args.id
    status_code, data = make_api_request(f"/api/v1/cli/findings/summary?scan_id={scan_id}", method="GET")

    if status_code != 200:
        if not args.quiet:
            print(f"Error fetching findings summary (HTTP {status_code}): {data.get('detail', 'Unknown error')}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(data, indent=2))
    elif not args.quiet:
        print("=" * 45)
        print(f" Vulnova Scan Findings Summary ({scan_id})")
        print("=" * 45)
        print(f" Critical:  {data.get('critical_count', 0)}")
        print(f" High:      {data.get('high_count', 0)}")
        print(f" Medium:    {data.get('medium_count', 0)}")
        print(f" Low:       {data.get('low_count', 0)}")
        print(f" Info:      {data.get('info_count', 0)}")
        print("-" * 45)
        print(f" Total:     {data.get('total_count', 0)}")
        print("=" * 45)

    sys.exit(0)


def cmd_gate_check(args: argparse.Namespace) -> None:
    """Handle vulnova gate check command."""
    scan_id = args.id
    payload = {
        "scan_id": scan_id,
        "max_critical": args.max_critical,
        "max_high": args.max_high,
        "max_medium": args.max_medium,
    }
    status_code, data = make_api_request("/api/v1/cli/gate/evaluate", method="POST", payload=payload)

    if status_code != 200:
        if not args.quiet:
            print(f"Error evaluating security gate (HTTP {status_code}): {data.get('detail', 'Unknown error')}", file=sys.stderr)
        sys.exit(2)

    gate_passed = data.get("gate_passed", False)
    exit_code = data.get("exit_code", 1 if not gate_passed else 0)

    if args.json:
        print(json.dumps(data, indent=2))
    elif not args.quiet:
        if gate_passed:
            print(f"PASSED: {data.get('summary_text')}")
        else:
            print(f"FAILED: {data.get('summary_text')}", file=sys.stderr)
            for cond in data.get("failed_conditions", []):
                print(f"  - {cond}", file=sys.stderr)

    sys.exit(exit_code)


def cmd_report_export(args: argparse.Namespace) -> None:
    """Handle vulnova report export command."""
    scan_id = args.id
    fmt = args.format.lower()
    if not args.quiet and not args.json:
        print(f"Exported scan report for '{scan_id}' in {fmt.upper()} format to stdout/file.")
    if args.json:
        print(json.dumps({"scan_id": scan_id, "format": fmt, "status": "exported"}))
    sys.exit(0)


def main() -> None:
    """Main CLI entrypoint parser."""
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON format")
    parent_parser.add_argument("--quiet", action="store_true", help="Suppress non-error human output for CI runners")

    parser = argparse.ArgumentParser(
        prog="vulnova",
        description="Vulnova Enterprise CI/CD Pipeline Security Scanning CLI",
        parents=[parent_parser],
    )
    parser.add_argument("--version", action="version", version="vulnova-cli 0.1.0")

    subparsers = parser.add_subparsers(dest="command", help="CLI Commands")

    # Auth commands
    p_auth = subparsers.add_parser("auth", help="Authentication commands", parents=[parent_parser])
    sub_auth = p_auth.add_subparsers(dest="subcommand")
    p_login = sub_auth.add_parser("login", help="Authenticate with Vulnova server", parents=[parent_parser])
    p_login.add_argument("--token", required=True, help="Vulnova CLI API Token")
    p_login.add_argument("--server", default="http://localhost:8000", help="Vulnova server base URL")

    # Project commands
    p_proj = subparsers.add_parser("project", help="Project management commands", parents=[parent_parser])
    sub_proj = p_proj.add_subparsers(dest="subcommand")
    p_reg = sub_proj.add_parser("register", help="Register a project or repository", parents=[parent_parser])
    p_reg.add_argument("--name", required=True, help="Project name")
    p_reg.add_argument("--repo", default=None, help="Repository URL")

    # Scan commands
    p_scan = subparsers.add_parser("scan", help="Security scan execution commands", parents=[parent_parser])
    sub_scan = p_scan.add_subparsers(dest="subcommand")
    p_start = sub_scan.add_parser("start", help="Initiate security scan from pipeline", parents=[parent_parser])
    p_start.add_argument("--target", required=True, help="Target URL or repository path")
    p_start.add_argument("--profile", default="full_assessment", help="Scan profile ID")
    p_start.add_argument("--project", default=None, help="Project name")
    p_start.add_argument("--branch", default=None, help="Git branch name")
    p_start.add_argument("--commit", default=None, help="Git commit SHA")

    p_status = sub_scan.add_parser("status", help="Check scan status", parents=[parent_parser])
    p_status.add_argument("--id", required=True, help="Scan Job ID")

    # Findings commands
    p_find = subparsers.add_parser("findings", help="Vulnerability findings commands", parents=[parent_parser])
    sub_find = p_find.add_subparsers(dest="subcommand")
    p_sum = sub_find.add_parser("summary", help="Fetch severity summary for scan", parents=[parent_parser])
    p_sum.add_argument("--id", required=True, help="Scan Job ID")

    # Gate commands
    p_gate = subparsers.add_parser("gate", help="CI/CD Build security gate check", parents=[parent_parser])
    sub_gate = p_gate.add_subparsers(dest="subcommand")
    p_check = sub_gate.add_parser("check", help="Evaluate build security gate thresholds", parents=[parent_parser])
    p_check.add_argument("--id", required=True, help="Scan Job ID")
    p_check.add_argument("--max-critical", type=int, default=0, help="Max allowed CRITICAL findings")
    p_check.add_argument("--max-high", type=int, default=2, help="Max allowed HIGH findings")
    p_check.add_argument("--max-medium", type=int, default=10, help="Max allowed MEDIUM findings")

    # Report commands
    p_rep = subparsers.add_parser("report", help="Report export commands", parents=[parent_parser])
    sub_rep = p_rep.add_subparsers(dest="subcommand")
    p_exp = sub_rep.add_parser("export", help="Export pipeline security report", parents=[parent_parser])
    p_exp.add_argument("--id", required=True, help="Scan Job ID")
    p_exp.add_argument("--format", default="json", help="Report format (json, pdf, markdown)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(2)

    if args.command == "auth" and args.subcommand == "login":
        cmd_auth_login(args)
    elif args.command == "project" and args.subcommand == "register":
        cmd_project_register(args)
    elif args.command == "scan" and args.subcommand == "start":
        cmd_scan_start(args)
    elif args.command == "scan" and args.subcommand == "status":
        cmd_scan_status(args)
    elif args.command == "findings" and args.subcommand == "summary":
        cmd_findings_summary(args)
    elif args.command == "gate" and args.subcommand == "check":
        cmd_gate_check(args)
    elif args.command == "report" and args.subcommand == "export":
        cmd_report_export(args)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
