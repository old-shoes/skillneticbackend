from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.modules.category.models import Category
from app.modules.homepage.models import HomepageStats
from app.modules.skill.models import Skill, SkillTag, Tag
from app.modules.tutorial.models import Tutorial


def build_skill_content(title: str, summary: str, use_case: str, recommended_models: List[str], skill_type: str) -> str:
    model_text = "、".join(recommended_models) if recommended_models else "通用大模型"
    return f"""## Skill 简介

{summary}

## 适用场景

- {use_case}
- 希望快速得到可直接使用的结果
- 需要稳定的结构化输出，减少反复修改

## 推荐模型

- {model_text}

## 使用步骤

1. 先明确这次任务的目标、对象和限制条件。
2. 把关键信息一次性提供给 `{title}`。
3. 查看首轮结果后，继续补充约束、语气或格式要求。
4. 最后将产出复制到实际工作流中继续加工。

## 输入建议

- 补充背景信息，而不是只给一句模糊需求
- 明确目标用户、输出风格和篇幅要求
- 如果有参考样例，可以一起提供

## 输出预期

- 先给出完整初稿
- 关键内容尽量分点呈现
- 根据 `{skill_type}` 类型，输出可复制、可继续编辑的结果

## 使用提醒

- 首轮结果更适合快速起稿，不建议直接无审阅发布
- 涉及品牌、法务或对外发布内容时，建议人工复核
"""


def main() -> None:
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    try:
        db.execute(delete(SkillTag))
        db.execute(delete(Skill))
        db.execute(delete(Tag))
        db.execute(delete(Tutorial))
        db.execute(delete(Category))
        db.execute(delete(HomepageStats))

        categories = [
            Category(name="写作", slug="writing", icon="prompt", color="blue", description="文案写作、标题生成、内容润色等", skill_count=2345, sort_order=1),
            Category(name="编程", slug="coding", icon="browse", color="green", description="代码生成、调试、解释与优化", skill_count=2128, sort_order=2),
            Category(name="办公", slug="office", icon="tool", color="orange", description="文档处理、数据分析、PPT 等效率工具", skill_count=2256, sort_order=3),
            Category(name="设计", slug="design", icon="browse", color="purple", description="图像生成、UI 设计、创意视觉等", skill_count=1789, sort_order=4),
            Category(name="营销", slug="marketing", icon="prompt", color="rose", description="社媒运营、广告文案、用户增长等", skill_count=1654, sort_order=5),
            Category(name="学习", slug="learning", icon="tutorial", color="indigo", description="知识问答、笔记总结、学习规划等", skill_count=1402, sort_order=6),
            Category(name="视频", slug="video", icon="browse", color="cyan", description="脚本创作、分镜、剪辑辅助", skill_count=1210, sort_order=7),
            Category(name="自动化", slug="automation", icon="agent", color="emerald", description="工作流编排、Agent、任务串联", skill_count=1098, sort_order=8),
        ]
        db.add_all(categories)
        db.flush()

        category_map = {item.slug: item for item in db.scalars(select(Category)).all()}

        tags = [
            Tag(name="小红书", slug="xiaohongshu", type="scene", skill_count=1, sort_order=20),
            Tag(name="短视频", slug="short-video", type="scene", skill_count=1, sort_order=21),
            Tag(name="简历", slug="resume", type="scene", skill_count=2, sort_order=22),
            Tag(name="PPT", slug="ppt", type="scene", skill_count=1, sort_order=23),
            Tag(name="Excel", slug="excel", type="scene", skill_count=1, sort_order=24),
            Tag(name="SEO", slug="seo", type="scene", skill_count=1, sort_order=25),
            Tag(name="电商", slug="ecommerce", type="scene", skill_count=1, sort_order=26),
            Tag(name="社媒", slug="social-media", type="scene", skill_count=1, sort_order=27),
            Tag(name="论文", slug="paper", type="scene", skill_count=1, sort_order=28),
            Tag(name="会议", slug="meeting", type="scene", skill_count=1, sort_order=29),
            Tag(name="新手", slug="beginner", type="difficulty", skill_count=11, sort_order=40),
            Tag(name="进阶", slug="intermediate", type="difficulty", skill_count=7, sort_order=41),
            Tag(name="专业", slug="advanced", type="difficulty", skill_count=2, sort_order=42),
            Tag(name="提示词", slug="prompt", type="type", skill_count=9, sort_order=50),
            Tag(name="工作流", slug="workflow", type="type", skill_count=6, sort_order=51),
            Tag(name="教程", slug="tutorial", type="type", skill_count=2, sort_order=52),
            Tag(name="工具配置", slug="tool-config", type="type", skill_count=2, sort_order=53),
            Tag(name="Agent", slug="agent", type="type", skill_count=1, sort_order=54),
        ]
        db.add_all(tags)
        db.flush()

        tag_map = {item.slug: item for item in db.scalars(select(Tag)).all()}

        skills = [
            Skill(
                title="小红书爆款标题生成",
                slug="xiaohongshu-title-generator",
                summary="输入产品、人群和卖点，快速生成 20 个小红书风格标题。",
                content=build_skill_content(
                    "小红书爆款标题生成",
                    "输入产品、人群和卖点，快速生成 20 个小红书风格标题。",
                    "适合品牌种草、爆款选题和社媒内容起稿。",
                    ["GPT-4o", "ChatGPT"],
                    "prompt",
                ),
                cover_icon="prompt",
                category_id=category_map["writing"].id,
                difficulty="beginner",
                type="prompt",
                search_keywords="小红书 标题 文案 种草 爆款",
                recommended_models=["GPT-4o", "ChatGPT"],
                favorite_count=8600,
                view_count=23000,
                is_featured=True,
                is_hot=True,
                status="published",
                published_at=now - timedelta(days=1),
            ),
            Skill(
                title="代码解释器（Python）",
                slug="python-code-explainer",
                summary="粘贴代码，自动解释逻辑、找出问题并给出优化建议。",
                content=build_skill_content(
                    "代码解释器（Python）",
                    "粘贴代码，自动解释逻辑、找出问题并给出优化建议。",
                    "适合阅读陌生代码、定位问题和做结构化讲解。",
                    ["DeepSeek", "ChatGPT"],
                    "tool_config",
                ),
                cover_icon="browse",
                category_id=category_map["coding"].id,
                difficulty="beginner",
                type="tool_config",
                search_keywords="Python 代码 解释 调试 注释",
                recommended_models=["DeepSeek", "ChatGPT"],
                favorite_count=6200,
                view_count=18000,
                is_featured=True,
                is_hot=True,
                status="published",
                published_at=now - timedelta(days=2),
            ),
            Skill(
                title="Excel 数据分析助手",
                slug="excel-data-analysis-assistant",
                summary="上传表格后贴数据，自动分析趋势、生成图表并给出业务洞察。",
                content=build_skill_content(
                    "Excel 数据分析助手",
                    "上传表格后贴数据，自动分析趋势、生成图表并给出业务洞察。",
                    "适合做周报分析、经营复盘和表格洞察。",
                    ["GPT-4o", "ChatGPT"],
                    "workflow",
                ),
                cover_icon="workflow",
                category_id=category_map["office"].id,
                difficulty="intermediate",
                type="workflow",
                search_keywords="Excel 分析 图表 报表 数据洞察",
                recommended_models=["GPT-4o", "ChatGPT"],
                favorite_count=5100,
                view_count=16000,
                is_featured=True,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=3),
            ),
            Skill(
                title="文章润色助手",
                slug="article-polisher",
                summary="提升文章语言质量，让表达更流畅、专业，适合各类写作场景。",
                content=build_skill_content(
                    "文章润色助手",
                    "提升文章语言质量，让表达更流畅、专业，适合各类写作场景。",
                    "适合公众号、博客、邮件和品牌文案优化。",
                    ["Claude"],
                    "prompt",
                ),
                cover_icon="prompt",
                category_id=category_map["writing"].id,
                difficulty="beginner",
                type="prompt",
                search_keywords="润色 写作 文章 优化 表达",
                recommended_models=["Claude"],
                favorite_count=4300,
                view_count=12000,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=4),
            ),
            Skill(
                title="Midjourney 提示词生成",
                slug="midjourney-prompt-generator",
                summary="根据描述生成高质量 Midjourney 画面提示词，轻松获得更稳定的出图。",
                content=build_skill_content(
                    "Midjourney 提示词生成",
                    "根据描述生成高质量 Midjourney 画面提示词，轻松获得更稳定的出图。",
                    "适合海报、插画、视觉概念和广告创意出图。",
                    ["Midjourney"],
                    "prompt",
                ),
                cover_icon="browse",
                category_id=category_map["design"].id,
                difficulty="beginner",
                type="prompt",
                search_keywords="Midjourney 提示词 画图 图像 生成",
                recommended_models=["Midjourney"],
                favorite_count=3800,
                view_count=11000,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=5),
            ),
            Skill(
                title="简历优化大师",
                slug="resume-optimizer-master",
                summary="上传简历后，优化内容结构，突出亮点，提升求职竞争力。",
                content=build_skill_content(
                    "简历优化大师",
                    "上传简历后，优化内容结构，突出亮点，提升求职竞争力。",
                    "适合校招、社招和岗位定制化投递。",
                    ["GPT-4o", "Claude"],
                    "prompt",
                ),
                cover_icon="user",
                category_id=category_map["office"].id,
                difficulty="intermediate",
                type="prompt",
                search_keywords="简历 求职 优化 岗位 匹配",
                recommended_models=["GPT-4o", "Claude"],
                favorite_count=7200,
                view_count=20000,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=6),
            ),
            Skill(
                title="PPT 大纲生成器",
                slug="ppt-outline-generator",
                summary="输入主题，自动生成结构清晰的 PPT 大纲和内容要点，节省构思时间。",
                content=build_skill_content(
                    "PPT 大纲生成器",
                    "输入主题，自动生成结构清晰的 PPT 大纲和内容要点，节省构思时间。",
                    "适合汇报、提案、培训和路演场景。",
                    ["ChatGPT", "通义千问"],
                    "workflow",
                ),
                cover_icon="tutorial",
                category_id=category_map["office"].id,
                difficulty="beginner",
                type="workflow",
                search_keywords="PPT 大纲 演示 汇报 结构",
                recommended_models=["ChatGPT", "通义千问"],
                favorite_count=3200,
                view_count=9000,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=7),
            ),
            Skill(
                title="短视频脚本创作",
                slug="short-video-script-creator",
                summary="生成短视频脚本、分镜和文案，适合抖音、小红书等创作场景。",
                content=build_skill_content(
                    "短视频脚本创作",
                    "生成短视频脚本、分镜和文案，适合抖音、小红书等创作场景。",
                    "适合口播脚本、短视频选题和分镜起稿。",
                    ["GPT-4o", "Kimi"],
                    "prompt",
                ),
                cover_icon="prompt",
                category_id=category_map["video"].id,
                difficulty="intermediate",
                type="prompt",
                search_keywords="短视频 脚本 口播 分镜 抖音",
                recommended_models=["GPT-4o", "Kimi"],
                favorite_count=4700,
                view_count=13000,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=8),
            ),
            Skill(
                title="自动化 Workflow 设计",
                slug="automation-workflow-design",
                summary="根据需求设计自动化工作流，提升效率，减少重复劳动。",
                content=build_skill_content(
                    "自动化 Workflow 设计",
                    "根据需求设计自动化工作流，提升效率，减少重复劳动。",
                    "适合把零散人工流程整理成可执行链路。",
                    ["ChatGPT", "DeepSeek"],
                    "workflow",
                ),
                cover_icon="workflow",
                category_id=category_map["automation"].id,
                difficulty="advanced",
                type="workflow",
                search_keywords="自动化 workflow agent 流程 设计",
                recommended_models=["ChatGPT", "DeepSeek"],
                favorite_count=2600,
                view_count=6000,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=9),
            ),
            Skill(
                title="会议纪要整理助手",
                slug="meeting-notes-assistant",
                summary="自动整理会议纪要、待办和结论，适合团队协作和项目推进。",
                content=build_skill_content(
                    "会议纪要整理助手",
                    "自动整理会议纪要、待办和结论，适合团队协作和项目推进。",
                    "适合内部会议、客户沟通和项目同步整理。",
                    ["Kimi", "GPT-4o"],
                    "workflow",
                ),
                cover_icon="workflow",
                category_id=category_map["office"].id,
                difficulty="beginner",
                type="workflow",
                search_keywords="会议 纪要 待办 总结 协作",
                recommended_models=["Kimi", "GPT-4o"],
                favorite_count=5800,
                view_count=17000,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=10),
            ),
            Skill(
                title="产品需求文档生成",
                slug="prd-generator",
                summary="一键生成结构完整、清晰的 PRD 文档，减少反复修改成本。",
                content=build_skill_content(
                    "产品需求文档生成",
                    "一键生成结构完整、清晰的 PRD 文档，减少反复修改成本。",
                    "适合需求梳理、方案评审和跨团队协作。",
                    ["DeepSeek", "ChatGPT"],
                    "workflow",
                ),
                cover_icon="workflow",
                category_id=category_map["office"].id,
                difficulty="intermediate",
                type="workflow",
                search_keywords="PRD 产品 需求 文档 原型",
                recommended_models=["DeepSeek", "ChatGPT"],
                favorite_count=2900,
                view_count=8600,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=11),
            ),
            Skill(
                title="邮件润色助手",
                slug="email-polisher",
                summary="让邮件表达更专业、简洁且礼貌，适合商务沟通和对外联系。",
                content=build_skill_content(
                    "邮件润色助手",
                    "让邮件表达更专业、简洁且礼貌，适合商务沟通和对外联系。",
                    "适合商务邮件、客户回复和跨团队沟通。",
                    ["Claude"],
                    "prompt",
                ),
                cover_icon="prompt",
                category_id=category_map["office"].id,
                difficulty="beginner",
                type="prompt",
                search_keywords="邮件 润色 商务 沟通 英文",
                recommended_models=["Claude"],
                favorite_count=2500,
                view_count=7900,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=12),
            ),
            Skill(
                title="论文大纲生成器",
                slug="paper-outline-generator",
                summary="根据研究主题快速生成论文大纲、章节建议和写作切入点。",
                content=build_skill_content(
                    "论文大纲生成器",
                    "根据研究主题快速生成论文大纲、章节建议和写作切入点。",
                    "适合课程论文、开题准备和研究框架梳理。",
                    ["Gemini", "ChatGPT"],
                    "tutorial",
                ),
                cover_icon="tutorial",
                category_id=category_map["learning"].id,
                difficulty="beginner",
                type="tutorial",
                search_keywords="论文 大纲 学术 写作 研究",
                recommended_models=["Gemini", "ChatGPT"],
                favorite_count=2100,
                view_count=6500,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=13),
            ),
            Skill(
                title="社媒文案日历生成",
                slug="social-content-calendar-generator",
                summary="生成一周社媒选题、文案与发布时间建议，适合内容团队排期。",
                content=build_skill_content(
                    "社媒文案日历生成",
                    "生成一周社媒选题、文案与发布时间建议，适合内容团队排期。",
                    "适合品牌账号、活动节点和内容排期规划。",
                    ["通义千问", "GPT-4o"],
                    "workflow",
                ),
                cover_icon="prompt",
                category_id=category_map["marketing"].id,
                difficulty="intermediate",
                type="workflow",
                search_keywords="社媒 文案 日历 排期 营销",
                recommended_models=["通义千问", "GPT-4o"],
                favorite_count=1900,
                view_count=5600,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=14),
            ),
            Skill(
                title="代码注释生成",
                slug="code-comment-generator",
                summary="为代码自动补充清晰注释，帮助团队理解上下文和维护逻辑。",
                content=build_skill_content(
                    "代码注释生成",
                    "为代码自动补充清晰注释，帮助团队理解上下文和维护逻辑。",
                    "适合老项目维护、交接和代码可读性提升。",
                    ["DeepSeek"],
                    "tool_config",
                ),
                cover_icon="tool",
                category_id=category_map["coding"].id,
                difficulty="beginner",
                type="tool_config",
                search_keywords="代码 注释 解释 开发 维护",
                recommended_models=["DeepSeek"],
                favorite_count=1700,
                view_count=5100,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=15),
            ),
            Skill(
                title="SEO 标题生成器",
                slug="seo-title-generator",
                summary="围绕关键词生成 SEO 友好的标题和描述，适合内容分发和搜索优化。",
                content=build_skill_content(
                    "SEO 标题生成器",
                    "围绕关键词生成 SEO 友好的标题和描述，适合内容分发和搜索优化。",
                    "适合文章发布页、落地页和搜索流量优化。",
                    ["ChatGPT", "Claude"],
                    "prompt",
                ),
                cover_icon="prompt",
                category_id=category_map["marketing"].id,
                difficulty="beginner",
                type="prompt",
                search_keywords="SEO 标题 关键词 描述 搜索优化",
                recommended_models=["ChatGPT", "Claude"],
                favorite_count=1600,
                view_count=4800,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=16),
            ),
            Skill(
                title="电商详情页文案生成",
                slug="ecommerce-detail-copy-generator",
                summary="生成商品卖点、详情页模块和转化型文案，适合电商上新与活动页。",
                content=build_skill_content(
                    "电商详情页文案生成",
                    "生成商品卖点、详情页模块和转化型文案，适合电商上新与活动页。",
                    "适合新品上架、活动详情页和商品卖点整理。",
                    ["Claude", "通义千问"],
                    "prompt",
                ),
                cover_icon="prompt",
                category_id=category_map["marketing"].id,
                difficulty="intermediate",
                type="prompt",
                search_keywords="电商 详情页 文案 卖点 转化",
                recommended_models=["Claude", "通义千问"],
                favorite_count=2400,
                view_count=7200,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=17),
            ),
            Skill(
                title="学习计划制定助手",
                slug="study-plan-assistant",
                summary="根据目标和时间生成可执行学习计划，适合自学者和考试准备场景。",
                content=build_skill_content(
                    "学习计划制定助手",
                    "根据目标和时间生成可执行学习计划，适合自学者和考试准备场景。",
                    "适合备考、自学转岗和技能提升规划。",
                    ["Kimi", "Gemini"],
                    "tutorial",
                ),
                cover_icon="tutorial",
                category_id=category_map["learning"].id,
                difficulty="beginner",
                type="tutorial",
                search_keywords="学习 计划 路线 目标 考试",
                recommended_models=["Kimi", "Gemini"],
                favorite_count=2800,
                view_count=7600,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=18),
            ),
            Skill(
                title="面试问答模拟器",
                slug="interview-qa-simulator",
                summary="模拟岗位面试问答，补充追问和反馈，帮助你更有针对性地准备面试。",
                content=build_skill_content(
                    "面试问答模拟器",
                    "模拟岗位面试问答，补充追问和反馈，帮助你更有针对性地准备面试。",
                    "适合正式面试前训练表达和查漏补缺。",
                    ["ChatGPT", "GPT-4o"],
                    "agent",
                ),
                cover_icon="agent",
                category_id=category_map["learning"].id,
                difficulty="intermediate",
                type="agent",
                search_keywords="面试 问答 模拟 求职 练习",
                recommended_models=["ChatGPT", "GPT-4o"],
                favorite_count=3300,
                view_count=8700,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=19),
            ),
            Skill(
                title="AI 周报生成器",
                slug="ai-weekly-report-generator",
                summary="整理一周工作进展，快速生成结构清晰的 AI 周报和复盘内容。",
                content=build_skill_content(
                    "AI 周报生成器",
                    "整理一周工作进展，快速生成结构清晰的 AI 周报和复盘内容。",
                    "适合周报、月报和阶段性项目复盘。",
                    ["通义千问", "GPT-4o"],
                    "workflow",
                ),
                cover_icon="workflow",
                category_id=category_map["office"].id,
                difficulty="advanced",
                type="workflow",
                search_keywords="周报 工作汇报 复盘 总结 AI",
                recommended_models=["通义千问", "GPT-4o"],
                favorite_count=2200,
                view_count=6400,
                is_featured=False,
                is_hot=False,
                status="published",
                published_at=now - timedelta(days=20),
            ),
        ]
        db.add_all(skills)
        db.flush()

        skill_map = {item.slug: item for item in db.scalars(select(Skill)).all()}

        skill_tag_pairs = {
            "xiaohongshu-title-generator": ["gpt-4o", "xiaohongshu", "beginner", "prompt"],
            "python-code-explainer": ["deepseek", "beginner", "tool-config"],
            "excel-data-analysis-assistant": ["gpt-4o", "excel", "intermediate", "workflow"],
            "article-polisher": ["claude", "beginner", "prompt"],
            "midjourney-prompt-generator": ["midjourney", "beginner", "prompt"],
            "resume-optimizer-master": ["gpt-4o", "resume", "intermediate", "prompt"],
            "ppt-outline-generator": ["chatgpt", "ppt", "beginner", "workflow"],
            "short-video-script-creator": ["gpt-4o", "short-video", "intermediate", "prompt"],
            "automation-workflow-design": ["chatgpt", "advanced", "workflow"],
            "meeting-notes-assistant": ["kimi", "meeting", "beginner", "workflow"],
            "prd-generator": ["deepseek", "intermediate", "workflow"],
            "email-polisher": ["claude", "beginner", "prompt"],
            "paper-outline-generator": ["gemini", "paper", "beginner", "tutorial"],
            "social-content-calendar-generator": ["qwen", "social-media", "intermediate", "workflow"],
            "code-comment-generator": ["deepseek", "beginner", "tool-config"],
            "seo-title-generator": ["chatgpt", "seo", "beginner", "prompt"],
            "ecommerce-detail-copy-generator": ["claude", "ecommerce", "intermediate", "prompt"],
            "study-plan-assistant": ["kimi", "beginner", "tutorial"],
            "interview-qa-simulator": ["chatgpt", "resume", "intermediate", "agent"],
            "ai-weekly-report-generator": ["qwen", "advanced", "workflow"],
        }

        skill_tags = []
        for skill_slug, tag_slugs in skill_tag_pairs.items():
            for tag_slug in tag_slugs:
                skill_tags.append(SkillTag(skill_id=skill_map[skill_slug].id, tag_id=tag_map[tag_slug].id))
        db.add_all(skill_tags)

        tutorials = [
            Tutorial(
                title="零基础学会写 Prompt",
                slug="prompt-basic",
                summary="从提示词基础到进阶技巧，写出更聪明的 Prompt，让 AI 更懂你。",
                chapter_count=5,
                duration_minutes=20,
                is_beginner=True,
                is_featured=True,
                status="published",
                published_at=now - timedelta(days=1),
            ),
            Tutorial(
                title="如何用 AI 提升办公效率",
                slug="ai-office-boost",
                summary="掌握 AI 在表格、文档、PPT、纪要中的高效应用方法。",
                chapter_count=6,
                duration_minutes=25,
                is_beginner=True,
                is_featured=True,
                status="published",
                published_at=now - timedelta(days=2),
            ),
            Tutorial(
                title="从 0 到 1 搭建个人 AI 工作流",
                slug="personal-ai-workflow",
                summary="学习将提示词、工具与流程组合起来，搭建属于你的 AI 工作流。",
                chapter_count=7,
                duration_minutes=35,
                is_beginner=True,
                is_featured=True,
                status="published",
                published_at=now - timedelta(days=3),
            ),
        ]
        db.add_all(tutorials)

        db.add(
            HomepageStats(
                skill_favorites=10000,
                quality_templates=2000,
                monthly_visits=50000,
                beginner_tutorials=30,
                is_active=True,
            )
        )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
