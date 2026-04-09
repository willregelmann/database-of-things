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

# Get first series (DOOMWAR)
series_list = api.series_list(params={"name": "DOOMWAR"})
series = series_list[0]

# Get issues list
issues = api.issues_list(params={"series_id": series.id})
first_issue = issues[0]

print("=== Issue from issues_list() ===")
print(f"Type: {type(first_issue)}")
print(f"Attributes: {dir(first_issue)}")
print(f"\nHas 'creators'? {hasattr(first_issue, 'creators')}")

# Try fetching full issue
print("\n=== Full Issue from issue() ===")
full_issue = api.issue(first_issue.id)
print(f"Type: {type(full_issue)}")
print(f"Attributes: {dir(full_issue)}")
print(f"\nHas 'creators'? {hasattr(full_issue, 'creators')}")

if hasattr(full_issue, 'creators'):
    print(f"\nCreators ({len(full_issue.creators)}):")
    for creator in full_issue.creators:
        print(f"  - {creator.name} ({creator.role})")
