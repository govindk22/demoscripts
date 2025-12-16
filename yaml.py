import subprocess
import yaml
import os
import json

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def export_helm_deployments(
    namespace,
    output_dir="helm_backup"
):
    """
    Export Helm-managed OpenShift objects to YAML files.

    :param namespace: OpenShift namespace
    :param output_dir: Directory to store backups
    """

    os.makedirs(output_dir, exist_ok=True)

    # Find Helm releases via secrets
    secrets_json = run(
        f"oc get secrets -n {namespace} "
        "-l owner=helm -o json"
    )
    secrets = json.loads(secrets_json)

    releases = set()
    for s in secrets["items"]:
        name = s["metadata"]["name"]
        # Format: sh.helm.release.v1.<release>.vX
        parts = name.split(".")
        if len(parts) >= 5:
            releases.add(parts[4])

    print(f"Found Helm releases: {', '.join(releases)}")

    for release in releases:
        print(f"Exporting release: {release}")

        # Get all resources labeled with this release
        resources_yaml = run(
            f"oc get all,cm,secret,ingress,route,svc,sa,role,rolebinding "
            f"-n {namespace} "
            f"-l app.kubernetes.io/instance={release} "
            f"-o yaml"
        )

        data = yaml.safe_load(resources_yaml)

        if not data or "items" not in data or len(data["items"]) == 0:
            print(f"⚠️ No objects found for release {release}")
            continue

        file_path = os.path.join(
            output_dir,
            f"{release}.yaml"
        )

        with open(file_path, "w") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                sort_keys=False
            )

        print(f"✔ Saved {file_path}")
