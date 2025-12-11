    def list_applications_with_metrics(
        self,
        name_filter: Optional[str] = None,
        page: int = 0,
        size: int = 50,
        find_last_prod_ci: bool = True,
        sandbox_search_name: str = "prod_ci",
    ) -> List[Dict]:
        """
        Return a list of applications with:
          - GUID, name
          - counts of open findings by severity (high, medium, low)
          - info about sandbox matching `sandbox_search_name` (if present): sandbox GUID, latest build/scan status,
            policy promotion date/status if available.
        This is best-effort: API response shapes vary, so the code probes for common fields.
        """
        apps_page = self.list_applications(page=page, size=size)
        # attempt to find the list in common properties
        items = apps_page.get("applications") or apps_page.get("content") or apps_page.get("appProfiles") or apps_page.get("data") or []
        results = []

        for app in items:
            app_guid = app.get("guid") or app.get("application_guid") or app.get("id") or app.get("resource_id")
            app_name = app.get("name") or app.get("application_name") or app.get("app_name") or app.get("display_name")
            if name_filter and app_name and name_filter.lower() not in app_name.lower():
                continue

            entry = {
                "guid": app_guid,
                "name": app_name,
                "raw_app": app,
                "finding_counts": {"high": 0, "medium": 0, "low": 0, "total_open": 0},
                "prod_ci_sandbox": None,
            }

            # --- findings counts (open only) ---
            if app_guid:
                # fetch all findings for app (may be heavy; adjust page_size / max_pages if needed)
                try:
                    findings = self.get_all_findings(application_guid=app_guid, status="OPEN", page_size=200, max_pages=20)
                except Exception:
                    findings = []

                counts = {"high": 0, "medium": 0, "low": 0}
                for f in findings:
                    sev = f.get("severity") or f.get("severity_name") or f.get("impact") or ""
                    sev_str = str(sev).upper() if sev is not None else ""
                    # normalization heuristics
                    if "CRIT" in sev_str or "HIGH" in sev_str or sev_str in ("4", "5"):
                        counts["high"] += 1
                    elif "MED" in sev_str or sev_str in ("3",):
                        counts["medium"] += 1
                    else:
                        counts["low"] += 1
                entry["finding_counts"] = {"high": counts["high"], "medium": counts["medium"], "low": counts["low"], "total_open": counts["high"] + counts["medium"] + counts["low"]}

            # --- sandbox / prod_ci info ---
            if find_last_prod_ci and app_guid:
                try:
                    sb_url = f"{self.base_url}/appsec/v1/applications/{app_guid}/sandboxes"
                    resp = self.session.get(sb_url)
                    resp.raise_for_status()
                    sbj = resp.json()
                    sandboxes = sbj.get("sandboxes") or sbj.get("data") or sbj or []
                    # normalize to list
                    if isinstance(sandboxes, dict):
                        # maybe single sandbox object
                        sandboxes = [sandboxes]
                except Exception:
                    sandboxes = []

                # find sandbox with name containing sandbox_search_name (case-insensitive)
                chosen = None
                for s in sandboxes:
                    sname = s.get("name") or s.get("sandbox_name") or s.get("display_name") or ""
                    if sname and sandbox_search_name.lower() in sname.lower():
                        chosen = s
                        break
                # fallback: if none found, pick sandbox with exact name or first sandbox
                if not chosen and sandboxes:
                    # try exact match
                    for s in sandboxes:
                        sname = s.get("name") or s.get("sandbox_name") or ""
                        if sname and sname.lower() == sandbox_search_name.lower():
                            chosen = s
                            break
                if not chosen and sandboxes:
                    chosen = sandboxes[0]

                if chosen:
                    sandbox_guid = chosen.get("guid") or chosen.get("sandbox_guid") or chosen.get("id") or chosen.get("sandbox_id")
                    prod_info = {"sandbox": chosen, "sandbox_guid": sandbox_guid, "latest_build": None, "promotion": None}
                    # Try to read common fields that may indicate last build/scan or promotion
                    # Many sandbox objects include 'latest_build' or 'last_scan' fields; probe them:
                    for candidate in ("latest_build", "last_build", "last_scan", "latest_scan", "most_recent_build"):
                        if candidate in chosen:
                            prod_info["latest_build"] = chosen.get(candidate)
                            break

                    # Some APIs return a 'last_policy_evaluation' or 'policy_promotion' fields on app or sandbox:
                    for candidate in ("last_policy_evaluation", "last_policy_evaluation_date", "policy_promotion_date", "promoted_at", "promotion_date"):
                        if candidate in chosen:
                            prod_info["promotion"] = chosen.get(candidate)
                            break
                    # If latest_build is still None, attempt to list builds for the sandbox (best-effort)
                    if not prod_info["latest_build"] and sandbox_guid:
                        try:
                            builds_url = f"{self.base_url}/appsec/v1/applications/{app_guid}/sandboxes/{sandbox_guid}/builds"
                            r = self.session.get(builds_url, params={"size": 1, "page": 0})
                            r.raise_for_status()
                            bj = r.json()
                            # Many build list responses contain 'builds' or 'data'
                            builds = bj.get("builds") or bj.get("data") or bj or []
                            if isinstance(builds, dict):
                                # single object -> wrap
                                builds = [builds]
                            if builds:
                                # take the most recent (assume returned sorted by date desc)
                                prod_info["latest_build"] = builds[0]
                        except Exception:
                            pass

                    entry["prod_ci_sandbox"] = prod_info

            results.append(entry)

        return results


    def promote_last_prod_ci_scan(
        self,
        application_guid: str,
        sandbox_search_name: str = "prod_ci",
        delete_on_promote: bool = False,
    ) -> Dict:
        """
        Promote the latest sandbox scan for the sandbox that matches `sandbox_search_name`
        to be the policy scan. Returns parsed JSON from the promote endpoint or raises an error.

        POST /appsec/v1/applications/{applicationGuid}/sandboxes/{sandboxGuid}/promote
        (optionally ?delete_on_promote=true)
        """
        # 1) get sandboxes for the application
        sb_url = f"{self.base_url}/appsec/v1/applications/{application_guid}/sandboxes"
        resp = self.session.get(sb_url)
        resp.raise_for_status()
        sbj = resp.json()
        sandboxes = sbj.get("sandboxes") or sbj.get("data") or sbj or []
        if isinstance(sandboxes, dict):
            sandboxes = [sandboxes]

        chosen = None
        for s in sandboxes:
            sname = s.get("name") or s.get("sandbox_name") or ""
            if sname and sandbox_search_name.lower() in sname.lower():
                chosen = s
                break
        if not chosen and sandboxes:
            # try exact match
            for s in sandboxes:
                sname = s.get("name") or s.get("sandbox_name") or ""
                if sname and sname.lower() == sandbox_search_name.lower():
                    chosen = s
                    break
        if not chosen:
            raise ValueError(f"No sandbox matching '{sandbox_search_name}' found for application {application_guid}")

        sandbox_guid = chosen.get("guid") or chosen.get("sandbox_guid") or chosen.get("id") or chosen.get("sandbox_id")
        if not sandbox_guid:
            raise ValueError("Could not determine sandbox GUID for chosen sandbox (inspect sandbox object).")

        # Promote endpoint
        promote_url = f"{self.base_url}/appsec/v1/applications/{application_guid}/sandboxes/{sandbox_guid}/promote"
        params = {}
        if delete_on_promote:
            params["delete_on_promote"] = "true"
        post_resp = self.session.post(promote_url, params=params)
        # If Veracode returns 202 or 200, parse JSON (some endpoints may return no body)
        post_resp.raise_for_status()
        try:
            return post_resp.json()
        except ValueError:
            # no JSON returned; return status info
            return {"status_code": post_resp.status_code, "text": post_resp.text}
