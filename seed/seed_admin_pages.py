from __future__ import annotations

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.tutorial.models import LearningPath, TutorialCategory, TutorialTag


def upsert_by_slug(db, model, payload: dict):
    item = db.scalar(select(model).where(model.slug == payload["slug"]))
    if item is None:
        item = model(**payload)
        db.add(item)
        return
    for key, value in payload.items():
        setattr(item, key, value)


def main() -> None:
    db = SessionLocal()
    try:
        categories = [
            {
                "name": "提示词技巧",
                "slug": "prompt",
                "icon": "category-prompt",
                "color": "#3B82F6",
                "description": "学习如何编写高质量提示词，提升 AI 输出效果",
                "category_group": "all",
                "scene": "content",
                "difficulty": "beginner",
                "tutorial_count": 128,
                "skill_count": 0,
                "is_hot": True,
                "is_enabled": True,
                "sort_order": 1,
            },
            {
                "name": "工具使用",
                "slug": "tools",
                "icon": "category-tools",
                "color": "#22C55E",
                "description": "掌握各类 AI 工具的使用方法和最佳实践",
                "category_group": "tools",
                "scene": "office",
                "difficulty": "beginner",
                "tutorial_count": 96,
                "skill_count": 0,
                "is_hot": True,
                "is_enabled": True,
                "sort_order": 2,
            },
            {
                "name": "工作流搭建",
                "slug": "workflow",
                "icon": "category-workflow",
                "color": "#8B5CF6",
                "description": "学习构建高效的 AI 工作流和自动化方案",
                "category_group": "automation",
                "scene": "office",
                "difficulty": "intermediate",
                "tutorial_count": 85,
                "skill_count": 0,
                "is_hot": True,
                "is_enabled": True,
                "sort_order": 3,
            },
            {
                "name": "行业应用",
                "slug": "industry",
                "icon": "category-industry",
                "color": "#F59E0B",
                "description": "探索 AI 在各个行业的应用场景和解决方案",
                "category_group": "industry",
                "scene": "content",
                "difficulty": "intermediate",
                "tutorial_count": 64,
                "skill_count": 0,
                "is_hot": True,
                "is_enabled": True,
                "sort_order": 4,
            },
            {
                "name": "自动化",
                "slug": "automation",
                "icon": "category-automation",
                "color": "#EF4444",
                "description": "学习自动化技术，提升工作效率和生产力",
                "category_group": "automation",
                "scene": "office",
                "difficulty": "intermediate",
                "tutorial_count": 52,
                "skill_count": 0,
                "is_hot": True,
                "is_enabled": True,
                "sort_order": 5,
            },
            {
                "name": "数据分析",
                "slug": "data-analysis",
                "icon": "category-data",
                "color": "#06B6D4",
                "description": "掌握 AI 驱动的数据分析方法和可视化技巧",
                "category_group": "data",
                "scene": "data",
                "difficulty": "beginner",
                "tutorial_count": 47,
                "skill_count": 0,
                "is_hot": False,
                "is_enabled": True,
                "sort_order": 6,
            },
            {
                "name": "编程开发",
                "slug": "programming",
                "icon": "category-programming",
                "color": "#2563EB",
                "description": "学习 AI 编程辅助开发工具的使用方法",
                "category_group": "programming",
                "scene": "programming",
                "difficulty": "intermediate",
                "tutorial_count": 73,
                "skill_count": 0,
                "is_hot": False,
                "is_enabled": True,
                "sort_order": 7,
            },
            {
                "name": "AI 绘画",
                "slug": "ai-drawing",
                "icon": "category-ai-drawing",
                "color": "#EC4899",
                "description": "使用 AI 工具进行图像创作和设计制作",
                "category_group": "content",
                "scene": "content",
                "difficulty": "beginner",
                "tutorial_count": 38,
                "skill_count": 0,
                "is_hot": False,
                "is_enabled": True,
                "sort_order": 8,
            },
            {
                "name": "职场办公",
                "slug": "office-work",
                "icon": "category-office",
                "color": "#0EA5E9",
                "description": "提升职场效率的 AI 工具和方法技巧",
                "category_group": "office",
                "scene": "office",
                "difficulty": "beginner",
                "tutorial_count": 61,
                "skill_count": 0,
                "is_hot": False,
                "is_enabled": True,
                "sort_order": 9,
            },
            {
                "name": "学习方法",
                "slug": "learning-method",
                "icon": "category-learning",
                "color": "#8B5CF6",
                "description": "利用 AI 提升学习效率和知识管理能力",
                "category_group": "learning",
                "scene": "learning",
                "difficulty": "advanced",
                "tutorial_count": 34,
                "skill_count": 0,
                "is_hot": False,
                "is_enabled": True,
                "sort_order": 10,
            },
        ]

        tags = [
            {"name": "ChatGPT", "slug": "chatgpt", "tutorial_count": 156, "is_hot": True, "is_enabled": True, "sort_order": 1},
            {"name": "Midjourney", "slug": "midjourney", "tutorial_count": 89, "is_hot": True, "is_enabled": True, "sort_order": 2},
            {"name": "提示词", "slug": "prompt", "tutorial_count": 234, "is_hot": True, "is_enabled": True, "sort_order": 3},
            {"name": "AI绘画", "slug": "ai-drawing", "tutorial_count": 67, "is_hot": True, "is_enabled": True, "sort_order": 4},
            {"name": "自动化", "slug": "automation", "tutorial_count": 45, "is_hot": True, "is_enabled": True, "sort_order": 5},
            {"name": "工作流", "slug": "workflow", "tutorial_count": 78, "is_hot": True, "is_enabled": True, "sort_order": 6},
            {"name": "数据分析", "slug": "data-analysis", "tutorial_count": 56, "is_hot": True, "is_enabled": True, "sort_order": 7},
            {"name": "职场办公", "slug": "office-work", "tutorial_count": 123, "is_hot": True, "is_enabled": True, "sort_order": 8},
            {"name": "Python", "slug": "python", "tutorial_count": 34, "is_hot": True, "is_enabled": True, "sort_order": 9},
        ]

        learning_paths = [
            {
                "title": "AI 新手入门路径",
                "slug": "ai-beginner-path",
                "description": "从 0 开始，快速掌握 AI 基础技能",
                "icon": "path-beginner",
                "tutorial_count": 12,
                "is_enabled": True,
                "sort_order": 1,
            },
            {
                "title": "提示词进阶路径",
                "slug": "prompt-advanced-path",
                "description": "掌握高质量提示词写法与实战技巧",
                "icon": "path-prompt",
                "tutorial_count": 18,
                "is_enabled": True,
                "sort_order": 2,
            },
            {
                "title": "工作流实战路径",
                "slug": "workflow-practice-path",
                "description": "从自动化到智能体，打造高效工作流",
                "icon": "path-workflow",
                "tutorial_count": 15,
                "is_enabled": True,
                "sort_order": 3,
            },
            {
                "title": "行业应用路径",
                "slug": "industry-application-path",
                "description": "AI 在各行业的落地应用与案例",
                "icon": "path-industry",
                "tutorial_count": 20,
                "is_enabled": True,
                "sort_order": 4,
            },
        ]

        for payload in categories:
            upsert_by_slug(db, TutorialCategory, payload)

        for payload in tags:
            upsert_by_slug(db, TutorialTag, payload)

        for payload in learning_paths:
            upsert_by_slug(db, LearningPath, payload)

        db.commit()
        print(
            "seed_admin_pages done",
            f"categories={len(categories)}",
            f"tags={len(tags)}",
            f"learning_paths={len(learning_paths)}",
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
