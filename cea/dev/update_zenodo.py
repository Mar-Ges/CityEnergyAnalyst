import os.path
import re
from datetime import datetime

from cea import __version__
import requests

ZENODO_URL = "https://zenodo.org/badge/latestdoi/49491341"
DOI_PREFIX = "10.5281"

ZENODO_BADGE_URL_PATTERN = re.compile(r"(https://zenodo\.org/badge/DOI/).+(\.svg)")
DOI_URL_PATTERN = re.compile(r"(https://doi\.org/).+")
README_CITE_PATTERN = re.compile(r"(For V)\d+.\d+.\d+( \(.+\): .+)")
CREDITS_CITE_PATTERN = re.compile(r'(The CEA team, "City Energy Analyst v)\d+\.\d+\.\d+(", Zenodo, )\d+, .+')


def update_readme(version: str, doi: str) -> None:
    readme_path = os.path.join(os.path.dirname(__file__), "..", "..", "README.rst")
    with open(readme_path) as f:
        readme = f.read()

    result = readme
    # Update badge url
    if not ZENODO_BADGE_URL_PATTERN.search(result):
        raise ValueError("Unable to find zenodo badge url in the file")
    result = ZENODO_BADGE_URL_PATTERN.sub(rf"\g<1>{doi}\g<2>", result)

    # Update doi url
    if not DOI_URL_PATTERN.search(result):
        raise ValueError("Unable to find zenodo doi url in the file")
    result = DOI_URL_PATTERN.sub(rf"\g<1>{doi}", result)

    # Update version
    if not README_CITE_PATTERN.search(result):
        raise ValueError("Unable to find cite statement in the file")
    result = README_CITE_PATTERN.sub(rf"\g<1>{version}\g<2>", result)

    with open(readme_path, "w") as f:
        f.write(result)


def update_credits(version: str, doi: str) -> None:
    credits_path = os.path.join(os.path.dirname(__file__), "..", "..", "CREDITS.md")
    with open(credits_path) as f:
        _credits = f.read()

    if not CREDITS_CITE_PATTERN.search(_credits):
        raise ValueError("Unable to find cite statement in the file")

    year = datetime.today().strftime("%Y")
    result = CREDITS_CITE_PATTERN.sub(rf"\g<1>{version}\g<2>{year}, {doi}", _credits)

    with open(credits_path, "w") as f:
        f.write(result)


def main(*args) -> None:
    current_version = __version__

    # Fetch the new zenodo id for current version
    r = requests.get(ZENODO_URL)
    zenodo_latest_id = r.url.split("/")[-1]

    doi = f"{DOI_PREFIX}/zenodo.{zenodo_latest_id}"
    update_readme(current_version, doi)
    update_credits(current_version, doi)


if __name__ == '__main__':
    main()
