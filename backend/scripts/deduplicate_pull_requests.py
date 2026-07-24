"""Merge duplicate Azure DevOps PR rows while preserving their review history.

Usage:
    python scripts/deduplicate_pull_requests.py          # report only
    python scripts/deduplicate_pull_requests.py --apply  # merge duplicates
"""

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import engine


async def main(apply: bool) -> int:
    async with engine.begin() as conn:
        duplicates = (await conn.execute(text("""
            SELECT repo, azure_pr_id, array_agg(id ORDER BY id) AS ids
            FROM pull_requests
            GROUP BY repo, azure_pr_id
            HAVING COUNT(*) > 1
            ORDER BY repo, azure_pr_id
        """))).mappings().all()

        if not duplicates:
            print("No duplicate pull requests found.")
            return 0

        for row in duplicates:
            ids = list(row["ids"])
            print(f"{row['repo']} #{row['azure_pr_id']}: ids={ids}; canonical={ids[0]}")

        if not apply:
            print("Report only. Re-run with --apply to merge these records.")
            return 1

        for row in duplicates:
            ids = list(row["ids"])
            canonical_id, duplicate_ids = ids[0], ids[1:]
            await conn.execute(
                text("UPDATE reviews SET pr_id = :canonical WHERE pr_id = ANY(:duplicates)"),
                {"canonical": canonical_id, "duplicates": duplicate_ids},
            )
            await conn.execute(
                text("DELETE FROM pull_requests WHERE id = ANY(:duplicates)"),
                {"duplicates": duplicate_ids},
            )
            print(
                f"Merged {row['repo']} #{row['azure_pr_id']}: "
                f"kept {canonical_id}, removed {duplicate_ids}"
            )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="perform the merge")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.apply)))
