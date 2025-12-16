import requests

class SonarPortfolioClient:
    def __init__(self, sonar_url, token):
        self.sonar_url = sonar_url.rstrip("/")
        self.auth = (token, "")

    def get_portfolio_measures(self, portfolio_key, metrics):
        url = f"{self.sonar_url}/api/measures/component_tree"
        params = {
            "component": portfolio_key,
            "metricKeys": ",".join(metrics),
            "ps": 500
        }

        resp = requests.get(url, params=params, auth=self.auth)
        resp.raise_for_status()

        return resp.json().get("components", [])

    @staticmethod
    def print_summary(projects):
        for p in projects:
            print(f"\n{p['name']} ({p['key']})")
            for m in p.get("measures", []):
                print(f"  {m['metric']}: {m.get('value')}")


from sonar_portfolio_measures import SonarPortfolioClient

SONAR_URL = "https://sonarqube.company.com"
TOKEN = "YOUR_SONAR_TOKEN"
PORTFOLIO_KEY = "enterprise-portfolio"

METRICS = [
    # Size
    "ncloc",                       # Lines of Code

    # Duplications
    "duplicated_lines_density",

    # Security
    "security_rating",
    "vulnerabilities",

    # Maintainability (aka readability)
    "sqale_rating",                # Maintainability rating
    "code_smells",

    # Reliability
    "reliability_rating",
    "bugs",

    # Coverage (optional but common)
    "coverage"
]

client = SonarPortfolioClient(SONAR_URL, TOKEN)
projects = client.get_portfolio_measures(PORTFOLIO_KEY, METRICS)

client.print_summary(projects)
