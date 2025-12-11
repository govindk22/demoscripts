"""
veracode_client.py
Simple Veracode REST client that:
 - lists applications
 - fetches findings for an application and computes high/medium open counts
 - renders an HTML report of open flaws (Jinja2)

Requirements:
 pip install requests jinja2 veracode-api-signing

Note: store API credentials safely. This example expects environment variables
VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET or you can pass them explicitly.
"""

import os
import math
import requests
from typing import List, Dict, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from dataclasses import dataclass
from datetime import datetime

# Import the Veracode requests plugin (from veracode-api-signing package).
# If the package exposes a different import path in your environment, adjust accordingly.
try:
    from veracode_api_signing.plugin_requests import RequestsAuthPluginVeracodeHMAC
except Exception as e:
    raise ImportError(
        "veracode-api-signing plugin not available. Install with: pip install veracode-api-signing"
    ) from e


DEFAULT_API_BASE = "https://api.veracode.com"  # Commercial region - change if needed


@dataclass
class FlawSummary:
    id: str
    cwe_id: Optional[int]
    severity: str
    title: Optional[str]
    status: Optional[str]
    mitigation_status: Optional[str]
    module: Optional[str]
    file_name: Optional[str]
    path: Optional[str]
    line_number: Optional[int]
    created_date: Optional[str]
    updated_date: Optional[str]
    description: Optional[str]


class VeracodeClient:
    def __init__(
        self,
        api_key_id: Optional[str] = None,
        api_key_secret: Optional[str] = None,
        base_url: str = DEFAULT_API_BASE,
        session: Optional[requests.Session] = None,
    ):
        self.api_key_id = api_key_id or os.environ.get("VERACODE_API_KEY_ID")
        self.api_key_secret = api_key_secret or os.environ.get("VERACODE_API_KEY_SECRET")
        if not self.api_key_id or not self.api_key_secret:
            raise ValueError("Provide VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET (or pass them).")

        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        # Install the HMAC plugin on the session
        self.session.auth = RequestsAuthPluginVeracodeHMAC(
            api_key_id=self.api_key_id, api_key_secret=self.api_key_secret
        )

    # -------------------------
    # Applications API helpers
    # -------------------------
    def list_applications(self, page: int = 0, size: int = 50) -> Dict:
        """
        Return a page of applications (JSON).
        See: GET /appsec/v1/applications/?page=0&size=50
        """
        url = f"{self.base_url}/appsec/v1/applications/"
        params = {"page": page, "size": size}
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def find_application_by_name(self, name: str) -> Optional[Dict]:
        """
        Return the first application whose name contains the provided string (case-insensitive).
        Uses listing-by-name query if available.
        """
        url = f"{self.base_url}/appsec/v1/applications/"
        params = {"name": name, "size": 50}
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("applications") or data.get("content") or data.get("appProfiles") or []
        # Best-effort normalization
        for app in items:
            app_name = app.get("name") or app.get("application_name") or app.get("app_name")
            if app_name and name.lower() in app_name.lower():
                return app
        return None

    # -------------------------
    # Findings API helpers
    # -------------------------
    def get_findings(
        self,
        application_guid: str,
        scan_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 0,
        size: int = 200,
    ) -> List[Dict]:
        """
        Query the Findings API for the given application GUID.
        Endpoint (example): GET /appsec/v2/applications/{application_guid}/findings
        Supports pagination (page, size). Returns aggregated list (one page by default).
        You can call repeatedly with page increments to fetch more pages.
        """
        url = f"{self.base_url}/appsec/v2/applications/{application_guid}/findings"
        params = {"page": page, "size": size}
        if scan_type:
            params["scan_type"] = scan_type
        if status:
            params["status"] = status  # e.g. 'OPEN' - API may accept different values; adjust if needed.
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        j = resp.json()
        # Findings may be in j.get("findings") or j.get("data")
        if isinstance(j, dict):
            if "findings" in j:
                return j["findings"]
            if "data" in j:
                return j["data"]
            # fallback: search for list values
            for v in j.values():
                if isinstance(v, list):
                    return v
        if isinstance(j, list):
            return j
        return []

    def get_all_findings(
        self,
        application_guid: str,
        scan_type: Optional[str] = None,
        status: Optional[str] = None,
        max_pages: int = 50,
        page_size: int = 200,
    ) -> List[Dict]:
        """
        Paginate through findings pages until no results or until max_pages reached.
        """
        all_findings = []
        page = 0
        while page < max_pages:
            findings = self.get_findings(application_guid, scan_type=scan_type, status=status, page=page, size=page_size)
            if not findings:
                break
            all_findings.extend(findings)
            if len(findings) < page_size:
                break
            page += 1
        return all_findings

    # -------------------------
    # Reporting helpers
    # -------------------------
    @staticmethod
    def summarize_findings(findings: List[Dict]) -> Dict[str, int]:
        """
        Count High and Medium severities among findings that appear 'open'.
        This mapping depends on the API's fields; we try common keys.
        """
        high = 0
        medium = 0
        for f in findings:
            # severity may be int or string; common string values: "HIGH", "MEDIUM", "LOW"
            sev = f.get("severity") or f.get("severity_name") or f.get("severity_text") or f.get("impact") or ""
            # normalize severity to uppercase string
            sev_str = str(sev).upper() if sev is not None else ""
            # status/mittigation: try to filter out fixed/mitigated items
            status = f.get("status") or f.get("finding_status") or f.get("remediation_status") or ""
            status_str = str(status).upper() if status is not None else ""
            is_open = "FIXED" not in status_str and "MITIGATED" not in status_str and "FALSE" not in status_str
            if is_open:
                if "HIGH" in sev_str or sev_str in ("4", "CRITICAL", "CRIT"):
                    high += 1
                elif "MED" in sev_str or sev_str == "3":
                    medium += 1
        return {"high": high, "medium": medium, "total_open": high + medium}

    def make_flaw_summary(self, finding: Dict) -> FlawSummary:
        """
        Convert raw finding to FlawSummary dataclass (best-effort mapping).
        """
        return FlawSummary(
            id = finding.get("id") or finding.get("finding_id") or str(finding.get("guid") or ""),
            cwe_id = finding.get("cwe") or finding.get("cwe_id"),
            severity = str(finding.get("severity") or finding.get("severity_name") or ""),
            title = finding.get("title") or finding.get("issue_name") or finding.get("finding_name"),
            status = finding.get("status") or finding.get("finding_status"),
            mitigation_status = finding.get("remediation_status") or finding.get("mitigated"),
            module = finding.get("module") or finding.get("component") or finding.get("library"),
            file_name = finding.get("file_name") or finding.get("file"),
            path = finding.get("path"),
            line_number = finding.get("line_number") or finding.get("line"),
            created_date = finding.get("date_created") or finding.get("created_date"),
            updated_date = finding.get("date_updated") or finding.get("updated_date"),
            description = finding.get("description") or finding.get("analysis"),
        )

    def generate_html_report(
        self,
        application_guid: str,
        application_name: str,
        output_path: str = "veracode_report.html",
        scan_type: Optional[str] = None,
        status: Optional[str] = "OPEN",
        page_size: int = 200,
    ) -> Dict:
        """
        Build an HTML report for an application showing open flaws and High/Medium counts.
        Returns a dict with report path and summary.
        """
        findings = self.get_all_findings(application_guid, scan_type=scan_type, status=status, page_size=page_size)
        summary = self.summarize_findings(findings)
        # Convert to FlawSummary list for templating
        flaw_summaries = [self.make_flaw_summary(f) for f in findings]

        # Jinja template (inline for convenience). You can load from a separate file if preferred.
        template_str = """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8"/>
          <title>Veracode Report - {{ application_name }}</title>
          <style>
            body { font-family: Arial, Helvetica, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background: #f2f2f2; }
            .metrics { margin-bottom: 20px; }
            .badge { padding: 6px 10px; border-radius: 4px; color: white; display: inline-block; }
            .high { background: #c0392b; }
            .medium { background: #f39c12; }
          </style>
        </head>
        <body>
          <h1>Veracode Report: {{ application_name }}</h1>
          <div class="metrics">
            <strong>Generated:</strong> {{ generated_at }}<br/>
            <strong>Application GUID:</strong> {{ application_guid }}<br/>
            <div>
              <span class="badge high">High: {{ summary.high }}</span>
              <span class="badge medium">Medium: {{ summary.medium }}</span>
              <span style="margin-left:10px"><strong>Total (High+Medium open):</strong> {{ summary.total_open }}</span>
            </div>
          </div>

          <h2>Open Flaws (first {{ flaws|length }} shown)</h2>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Severity</th>
                <th>Title</th>
                <th>CWE</th>
                <th>Status</th>
                <th>File</th>
                <th>Line</th>
                <th>Created</th>
                <th>Description (short)</th>
              </tr>
            </thead>
            <tbody>
            {% for f in flaws %}
              <tr>
                <td>{{ f.id }}</td>
                <td>{{ f.severity }}</td>
                <td>{{ f.title or '-' }}</td>
                <td>{{ f.cwe_id or '-' }}</td>
                <td>{{ f.status or '-' }}</td>
                <td>{{ f.file_name or f.path or '-' }}</td>
                <td>{{ f.line_number or '-' }}</td>
                <td>{{ f.created_date or '-' }}</td>
                <td>{{ (f.description[:250] + '...') if f.description and f.description|length > 250 else (f.description or '-') }}</td>
              </tr>
            {% endfor %}
            </tbody>
          </table>

          <p>Report generated by VeracodeClient at {{ generated_at }}.</p>
        </body>
        </html>
        """

        env = Environment(autoescape=select_autoescape(["html", "xml"]))
        template = env.from_string(template_str)
        rendered = template.render(
            application_name=application_name,
            application_guid=application_guid,
            summary=summary,
            flaws=flaw_summaries,
            generated_at=datetime.utcnow().isoformat() + "Z",
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        return {"report_path": output_path, "summary": summary, "flaws_count": len(flaw_summaries)}

# -------------------------
# Simple CLI usage example
# -------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Veracode quick report generator")
    parser.add_argument("--app-name", required=True, help="Application name to search for (partial match)")
    parser.add_argument("--out", default="veracode_report.html", help="HTML output path")
    parser.add_argument("--api-id", default=None, help="Veracode API Key ID")
    parser.add_argument("--api-secret", default=None, help="Veracode API Key Secret")
    args = parser.parse_args()

    client = VeracodeClient(api_key_id=args.api_id, api_key_secret=args.api_secret)
    app = client.find_application_by_name(args.app_name)
    if not app:
        print(f"Application with name containing '{args.app_name}' not found.")
        exit(2)

    # Try to extract the GUID (varies by response shape)
    guid = app.get("guid") or app.get("application_guid") or app.get("id") or app.get("resource_id")
    app_name = app.get("name") or app.get("application_name") or args.app_name
    if not guid:
        print("Could not determine application GUID from API response; inspect the application JSON:")
        print(app)
        exit(3)

    print(f"Found application: {app_name} (GUID: {guid})")
    result = client.generate_html_report(application_guid=guid, application_name=app_name, output_path=args.out)
    print("Report written to:", result["report_path"])
    print("Summary:", result["summary"])
