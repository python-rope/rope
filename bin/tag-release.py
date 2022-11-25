#!/usr/bin/env python

import re
import subprocess
from datetime import datetime

import toml


pyproject = toml.load("pyproject.toml")
version = pyproject["project"]["version"]


def get_changelog(version):
    s = open("CHANGELOG.md").read()
    search_heading = f"# Release {version}"
    curdate = datetime.today().date().isoformat()

    headings = re.findall("# Release \d+\.\d+\.\d+", s)
    version_heading_index = headings.index(search_heading)
    version_changelog = s[
        s.index(headings[version_heading_index]) : s.index(
            headings[version_heading_index + 1]
        )
    ].strip()

    version_changelog = insert_date(version_changelog, curdate, after=search_heading)
    version_changelog = remove_headings(version_changelog)

    return version_changelog


def remove_headings(version_changelog):
    # Remove Markdown-style headings as it matches Git comment syntax
    version_changelog = re.sub("^#+\s+", "", version_changelog, flags=re.MULTILINE)
    return version_changelog


def insert_date(version_changelog, curdate, after):
    # Add a date section, if it doesn't already exist in the changelog section
    if "Date:" not in version_changelog:
        version_changelog = version_changelog.replace(
            after, f"{after}\n\nDate: {curdate}", 1
        )
    return version_changelog


message = get_changelog(version)
proc = subprocess.Popen(["git", "tag", "-s", version, "-m", message])
proc.wait()

subprocess.check_call(["git", "show", version])

print()
if input("Push [yn]? ") in "yY":
    subprocess.check_output(["git", "push", "origin", version])
