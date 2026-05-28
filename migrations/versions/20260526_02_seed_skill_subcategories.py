"""seed second-level skill categories

Revision ID: 20260526_02
Revises: 20260526_01
Create Date: 2026-05-26 13:00:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260526_02"
down_revision = "20260526_01"
branch_labels = None
depends_on = None


SUBCATEGORY_ROWS = [
    ("writing", "文案写作", "copywriting", "Copywriting", 1),
    ("writing", "社媒内容", "social-content", "Social Content", 2),
    ("writing", "长文写作", "longform-writing", "Long-form Writing", 3),
    ("writing", "编辑校对", "editing-proofreading", "Editing & Proofreading", 4),
    ("coding", "前端开发", "frontend-development", "Frontend Development", 1),
    ("coding", "后端开发", "backend-development", "Backend Development", 2),
    ("coding", "数据库与接口", "database-api", "Database & API", 3),
    ("coding", "AI 开发", "ai-development", "AI Development", 4),
    ("office", "PPT 与汇报", "ppt-presentation", "PPT & Presentation", 1),
    ("office", "表格与数据", "excel-data", "Spreadsheets & Data", 2),
    ("office", "邮件与文档", "email-documents", "Email & Documents", 3),
    ("office", "会议与总结", "meeting-summary", "Meetings & Summaries", 4),
    ("design", "平面设计", "graphic-design", "Graphic Design", 1),
    ("design", "UI 设计", "ui-design", "UI Design", 2),
    ("design", "电商设计", "ecommerce-design", "E-commerce Design", 3),
    ("design", "图片处理", "image-editing", "Image Editing", 4),
    ("marketing", "品牌营销", "brand-marketing", "Brand Marketing", 1),
    ("marketing", "内容营销", "content-marketing", "Content Marketing", 2),
    ("marketing", "SEO 与增长", "seo-growth", "SEO & Growth", 3),
    ("marketing", "广告投放", "ad-campaign", "Ad Campaigns", 4),
    ("learning", "语言学习", "language-learning", "Language Learning", 1),
    ("learning", "考试学习", "exam-study", "Exam Study", 2),
    ("learning", "知识整理", "knowledge-notes", "Knowledge Notes", 3),
    ("learning", "论文写作", "paper-writing", "Paper Writing", 4),
    ("video", "短视频脚本", "short-video-script", "Short Video Scripts", 1),
    ("video", "口播与分镜", "narration-storyboard", "Narration & Storyboard", 2),
    ("video", "剪辑策划", "video-editing-planning", "Editing Planning", 3),
    ("video", "标题与封面", "video-title-cover", "Titles & Covers", 4),
    ("automation", "工作流自动化", "workflow-automation", "Workflow Automation", 1),
    ("automation", "办公自动化", "office-automation", "Office Automation", 2),
    ("automation", "数据自动化", "data-automation", "Data Automation", 3),
    ("automation", "Agent 自动化", "agent-automation", "Agent Automation", 4),
]


def upgrade() -> None:
    for parent_slug, name, slug, name_en, sort_order in SUBCATEGORY_ROWS:
        op.execute(
            f"""
            INSERT INTO categories (
              id,
              name,
              slug,
              name_en,
              parent_id,
              level,
              icon,
              color,
              description,
              skill_count,
              is_enabled,
              is_hot,
              sort_order,
              created_at,
              updated_at
            )
            SELECT
              gen_random_uuid(),
              '{name}',
              '{slug}',
              '{name_en}',
              parent.id,
              2,
              parent.icon,
              parent.color,
              '',
              0,
              TRUE,
              FALSE,
              {sort_order},
              NOW(),
              NOW()
            FROM categories AS parent
            WHERE parent.slug = '{parent_slug}'
              AND parent.level = 1
              AND NOT EXISTS (
                SELECT 1 FROM categories existing WHERE existing.slug = '{slug}'
              )
            """
        )


def downgrade() -> None:
    slugs = ", ".join(f"'{slug}'" for _, _, slug, _, _ in SUBCATEGORY_ROWS)
    op.execute(f"DELETE FROM categories WHERE slug IN ({slugs})")
