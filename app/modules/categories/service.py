from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.tutorial.models import Tutorial, TutorialCategory, TutorialTag

from .schemas import (
    CategoryItemOut,
    CategoryListOut,
    CategoryListQueryIn,
    CategoryOverviewOut,
    CategoryOverviewStatsOut,
    CategorySidebarFilterOut,
    HotTagOut,
)


DEFAULT_LOCALE = "zh"

SCENE_LABELS: Dict[str, Dict[str, str]] = {
    "office": {"zh": "职场办公", "en": "Office Work"},
    "content": {"zh": "内容创作", "en": "Content Creation"},
    "data": {"zh": "数据分析", "en": "Data Analysis"},
    "programming": {"zh": "开发编程", "en": "Programming"},
    "learning": {"zh": "学习提升", "en": "Learning"},
    "life": {"zh": "生活娱乐", "en": "Lifestyle"},
    "tools": {"zh": "AI工具使用", "en": "AI Tools"},
    "industry": {"zh": "行业应用", "en": "Industry"},
    "automation": {"zh": "自动化", "en": "Automation"},
}

CATEGORY_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "prompt": {
        "name_en": "Prompt Skills",
        "description_en": "Learn how to write higher-quality prompts and get better AI output.",
    },
    "tools": {
        "name_en": "Tool Usage",
        "description_en": "Master practical usage patterns and best practices for AI tools.",
    },
    "workflow": {
        "name_en": "Workflow Building",
        "description_en": "Build efficient AI workflows and practical automation systems.",
    },
    "industry": {
        "name_en": "Industry Use Cases",
        "description_en": "Explore how AI is applied across industries and real workflows.",
    },
    "automation": {
        "name_en": "Automation",
        "description_en": "Learn automation techniques to improve productivity and output.",
    },
    "data-analysis": {
        "name_en": "Data Analysis",
        "description_en": "Use AI for analysis workflows, summaries, and clearer insights.",
    },
    "programming": {
        "name_en": "Programming",
        "description_en": "Learn how to use AI coding tools in practical development work.",
    },
    "ai-drawing": {
        "name_en": "AI Art",
        "description_en": "Create images and visual assets with modern AI art tools.",
    },
    "office-work": {
        "name_en": "Office Work",
        "description_en": "Boost day-to-day office work with AI tools and practical methods.",
    },
    "learning-method": {
        "name_en": "Learning Methods",
        "description_en": "Use AI to improve learning speed, retention, and knowledge workflows.",
    },
}

TAG_TRANSLATIONS: Dict[str, str] = {
    "prompt": "Prompts",
    "ai-drawing": "AI Art",
    "workflow": "Workflow",
    "data-analysis": "Data Analysis",
    "office-work": "Office Work",
}

GROUP_LABELS: Dict[str, str] = {
    "all": "All Categories",
    "hot": "Hot Categories",
    "recent": "Recently Updated",
}


def normalize_locale(locale: str) -> str:
    return locale if locale == "en" else DEFAULT_LOCALE


class CategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_category_stmt(self):
        return select(TutorialCategory).where(
            TutorialCategory.deleted_at.is_(None),
            TutorialCategory.is_enabled.is_(True),
        )

    def _published_tutorials_stmt(self):
        return select(Tutorial).where(
            Tutorial.deleted_at.is_(None),
            Tutorial.status == "published",
        )

    def _scene_label(self, value: str, locale: str) -> str:
        return SCENE_LABELS.get(value, {}).get(locale, value)

    def _category_name(self, item: TutorialCategory, locale: str) -> str:
        if locale == DEFAULT_LOCALE:
            return item.name
        return CATEGORY_TRANSLATIONS.get(item.slug, {}).get("name_en", item.name)

    def _category_description(self, item: TutorialCategory, locale: str) -> str:
        if locale == DEFAULT_LOCALE:
            return item.description
        return CATEGORY_TRANSLATIONS.get(item.slug, {}).get("description_en", item.description)

    def _tag_name(self, item: TutorialTag, locale: str) -> str:
        if locale == DEFAULT_LOCALE:
            return item.name
        return TAG_TRANSLATIONS.get(item.slug, item.name)

    def _map_category(self, item: TutorialCategory, locale: str) -> CategoryItemOut:
        return CategoryItemOut(
            id=str(item.id),
            name=self._category_name(item, locale),
            slug=item.slug,
            icon=item.icon,
            color=item.color,
            description=self._category_description(item, locale),
            tutorialCount=item.tutorial_count,
            skillCount=getattr(item, "skill_count", 0) or 0,
            sortOrder=item.sort_order,
            isEnabled=item.is_enabled,
            group=getattr(item, "category_group", None),
            scene=getattr(item, "scene", None),
            difficulty=getattr(item, "difficulty", None),
            isHot=getattr(item, "is_hot", False) or False,
        )

    def _apply_query_filters(self, rows: List[CategoryItemOut], query: CategoryListQueryIn) -> List[CategoryItemOut]:
        keyword = (query.q or "").strip().lower()
        result = rows

        if query.group and query.group != "all":
            if query.group == "hot":
                result = [item for item in result if item.isHot]
            elif query.group == "recent":
                result = [item for item in result if item.sortOrder <= 4]
            else:
                result = [item for item in result if item.group == query.group]

        if query.scene:
            result = [item for item in result if item.scene == query.scene]

        if keyword:
            result = [
                item
                for item in result
                if keyword in item.name.lower()
                or keyword in item.description.lower()
                or keyword in item.slug.lower()
            ]

        if query.sort == "tutorials":
            result.sort(key=lambda item: (-item.tutorialCount, item.sortOrder))
        elif query.sort == "alphabetical":
            result.sort(key=lambda item: item.name.lower())
        else:
            result.sort(key=lambda item: item.sortOrder)

        return result

    def get_overview(self, locale: str) -> CategoryOverviewOut:
        locale = normalize_locale(locale)
        categories = self.db.scalars(
            self._base_category_stmt().order_by(TutorialCategory.sort_order.asc(), TutorialCategory.created_at.asc())
        ).all()

        total_categories = len(categories)
        total_tutorials = int(
            self.db.scalar(
                select(func.count(Tutorial.id)).where(
                    Tutorial.deleted_at.is_(None),
                    Tutorial.status == "published",
                )
            )
            or 0
        )
        weekly_views = int(
            self.db.scalar(
                select(func.coalesce(func.sum(Tutorial.view_count), 0)).where(
                    Tutorial.deleted_at.is_(None),
                    Tutorial.status == "published",
                )
            )
            or 0
        )
        weekly_favorites = int(
            self.db.scalar(
                select(func.coalesce(func.sum(Tutorial.favorite_count), 0)).where(
                    Tutorial.deleted_at.is_(None),
                    Tutorial.status == "published",
                )
            )
            or 0
        )

        hot_count = sum(1 for item in categories if getattr(item, "is_hot", False))
        recent_count = sum(1 for item in categories if item.sort_order <= 4)

        groups = [
            CategorySidebarFilterOut(
                label="全部分类" if locale == "zh" else GROUP_LABELS["all"],
                value="all",
                count=total_categories,
            ),
            CategorySidebarFilterOut(
                label="热门分类" if locale == "zh" else GROUP_LABELS["hot"],
                value="hot",
                count=hot_count,
            ),
            CategorySidebarFilterOut(
                label="最近更新" if locale == "zh" else GROUP_LABELS["recent"],
                value="recent",
                count=recent_count,
            ),
        ]

        scenes: List[CategorySidebarFilterOut] = []
        for scene_value in SCENE_LABELS:
            count = sum(
                item.tutorial_count
                for item in categories
                if getattr(item, "scene", None) == scene_value
            )
            if count <= 0:
                continue
            scenes.append(
                CategorySidebarFilterOut(
                    label=self._scene_label(scene_value, locale),
                    value=scene_value,
                    count=count,
                )
            )

        hot_tags = self.db.scalars(
            select(TutorialTag)
            .where(
                TutorialTag.deleted_at.is_(None),
                TutorialTag.is_enabled.is_(True),
                TutorialTag.is_hot.is_(True),
                TutorialTag.slug.in_(
                    [
                        "chatgpt",
                        "midjourney",
                        "prompt",
                        "ai-drawing",
                        "automation",
                        "workflow",
                        "data-analysis",
                        "office-work",
                        "python",
                    ]
                ),
            )
            .order_by(TutorialTag.sort_order.asc(), TutorialTag.created_at.asc())
            .limit(9)
        ).all()

        return CategoryOverviewOut(
            stats=CategoryOverviewStatsOut(
                totalCategories=total_categories,
                totalTutorials=total_tutorials,
                weeklyViews=weekly_views,
                weeklyFavorites=weekly_favorites,
            ),
            groups=groups,
            scenes=scenes,
            hotTags=[
                HotTagOut(
                    id=str(item.id),
                    name=self._tag_name(item, locale),
                    slug=item.slug,
                    count=item.tutorial_count,
                )
                for item in hot_tags
            ],
        )

    def get_categories(self, query: CategoryListQueryIn) -> CategoryListOut:
        rows = self.db.scalars(
            self._base_category_stmt().order_by(TutorialCategory.sort_order.asc(), TutorialCategory.created_at.asc())
        ).all()
        items = [self._map_category(item, normalize_locale(query.locale)) for item in rows]
        filtered = self._apply_query_filters(items, query)
        return CategoryListOut(list=filtered)
