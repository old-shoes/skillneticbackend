from __future__ import annotations

import argparse

import psycopg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report GitHub-related records for one repo_full_name")
    parser.add_argument("--repo", required=True, help="Repo full name, e.g. FoundationAgents/MetaGPT")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    conn = psycopg.connect("postgresql://aiskill:aiskill@localhost:5432/aiskill")
    try:
        with conn.cursor() as cur:
            print("github_skill_imports")
            cur.execute(
                """
                select id, import_status, parsed_tags, created_at, updated_at
                from github_skill_imports
                where repo_full_name = %s
                order by created_at desc
                """,
                (args.repo,),
            )
            for row in cur.fetchall():
                print(row)

            print("skill_submissions")
            cur.execute(
                """
                select id, status, tags, created_at, updated_at
                from skill_submissions
                where repo_full_name = %s
                order by created_at desc
                """,
                (args.repo,),
            )
            for row in cur.fetchall():
                print(row)

            print("skills")
            cur.execute(
                """
                select id, slug, title, source_type, source_name, source_url, search_keywords, created_at
                from skills
                where source_name = %s
                order by created_at desc
                """,
                (args.repo,),
            )
            for row in cur.fetchall():
                print(row)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
