from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.modules.tutorial.models import (
    LearningPath,
    Tutorial,
    TutorialCategory,
    TutorialPromptBlock,
    TutorialRelatedItem,
    TutorialTag,
    TutorialTagRelation,
)


def tutorial_markdown(title: str, intro: str, section_two: str, section_three: str, section_four: str, section_five: str) -> str:
    return f"""## 1. 先理解问题

{intro}

> 小贴士：先把目标、对象和输出结果说清楚，再让 AI 或工具执行，成功率会高很多。

## 2. 核心方法

{section_two}

## 3. 实战示例

{section_three}

## 4. 常见问题与避坑

{section_four}

## 5. 进阶学习建议

{section_five}
"""


def main() -> None:
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    try:
        db.execute(delete(TutorialRelatedItem))
        db.execute(delete(TutorialPromptBlock))
        db.execute(delete(TutorialTagRelation))
        db.execute(delete(Tutorial))
        db.execute(delete(TutorialTag))
        db.execute(delete(LearningPath))
        db.execute(delete(TutorialCategory))

        categories = [
            TutorialCategory(name="入门教程", slug="beginner", icon="category-beginner", color="blue", description="从 0 开始的 AI 基础教程", tutorial_count=12, sort_order=1),
            TutorialCategory(name="提示词技巧", slug="prompt", icon="category-prompt", color="purple", description="提示词写法与优化", tutorial_count=32, sort_order=2),
            TutorialCategory(name="工具使用", slug="tools", icon="category-tool", color="emerald", description="AI 工具配置与实操", tutorial_count=18, sort_order=3),
            TutorialCategory(name="工作流搭建", slug="workflow", icon="category-workflow", color="indigo", description="自动化流程与效率提升", tutorial_count=15, sort_order=4),
            TutorialCategory(name="行业应用", slug="industry", icon="category-industry", color="orange", description="行业内的 AI 应用案例", tutorial_count=20, sort_order=5),
            TutorialCategory(name="进阶提升", slug="advanced", icon="category-advanced", color="rose", description="更复杂的进阶实践", tutorial_count=14, sort_order=6),
            TutorialCategory(name="案例实战", slug="cases", icon="category-case", color="cyan", description="从案例中学习完整方法", tutorial_count=17, sort_order=7),
        ]
        db.add_all(categories)
        db.flush()

        category_map = {item.slug: item for item in db.scalars(select(TutorialCategory)).all()}

        tags = [
            TutorialTag(name="ChatGPT", slug="chatgpt", tutorial_count=36, is_hot=True, sort_order=1),
            TutorialTag(name="提示词", slug="prompt", tutorial_count=28, is_hot=True, sort_order=2),
            TutorialTag(name="Midjourney", slug="midjourney", tutorial_count=18, is_hot=True, sort_order=3),
            TutorialTag(name="工作流", slug="workflow", tutorial_count=16, is_hot=True, sort_order=4),
            TutorialTag(name="Excel", slug="excel", tutorial_count=14, is_hot=True, sort_order=5),
            TutorialTag(name="数据分析", slug="data-analysis", tutorial_count=12, is_hot=True, sort_order=6),
            TutorialTag(name="小红书", slug="xiaohongshu", tutorial_count=10, is_hot=True, sort_order=7),
            TutorialTag(name="Python", slug="python", tutorial_count=10, is_hot=True, sort_order=8),
            TutorialTag(name="AI API", slug="ai-api", tutorial_count=9, is_hot=True, sort_order=9),
            TutorialTag(name="自动化", slug="automation", tutorial_count=8, is_hot=True, sort_order=10),
            TutorialTag(name="Agent", slug="agent", tutorial_count=8, is_hot=True, sort_order=11),
            TutorialTag(name="办公效率", slug="office-efficiency", tutorial_count=7, is_hot=True, sort_order=12),
            TutorialTag(name="内容创作", slug="content-creation", tutorial_count=7, is_hot=True, sort_order=13),
            TutorialTag(name="运营", slug="operations", tutorial_count=6, is_hot=True, sort_order=14),
            TutorialTag(name="设计", slug="design", tutorial_count=6, is_hot=True, sort_order=15),
            TutorialTag(name="编程", slug="coding", tutorial_count=6, is_hot=True, sort_order=16),
        ]
        db.add_all(tags)
        db.flush()
        tag_map = {item.slug: item for item in db.scalars(select(TutorialTag)).all()}

        tutorials = [
            Tutorial(
                title="ChatGPT 提示词入门：从一句话到高质量 Prompt",
                slug="chatgpt-prompt-beginner",
                summary="从角色设定、任务描述、示例约束、示例结构四个部分，学会写出稳定可复用的提示词，让 AI 输出更准确、更高质量的结果。",
                content_markdown=tutorial_markdown(
                    "ChatGPT 提示词入门",
                    "提示词就是你给 AI 的任务说明。说明越清楚，AI 越容易理解你的目标、边界和输出方式。",
                    "高质量 Prompt 通常包含四个部分：角色设定、任务描述、输出格式、约束条件。先让 AI 知道它是谁，再告诉它要解决什么问题。",
                    "不要只写“帮我写一篇小红书笔记”。可以改成“你是一名小红书运营，请为刚入职的白领写一篇 AI 提升效率的笔记，口语化，含 3 个技巧和总结”。",
                    "最常见的问题是任务太泛、没有交代人群、没有限制格式、没有示例。这样会让输出变得空泛、不稳定。",
                    "拿自己工作里最常见的一项任务，把 Prompt 按四步法重写一遍，再对比结果差异。",
                ),
                cover_image="/icons/tutorials/cover-chatgpt-prompt.svg",
                cover_icon="chatgpt",
                category_id=category_map["prompt"].id,
                difficulty="beginner",
                read_time_minutes=12,
                view_count=23600,
                favorite_count=1200,
                like_count=128,
                is_featured=True,
                is_beginner=True,
                learning_points=[
                    "理解提示词的核心结构和设计原则",
                    "掌握四步法编写高质量 Prompt",
                    "通过示例对比优化 Prompt 的方法",
                    "解决常见问题和避坑技巧",
                ],
                suitable_for=[
                    "AI 新手，想快速上手 ChatGPT",
                    "希望让 AI 输出更稳定、更有结构的用户",
                    "内容创作者、运营、设计师、开发者等",
                ],
                search_keywords="ChatGPT 提示词 Prompt 入门",
                seo_title="ChatGPT 提示词入门教程",
                seo_description="学习如何写出高质量 ChatGPT Prompt，掌握结构、示例和优化方法。",
                status="published",
                published_at=now - timedelta(days=1),
            ),
            Tutorial(
                title="Midjourney 绘图完整指南：从入门到精通",
                slug="midjourney-guide-complete",
                summary="从账号注册、界面使用、提示词结构、风格优化、控制参数和高清放大，带你全面掌握 MJ 绘图技巧。",
                content_markdown=tutorial_markdown(
                    "Midjourney 绘图完整指南",
                    "Midjourney 的核心不是背参数，而是先建立稳定的提示词结构，再通过小步迭代去控制结果。",
                    "提示词可以拆成主体、场景、风格、光线、镜头、参数六部分。不要一次塞太多风格词，否则你很难知道是哪一段起了作用。",
                    "先用简单提示词得到第一版图，再逐步补充构图、材质、色调和画幅参数，这样更容易得到可复用的风格。",
                    "很多人会一次改太多变量，结果不知道什么让图片变好了。每轮只改 1 到 2 个关键点，效率最高。",
                    "把你最常用的风格词和参数沉淀成模板，后面做海报、封面、产品图时能直接复用。",
                ),
                cover_image="/icons/tutorials/cover-midjourney-guide.svg",
                cover_icon="midjourney",
                category_id=category_map["tools"].id,
                difficulty="intermediate",
                read_time_minutes=15,
                view_count=18900,
                favorite_count=986,
                like_count=96,
                is_featured=True,
                is_beginner=False,
                learning_points=[
                    "掌握 Midjourney 的基础工作流",
                    "理解风格词和参数对结果的影响",
                    "建立可复用的绘图提示词结构",
                ],
                suitable_for=[
                    "设计师和视觉内容创作者",
                    "想系统学习 AI 绘图的用户",
                    "需要提高出图效率的小团队",
                ],
                search_keywords="Midjourney 绘图 AI 设计",
                seo_title="Midjourney 绘图完整指南",
                seo_description="系统学习 Midjourney 提示词结构、风格控制和参数使用方法。",
                status="published",
                published_at=now - timedelta(days=2),
            ),
            Tutorial(
                title="工作流搭建实战：用 n8n 实现自动化任务",
                slug="n8n-workflow-automation",
                summary="通过 3 个实战案例，带你掌握 n8n 的核心节点与工作流搭建思路，实现日常任务自动化，提升效率。",
                content_markdown=tutorial_markdown(
                    "工作流搭建实战",
                    "做自动化时，先别想着一口气搭完整系统。先明确输入、处理逻辑和输出结果，工作流就容易拆清楚。",
                    "n8n 的核心是触发器、节点和分支逻辑。把每个节点职责控制在最小范围内，后续维护会轻松很多。",
                    "适合让 AI 参与的环节通常是分类、提取、改写和总结；适合规则节点处理的部分，则应尽量保持确定性。",
                    "一上来就做超长流程最容易失控。先把关键节点单独跑通，再合并成完整链路，排错成本更低。",
                    "建议为每条工作流记录失败点、重试方式和人工兜底策略，这样才能真正用于日常业务。",
                ),
                cover_image="/icons/tutorials/cover-workflow-guide.svg",
                cover_icon="workflow",
                category_id=category_map["workflow"].id,
                difficulty="intermediate",
                read_time_minutes=18,
                view_count=15300,
                favorite_count=754,
                like_count=81,
                is_featured=True,
                is_beginner=False,
                learning_points=[
                    "理解触发器、动作和分支节点的关系",
                    "掌握更稳定的工作流设计思路",
                    "知道哪些环节适合接入 AI 能力",
                ],
                suitable_for=[
                    "做运营自动化和流程搭建的同学",
                    "想接入 AI 节点的工作流实践者",
                    "需要连接表单、表格、通知和内容系统的团队",
                ],
                search_keywords="n8n 工作流 自动化",
                seo_title="n8n 自动化工作流实战教程",
                seo_description="学习如何设计稳定、可维护的 n8n 自动化工作流，并合理接入 AI 节点。",
                status="published",
                published_at=now - timedelta(days=3),
            ),
            Tutorial(
                title="Excel + AI 数据分析：从数据到洞察",
                slug="excel-ai-data-analysis",
                summary="结合 AI 工具，快速完成数据清洗、分析和可视化，让 Excel 处理数据更高效。",
                content_markdown=tutorial_markdown(
                    "Excel + AI 数据分析",
                    "AI 可以显著加快分析效率，但前提是表格数据足够干净、字段命名一致、问题定义明确。",
                    "先让 Excel 处理结构化工作，比如筛选、透视、公式和清洗；再让 AI 帮你做趋势总结、异常解读和报告草稿。",
                    "把业务问题说清楚，比如“请总结近 4 周订单量变化、异常渠道和建议动作”，比“帮我分析一下”有效得多。",
                    "AI 给出的洞察需要回到原始数据做验证，尤其是涉及业务结论、预算决策和异常判断时，不能直接照搬。",
                    "把常用分析问题、输出格式和汇报模板沉淀下来，就能形成团队可复用的数据分析流程。",
                ),
                cover_image="/icons/tutorials/cover-excel-ai.svg",
                cover_icon="excel",
                category_id=category_map["industry"].id,
                difficulty="beginner",
                read_time_minutes=14,
                view_count=12700,
                favorite_count=632,
                like_count=64,
                is_featured=False,
                is_beginner=True,
                learning_points=[
                    "理解 Excel 与 AI 的分工方式",
                    "提高数据清洗和摘要生成效率",
                    "建立可复用的数据分析提问模板",
                ],
                suitable_for=[
                    "经常处理表格和报表的运营、分析师",
                    "想提高数据汇总效率的业务同学",
                    "需要周报、月报自动化辅助的团队",
                ],
                search_keywords="Excel AI 数据分析",
                seo_title="Excel + AI 数据分析教程",
                seo_description="学习如何用 Excel 和 AI 协同完成数据清洗、分析和报告输出。",
                status="published",
                published_at=now - timedelta(days=4),
            ),
            Tutorial(
                title="小红书 AI 爆款内容创作全攻略",
                slug="xiaohongshu-ai-content-guide",
                summary="从选题、标题、正文到封面图，利用 AI 提升内容创作效率，打造爆款笔记。",
                content_markdown=tutorial_markdown(
                    "小红书 AI 内容创作",
                    "AI 真正节省时间的地方，往往不是直接写正文，而是前面的选题、标题角度和内容结构设计。",
                    "先定义账号人设、受众、语气和内容目标，再让 AI 输出标题、提纲和段落，内容质量会稳定很多。",
                    "建议先批量生成多个标题方向，再筛出最适合的角度继续写正文，最后再做封面文案和开头优化。",
                    "常见问题是 AI 文案太像模板，缺少真实感。这个时候要补充个人经验、具体场景和真实细节。",
                    "把选题、标题、提纲、正文、封面图这一套流程拆成模板，后续做内容矩阵会轻松很多。",
                ),
                cover_image="/icons/tutorials/cover-xiaohongshu-writing.svg",
                cover_icon="xiaohongshu",
                category_id=category_map["cases"].id,
                difficulty="beginner",
                read_time_minutes=16,
                view_count=9800,
                favorite_count=512,
                like_count=57,
                is_featured=False,
                is_beginner=True,
                learning_points=[
                    "用 AI 提高选题和标题效率",
                    "让内容结构更适合平台阅读习惯",
                    "把内容生产拆成可复用的流程",
                ],
                suitable_for=[
                    "小红书创作者和内容运营",
                    "内容产能有限的小团队",
                    "希望用 AI 辅助内容创作的品牌方",
                ],
                search_keywords="小红书 AI 内容创作 运营",
                seo_title="小红书 AI 内容创作教程",
                seo_description="学习如何用 AI 做小红书选题、标题、正文和封面文案，提高内容效率。",
                status="published",
                published_at=now - timedelta(days=5),
            ),
            Tutorial(
                title="Python + AI 实战：构建智能应用",
                slug="python-ai-app-practice",
                summary="使用 Python 结合 OpenAI API，快速构建聊天机器人、文本分析等智能应用。",
                content_markdown=tutorial_markdown(
                    "Python + AI 实战",
                    "做 AI 应用时，最重要的不是功能堆砌，而是先选一个足够聚焦的使用场景，比如摘要、分类、抽取或问答。",
                    "建议把 Prompt 模板和程序逻辑分离，Python 负责参数校验、调用接口、重试和结构化结果处理。",
                    "如果后续还要给系统继续消费，就尽量让模型返回结构化 JSON，而不是只返回自然语言段落。",
                    "很多项目早期没有日志和失败记录，后面很难定位问题。哪怕 MVP，也应该先把关键输入输出记下来。",
                    "先把完整闭环做通，再逐步优化 Prompt、缓存、延迟和交互体验，不要一开始就过度设计。",
                ),
                cover_image="/icons/tutorials/cover-python-ai.svg",
                cover_icon="python",
                category_id=category_map["advanced"].id,
                difficulty="advanced",
                read_time_minutes=20,
                view_count=8200,
                favorite_count=423,
                like_count=49,
                is_featured=False,
                is_beginner=False,
                learning_points=[
                    "理解 AI 应用的最小组成结构",
                    "掌握 Python 连接 Prompt 与 API 的方式",
                    "知道如何从 Demo 走向更稳定的应用形态",
                ],
                suitable_for=[
                    "想做 AI 产品原型的开发者",
                    "给内部工具加上 LLM 能力的工程师",
                    "想快速验证创意的独立开发者",
                ],
                search_keywords="Python AI OpenAI API 智能应用",
                seo_title="Python + AI 应用实战教程",
                seo_description="学习如何使用 Python 和 OpenAI API 快速构建实用的 AI 应用。",
                status="published",
                published_at=now - timedelta(days=6),
            ),
        ]
        db.add_all(tutorials)
        db.flush()

        tutorial_map = {item.slug: item for item in db.scalars(select(Tutorial)).all()}

        relations = [
            ("chatgpt-prompt-beginner", ["chatgpt", "prompt"]),
            ("midjourney-guide-complete", ["midjourney", "design"]),
            ("n8n-workflow-automation", ["workflow", "automation", "agent"]),
            ("excel-ai-data-analysis", ["excel", "data-analysis", "office-efficiency"]),
            ("xiaohongshu-ai-content-guide", ["xiaohongshu", "content-creation", "operations"]),
            ("python-ai-app-practice", ["python", "ai-api", "coding"]),
        ]
        for tutorial_slug, tutorial_tags in relations:
            for tag_slug in tutorial_tags:
                db.add(TutorialTagRelation(tutorial_id=tutorial_map[tutorial_slug].id, tag_id=tag_map[tag_slug].id))

        prompt_blocks = [
            (
                "chatgpt-prompt-beginner",
                "小红书标题生成 Prompt",
                "适合在 ChatGPT 中直接使用",
                "你是一名资深小红书运营专家，请帮我生成 10 个关于“如何用 AI 提升工作效率”的小红书标题。要求：口语化、有点击欲望、不夸大，适合新手白领。",
            ),
            (
                "midjourney-guide-complete",
                "产品海报 Prompt",
                "适合测试构图和风格",
                "一款高端无线耳机放在极简办公桌上，柔和自然光，商业摄影风格，材质真实，细节清晰，浅景深 --ar 4:5 --stylize 150",
            ),
            (
                "n8n-workflow-automation",
                "邮件分类 Prompt",
                "适合放进 AI 节点",
                "请将以下邮件分类到 sales、support、billing、partnership、spam 其中之一，并返回 JSON：{label, confidence}。",
            ),
            (
                "excel-ai-data-analysis",
                "报表摘要 Prompt",
                "把表格快速整理成业务摘要",
                "你是一名业务分析师，请根据这份销售表格总结 3 个核心趋势、1 个异常点，以及 2 条后续建议，输出简洁商务风。",
            ),
            (
                "xiaohongshu-ai-content-guide",
                "标题批量生成 Prompt",
                "先出多个方向再筛选",
                "你是一名小红书增长编辑，请为“AI 提升办公室效率”这个主题生成 12 个标题，混合实用型、好奇型、情绪型角度，避免标题党。",
            ),
            (
                "python-ai-app-practice",
                "结构化抽取 Prompt",
                "适合 Python + LLM 流程",
                "请从以下客户消息中提取姓名、产品、紧急程度和期望动作，只返回合法 JSON。",
            ),
        ]
        for tutorial_slug, title, description, content in prompt_blocks:
            db.add(
                TutorialPromptBlock(
                    tutorial_id=tutorial_map[tutorial_slug].id,
                    title=title,
                    description=description,
                    content=content,
                    sort_order=1,
                )
            )

        related_map = {
            "chatgpt-prompt-beginner": [
                "midjourney-guide-complete",
                "n8n-workflow-automation",
                "excel-ai-data-analysis",
            ],
            "midjourney-guide-complete": [
                "chatgpt-prompt-beginner",
                "xiaohongshu-ai-content-guide",
                "python-ai-app-practice",
            ],
            "n8n-workflow-automation": [
                "chatgpt-prompt-beginner",
                "excel-ai-data-analysis",
                "python-ai-app-practice",
            ],
            "excel-ai-data-analysis": [
                "chatgpt-prompt-beginner",
                "n8n-workflow-automation",
                "xiaohongshu-ai-content-guide",
            ],
            "xiaohongshu-ai-content-guide": [
                "chatgpt-prompt-beginner",
                "midjourney-guide-complete",
                "excel-ai-data-analysis",
            ],
            "python-ai-app-practice": [
                "n8n-workflow-automation",
                "midjourney-guide-complete",
                "chatgpt-prompt-beginner",
            ],
        }
        for tutorial_slug, related_slugs in related_map.items():
            for index, related_slug in enumerate(related_slugs, start=1):
                db.add(
                    TutorialRelatedItem(
                        tutorial_id=tutorial_map[tutorial_slug].id,
                        related_tutorial_id=tutorial_map[related_slug].id,
                        sort_order=index,
                    )
                )

        learning_paths = [
            LearningPath(title="AI 新手入门路径", slug="ai-beginner-path", description="从 0 开始，快速掌握 AI 基础技能", icon="path-beginner", tutorial_count=12, sort_order=1),
            LearningPath(title="提示词进阶路径", slug="prompt-advanced-path", description="掌握高质量提示词写法与实战技巧", icon="path-prompt", tutorial_count=18, sort_order=2),
            LearningPath(title="工作流实战路径", slug="workflow-practice-path", description="从自动化到智能体，打造高效工作流", icon="path-workflow", tutorial_count=15, sort_order=3),
            LearningPath(title="行业应用路径", slug="industry-application-path", description="AI 在各行业的落地应用与案例", icon="path-industry", tutorial_count=20, sort_order=4),
        ]
        db.add_all(learning_paths)
        db.commit()
        print("seed_tutorials_page done")
    finally:
        db.close()


if __name__ == "__main__":
    main()
