from __future__ import annotations

import psycopg


SKILL_ID = "bc7263f0-a127-4249-bdb0-11db03f9842c"
DIRTY = ["投资研究", "股票研究", "市场扫描", "供应链", "产业链"]


def main() -> None:
    conn = psycopg.connect("postgresql://aiskill:aiskill@localhost:5432/aiskill")
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                delete from skill_tags
                where skill_id = %s
                  and tag_id in (
                    select id from tags where name = any(%s)
                  )
                """,
                (SKILL_ID, DIRTY),
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                """
                select count(*)
                from skill_tags st
                join tags t on t.id = st.tag_id
                where st.skill_id = %s
                  and t.name = any(%s)
                """,
                (SKILL_ID, DIRTY),
            )
            print({"remaining_for_skill": cur.fetchone()[0]})
    finally:
        conn.close()


if __name__ == "__main__":
    main()
