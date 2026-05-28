"""backfill skill content and sync approved submissions

Revision ID: 20260523_01
Revises: 20260522_02
Create Date: 2026-05-23 11:20:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260523_01"
down_revision = "20260522_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE skills AS s
        SET content = btrim(ss.system_prompt)
        FROM skill_submissions AS ss
        WHERE ss.approved_skill_id = s.id
          AND ss.deleted_at IS NULL
          AND btrim(COALESCE(ss.system_prompt, '')) <> ''
          AND btrim(COALESCE(s.content, '')) = ''
        """
    )

    op.execute(
        """
        UPDATE skills
        SET content = CONCAT(
          '## Skill 简介', E'\\n\\n',
          summary, E'\\n\\n',
          '## 适用场景', E'\\n\\n',
          '- 适合 ', COALESCE(NULLIF(use_case, ''), '当前这个工作场景'), E'\\n',
          '- 希望快速得到可直接使用的结果', E'\\n',
          '- 需要稳定的结构化输出，减少反复修改', E'\\n\\n',
          '## 推荐模型', E'\\n\\n',
          '- ', CASE
            WHEN jsonb_array_length(COALESCE(recommended_models, '[]'::jsonb)) > 0
              THEN array_to_string(ARRAY(SELECT jsonb_array_elements_text(recommended_models)), '、')
            ELSE '通用大模型'
          END, E'\\n\\n',
          '## 使用步骤', E'\\n\\n',
          '1. 先明确这次任务的目标、对象和限制条件。', E'\\n',
          '2. 把关键信息一次性提供给「', title, '」。', E'\\n',
          '3. 查看首轮结果后，继续补充约束、语气或格式要求。', E'\\n',
          '4. 最后将产出复制到实际工作流中继续加工。', E'\\n\\n',
          '## 输入建议', E'\\n\\n',
          '- 补充背景信息，而不是只给一句模糊需求', E'\\n',
          '- 明确目标用户、输出风格和篇幅要求', E'\\n',
          '- 如果有参考样例，可以一起提供', E'\\n\\n',
          '## 输出预期', E'\\n\\n',
          '- 先给出完整初稿', E'\\n',
          '- 关键内容尽量分点呈现', E'\\n',
          '- 根据 ', COALESCE(NULLIF(type, ''), 'skill'), ' 类型，输出可复制、可继续编辑的结果', E'\\n\\n',
          '## 使用提醒', E'\\n\\n',
          '- 首轮结果更适合快速起稿，不建议直接无审阅发布', E'\\n',
          '- 涉及品牌、法务或对外发布内容时，建议人工复核'
        )
        WHERE deleted_at IS NULL
          AND status = 'published'
          AND btrim(COALESCE(content, '')) = ''
        """
    )


def downgrade() -> None:
    pass
