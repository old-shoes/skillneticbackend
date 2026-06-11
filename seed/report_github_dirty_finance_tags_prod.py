from __future__ import annotations

import psycopg


DIRTY = ["投资研究", "股票研究", "市场扫描", "供应链", "产业链"]


def main() -> None:
    conn = psycopg.connect("postgresql://aiskill:aiskill@localhost:5432/aiskill")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, repo_full_name, tags
                from skill_submissions
                where deleted_at is null
                  and (
                    coalesce(tags::text, '') like '%投资研究%'
                    or coalesce(tags::text, '') like '%股票研究%'
                    or coalesce(tags::text, '') like '%市场扫描%'
                    or coalesce(tags::text, '') like '%供应链%'
                    or coalesce(tags::text, '') like '%产业链%'
                  )
                order by created_at asc
                """
            )
            print("submission_hits")
            for row in cur.fetchall():
                print(row)

            cur.execute(
                """
                select s.id, s.slug, s.title, array_agg(t.name order by t.name) as tags
                from skill_tags st
                join skills s on s.id = st.skill_id
                join tags t on t.id = st.tag_id
                where t.name = any(%s)
                group by s.id, s.slug, s.title
                order by s.title asc
                """
                ,
                (DIRTY,),
            )
            print("skill_tag_hits")
            for row in cur.fetchall():
                print(row)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
