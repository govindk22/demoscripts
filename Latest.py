import requests

def get_last_build_for_branch(
    gitlab_url,
    project_id,
    branch,
    private_token,
    job_name=None
):
    headers = {"PRIVATE-TOKEN": private_token}

    # 1. Get latest pipeline
    pipelines_url = f"{gitlab_url}/api/v4/projects/{project_id}/pipelines"
    pipelines = requests.get(
        pipelines_url,
        headers=headers,
        params={"ref": branch, "per_page": 1}
    ).json()

    if not pipelines:
        return None

    pipeline_id = pipelines[0]["id"]

    # 2. Get jobs for pipeline
    jobs_url = f"{gitlab_url}/api/v4/projects/{project_id}/pipelines/{pipeline_id}/jobs"
    jobs = requests.get(jobs_url, headers=headers).json()

    if job_name:
        jobs = [j for j in jobs if j["name"] == job_name]

    # 3. Return latest job
    return jobs[0] if jobs else None
