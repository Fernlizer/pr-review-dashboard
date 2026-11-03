#!/usr/bin/env python3
"""Install the dashboard-owned skills into a Hermes profile, without touching secrets."""

import argparse
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-home", type=Path,
                        default=Path.home() / ".hermes/profiles/pr-review")
    args = parser.parse_args()
    if not (args.hermes_home / "config.yaml").is_file():
        parser.error("Create/configure the Hermes profile before installing its dashboard skills")
    source = Path(__file__).resolve().parents[1] / "backend/hermes_skills"
    for skill in sorted(source.iterdir()):
        if not (skill / "SKILL.md").is_file():
            continue
        destination = args.hermes_home / "skills" / skill.name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(skill / "SKILL.md", destination / "SKILL.md")
        print(f"Installed {skill.name}")


if __name__ == "__main__":
    main()
