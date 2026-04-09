#!/usr/bin/env python3
import os
import sys
try:
    import mokkari
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "mokkari"])
    import mokkari

username = os.getenv("METRON_USERNAME")
password = os.getenv("METRON_PASSWORD")

api = mokkari.api(username=username, passwd=password)

# Get first issue of DOOMWAR
series_list = api.series_list(params={"name": "DOOMWAR"})
series = series_list[0]
issues = api.issues_list(params={"series_id": series.id})
full_issue = api.issue(issues[0].id)

print(f"Issue: {full_issue.series.name} #{full_issue.number}")
print(f"\nCredits type: {type(full_issue.credits)}")
print(f"Credits: {full_issue.credits}")

if full_issue.credits:
    print(f"\nNumber of credits: {len(full_issue.credits)}")
    for credit in full_issue.credits:
        print(f"\nCredit type: {type(credit)}")
        print(f"Credit attributes: {dir(credit)}")
        print(f"Credit data: {credit}")
        break  # Just show first one
