#!/usr/bin/env python3
import json
import os
import sys
import urllib.parse
import urllib.error
import urllib.request
from collections import defaultdict


README_PATH = "README.md"
START_MARKER = "<!-- AUTO-TECHSTACK:START -->"
END_MARKER = "<!-- AUTO-TECHSTACK:END -->"
MAX_BADGES = 8
EXCLUDED_LANGUAGES = {"Jupyter Notebook", "ShaderLab"}

LOGO_MAP = {
    "C++": "cplusplus",
    "C#": "csharp",
    "Jupyter Notebook": "jupyter",
    "Vue": "vuedotjs",
}


def get_json(url, token=None):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError(
                "GitHub API rate limit exceeded. Provide GITHUB_TOKEN (or GH_TOKEN) and retry."
            ) from exc
        raise


def list_repos(username, token):
    page = 1
    repos = []
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&type=owner&page={page}"
        items = get_json(url, token=token)
        if not items:
            break
        repos.extend(items)
        page += 1
    return repos


def collect_languages(repos, token):
    lang_totals = defaultdict(int)
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        langs = get_json(repo["languages_url"], token=token)
        for language, size in langs.items():
            if language in EXCLUDED_LANGUAGES:
                continue
            lang_totals[language] += int(size)
    return lang_totals


def to_badge(language):
    logo = LOGO_MAP.get(language, language.lower().replace(" ", ""))
    label = urllib.parse.quote(language)
    logo_q = urllib.parse.quote(logo)
    return f"![{language}](https://img.shields.io/badge/{label}-111827?style=for-the-badge&logo={logo_q}&logoColor=white)"


def build_techstack_block(lang_totals):
    top_languages = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:MAX_BADGES]
    if not top_languages:
        return "_No language data found yet._"
    badges = [to_badge(lang) for lang, _ in top_languages]
    return "".join(badges)


def update_readme(content, generated_block):
    if START_MARKER not in content or END_MARKER not in content:
        raise ValueError("README markers not found.")
    before, rest = content.split(START_MARKER, 1)
    _, after = rest.split(END_MARKER, 1)
    return f"{before}{START_MARKER}\n{generated_block}\n{END_MARKER}{after}"


def main():
    username = os.getenv("PROFILE_USERNAME", "SCIERke")
    token = os.getenv("GITHUB_TOKEN", "").strip() or os.getenv("GH_TOKEN", "").strip() or None
    preview_only = "--preview" in sys.argv
    repos = list_repos(username, token)
    lang_totals = collect_languages(repos, token)
    generated = build_techstack_block(lang_totals)

    if preview_only:
        owned_repos = [
            r["name"]
            for r in repos
            if not r.get("fork") and not r.get("archived")
        ]
        top_languages = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:MAX_BADGES]
        print("Fetched repos (non-fork, non-archived):")
        for name in owned_repos:
            print(f"- {name}")
        print("\nTop languages:")
        for language, size in top_languages:
            print(f"- {language}: {size}")
        print("\nBadges:")
        print(generated)
        return

    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    updated = update_readme(readme, generated)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"Updated {README_PATH} with top {MAX_BADGES} languages for {username}.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
