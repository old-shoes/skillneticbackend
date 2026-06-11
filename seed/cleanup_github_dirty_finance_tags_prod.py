from __future__ import annotations

import psycopg


DIRTY = {"投资研究", "股票研究", "市场扫描", "供应链", "产业链"}


def main() -> None:
    conn = psycopg.connect("postgresql://aiskill:aiskill@localhost:5432/aiskill")
    conn.autocommit = False
    touched = 0
    synced = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, tags, approved_skill_id, title, summary
                from skill_submissions
                where deleted_at is null
                  and github_url is not null
                """
            )
            rows = cur.fetchall()
            for submission_id, tags, approved_skill_id, title, summary in rows:
                current_tags = list(tags or [])
                cleaned_tags = [tag for tag in current_tags if tag not in DIRTY]
                if cleaned_tags == current_tags:
                    continue
                cur.execute(
                    "update skill_submissions set tags = %s where id = %s",
                    (cleaned_tags, submission_id),
                )
                touched += 1
                if approved_skill_id:
                    cur.execute(
                        """
                        delete from skill_tags
                        where skill_id = %s
                          and tag_id in (
                            select id from tags where name = any(%s)
                          )
                        """,
                        (approved_skill_id, list(DIRTY)),
                    )
                    search_keywords = " ".join(
                        part for part in [title or "", summary or "", *cleaned_tags] if part
                    )
                    cur.execute(
                        "update skills set search_keywords = %s where id = %s",
                        (search_keywords, approved_skill_id),
                    )
                    synced += 1
            cur.execute(
                """
                delete from skill_tags
                where tag_id in (
                    select id from tags where name = any(%s)
                )
                  and skill_id in (
                    select distinct approved_skill_id
                    from skill_submissions
                    where deleted_at is null
                      and github_url is not null
                      and approved_skill_id is not null
                  )
                """,
                (list(DIRTY),),
            )
        conn.commit()
        print({"touched": touched, "synced": synced})
        with conn.cursor() as cur:
            cur.execute(
                """
                select count(*)
                from skill_submissions
                where coalesce(tags::text, '') like '%投资研究%'
                   or coalesce(tags::text, '') like '%股票研究%'
                   or coalesce(tags::text, '') like '%市场扫描%'
                   or coalesce(tags::text, '') like '%供应链%'
                   or coalesce(tags::text, '') like '%产业链%'
                """
            )
            print({"remaining_submission_hits": cur.fetchone()[0]})
            cur.execute(
                """
                select count(*)
                from skill_tags st
                join tags t on t.id = st.tag_id
                where t.name in ('投资研究', '股票研究', '市场扫描', '供应链', '产业链')
                """
            )
            print({"remaining_skill_tag_hits": cur.fetchone()[0]})
    finally:
        conn.close()


if __name__ == "__main__":
    main()
