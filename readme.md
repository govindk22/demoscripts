
pip install python-gitlab requests pandas python-dateutil


Member Statistics

Complete gitlab-commit-stats.py module to pull user commit statistics
- Metrics to include User Full Name, No of commits - excluding merges, No of merges, flag if rapid commit
- From To date range filter to exclude with default range as starting last monh first to end of that month
- Option to exclude some repo patterns such as poc, infra-configs and etc
- this seems necessary as gitlab provided contribution is not providing option to exclude some repos


set GITLAB_URL=https://gitlab.com
set GITLAB_TOKEN=glpat-t9HqEF8F9JSaO2kHCk7-_W86MQp1OjNpaXkxCw.01.120e2q5a9

python gitlab-member.py
