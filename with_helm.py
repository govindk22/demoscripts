#!/usr/bin/env python3
import os
import yaml
import subprocess
import json
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

CLUSTERS_DIR = "clusters"
TEMPLATE_DIR = "templates"
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_oc(cmd, namespace=None):
    """Run oc CLI command and return JSON output."""
    base_cmd = ["oc"] + cmd
    if namespace:
        base_cmd.extend(["-n", namespace])
    try:
        result = subprocess.check_output(base_cmd, text=True)
        return json.loads(result)
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(base_cmd)} -> {e}")
        return {}


def switch_cluster(cluster_url):
    """Login to OpenShift cluster."""
    print(f"🔐 Switching to cluster: {cluster_url}")
    try:
        subprocess.run(["oc", "login", cluster_url, "--token", os.getenv("OC_TOKEN")], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to login to {cluster_url}: {e}")


def install_helm_package(release_name, chart_name, namespace, values_file=None):
    """
    Install or upgrade a Helm release in the given namespace.
    """
    print(f"🚀 Installing Helm release '{release_name}' using chart '{chart_name}' in ns '{namespace}'")

    cmd = ["helm", "upgrade", "--install", release_name, chart_name, "-n", namespace]
    if values_file and os.path.exists(values_file):
        cmd.extend(["-f", values_file])
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Helm install/upgrade succeeded for {release_name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Helm install failed for {release_name}: {e}")


def get_deployments(namespace):
    data = run_oc(["get", "deployments", "-o", "json"], namespace)
    deployments = []
    for item in data.get("items", []):
        metadata = item["metadata"]
        spec = item["spec"]
        deployments.append({
            "type": "deployment",
            "name": metadata["name"],
            "namespace": metadata["namespace"],
            "replicas": spec.get("replicas", 0),
            "images": [c["image"] for c in spec["template"]["spec"]["containers"]],
        })
    return deployments


def get_jobs(namespace):
    data = run_oc(["get", "jobs", "-o", "json"], namespace)
    jobs = []
    for item in data.get("items", []):
        metadata = item["metadata"]
        jobs.append({
            "type": "job",
            "name": metadata["name"],
            "namespace": metadata["namespace"],
            "completions": item["spec"].get("completions", 0),
        })
    return jobs


def get_routes(namespace):
    data = run_oc(["get", "routes", "-o", "json"], namespace)
    routes = []
    for item in data.get("items", []):
        metadata = item["metadata"]
        spec = item["spec"]
        tls = spec.get("tls", {})
        expiry = None
        if "certificate" in tls:
            expiry = parse_cert_expiry(tls["certificate"])
        routes.append({
            "type": "route",
            "name": metadata["name"],
            "namespace": metadata["namespace"],
            "host": spec.get("host", ""),
            "tls_termination": tls.get("termination", ""),
            "cert_expiry": expiry,
        })
    return routes


def parse_cert_expiry(cert_text):
    """Parse PEM certificate expiry date using openssl."""
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(cert_text.encode())
            tmp.flush()
            out = subprocess.check_output(["openssl", "x509", "-enddate", "-noout", "-in", tmp.name], text=True)
            return out.strip().split("=", 1)[1]
    except Exception:
        return None


def collect_cluster_data(yaml_file, include_routes=False, helm_packages=None):
    with open(yaml_file) as f:
        conf = yaml.safe_load(f)
    host = conf.get("host", {})
    namespace = host.get("namespace")
    cluster_url = host.get("clusterUrl")

    switch_cluster(cluster_url)

    # 🚀 Helm installation (if requested)
    if helm_packages:
        for pkg in helm_packages:
            release = pkg.get("release")
            chart = pkg.get("chart")
            values = pkg.get("values")
            install_helm_package(release, chart, namespace, values)

    deployments = get_deployments(namespace)
    jobs = get_jobs(namespace)
    routes = get_routes(namespace) if include_routes else []

    return deployments + jobs + routes


def render_report(data, output_html=True):
    df = pd.DataFrame(data)
    csv_path = os.path.join(OUTPUT_DIR, "report.csv")
    json_path = os.path.join(OUTPUT_DIR, "report.json")

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)

    if output_html and not df.empty:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("report.html.j2")
        html = template.render(data=data, generated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        with open(os.path.join(OUTPUT_DIR, "report.html"), "w") as f:
            f.write(html)

    print(f"✅ Reports generated: {csv_path}, {json_path}, report.html")


def main(include_routes=False, helm_packages=None):
    all_data = []
    for yaml_file in os.listdir(CLUSTERS_DIR):
        if yaml_file.endswith(".yaml"):
            print(f"\n📦 Processing: {yaml_file}")
            records = collect_cluster_data(
                os.path.join(CLUSTERS_DIR, yaml_file),
                include_routes,
                helm_packages
            )
            all_data.extend(records)
    render_report(all_data, output_html=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenShift Cluster Report + Helm Installer")
    parser.add_argument("--include-routes", action="store_true", help="Include routes and certificate expiry")
    parser.add_argument("--helm", nargs="+", metavar="release=chart[:values.yaml]",
                        help="Helm releases to install, e.g. app1=charts/app1:values-prod.yaml")
    args = parser.parse_args()

    helm_pkgs = []
    if args.helm:
        for spec in args.helm:
            # Parse format release=chart[:values.yaml]
            parts = spec.split("=")
            if len(parts) != 2:
                continue
            release, chart_spec = parts
            chart_parts = chart_spec.split(":")
            chart = chart_parts[0]
            values = chart_parts[1] if len(chart_parts) > 1 else None
            helm_pkgs.append({"release": release, "chart": chart, "values": values})

    main(include_routes=args.include_routes, helm_packages=helm_pkgs)
