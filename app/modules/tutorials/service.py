from typing import Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.modules.tutorial.models import (
    LearningPath,
    Tutorial,
    TutorialCategory,
    TutorialPromptBlock,
    TutorialRelatedItem,
    TutorialTag,
    TutorialTagRelation,
)
from app.modules.tutorials.i18n import (
    AUTHOR_BY_LOCALE,
    DEFAULT_TUTORIAL_LOCALE,
    HOT_KEYWORDS_BY_LOCALE,
    LEARNING_PATH_TRANSLATIONS,
    TUTORIAL_CATEGORY_TRANSLATIONS,
    TUTORIAL_TAG_TRANSLATIONS,
    TUTORIAL_TRANSLATIONS,
    get_detail_translation,
    get_localized_list,
    normalize_tutorial_locale,
)
from app.modules.tutorials.schemas import (
    LearningPathOut,
    PaginationOut,
    TutorialAuthorOut,
    TutorialCategoryOut,
    TutorialDetailOut,
    TutorialFilterOptionOut,
    TutorialFiltersOut,
    TutorialListItemOut,
    TutorialListOut,
    TutorialPrevNextItemOut,
    TutorialPrevNextOut,
    TutorialPromptBlockOut,
    TutorialQueryIn,
    TutorialRelatedItemOut,
    TutorialTagOut,
    WeeklyHotTutorialOut,
    TutorialHelpfulIn,
)
from app.modules.track.models import TrackingEvent


class TutorialService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_query(self) -> Select:
        return (
            select(Tutorial.id)
            .join(TutorialCategory, Tutorial.category_id == TutorialCategory.id)
            .where(
                Tutorial.status == "published",
                Tutorial.deleted_at.is_(None),
                TutorialCategory.deleted_at.is_(None),
                TutorialCategory.is_enabled.is_(True),
            )
        )

    def _apply_filters(self, stmt: Select, query: TutorialQueryIn) -> Select:
        if query.category and query.category != "all":
            stmt = stmt.where(TutorialCategory.slug == query.category)

        if query.tag:
            stmt = stmt.where(
                Tutorial.id.in_(
                    select(TutorialTagRelation.tutorial_id)
                    .join(TutorialTag, TutorialTagRelation.tag_id == TutorialTag.id)
                    .where(TutorialTag.slug == query.tag, TutorialTag.deleted_at.is_(None), TutorialTag.is_enabled.is_(True))
                )
            )

        return stmt

    def _get_localized_tutorial_title(self, tutorial: Tutorial, locale: str) -> str:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return tutorial.title
        return TUTORIAL_TRANSLATIONS.get(tutorial.slug, {}).get("title_en", tutorial.title)

    def _get_localized_tutorial_summary(self, tutorial: Tutorial, locale: str) -> str:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return tutorial.summary
        return TUTORIAL_TRANSLATIONS.get(tutorial.slug, {}).get("summary_en", tutorial.summary)

    def _get_localized_tutorial_keywords(self, tutorial: Tutorial, locale: str) -> str:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return tutorial.search_keywords or ""
        fallback = tutorial.search_keywords or ""
        return TUTORIAL_TRANSLATIONS.get(tutorial.slug, {}).get("keywords_en", fallback)

    def _get_localized_tutorial_content(self, tutorial: Tutorial, locale: str) -> str:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return tutorial.content_markdown
        detail = get_detail_translation(tutorial.slug, locale)
        return str(detail.get("content_markdown_en", tutorial.content_markdown))

    def _get_localized_learning_points(self, tutorial: Tutorial, locale: str) -> List[str]:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return [str(item) for item in tutorial.learning_points or []]
        detail = get_detail_translation(tutorial.slug, locale)
        return get_localized_list(detail, "learning_points_en") or [str(item) for item in tutorial.learning_points or []]

    def _get_localized_suitable_for(self, tutorial: Tutorial, locale: str) -> List[str]:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return [str(item) for item in tutorial.suitable_for or []]
        detail = get_detail_translation(tutorial.slug, locale)
        return get_localized_list(detail, "suitable_for_en") or [str(item) for item in tutorial.suitable_for or []]

    def _get_localized_tutorial_seo_title(self, tutorial: Tutorial, locale: str) -> Optional[str]:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return tutorial.seo_title
        detail = get_detail_translation(tutorial.slug, locale)
        return detail.get("seo_title_en", tutorial.seo_title)  # type: ignore[return-value]

    def _get_localized_tutorial_seo_description(self, tutorial: Tutorial, locale: str) -> Optional[str]:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return tutorial.seo_description
        detail = get_detail_translation(tutorial.slug, locale)
        return detail.get("seo_description_en", tutorial.seo_description)  # type: ignore[return-value]

    def _get_localized_category_name(self, category: TutorialCategory, locale: str) -> str:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return category.name
        return TUTORIAL_CATEGORY_TRANSLATIONS.get(category.slug, {}).get("name_en", category.name)

    def _get_localized_tag_name(self, tag: TutorialTag, locale: str) -> str:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return tag.name
        return TUTORIAL_TAG_TRANSLATIONS.get(tag.slug, {}).get("name_en", tag.name)

    def _get_localized_learning_path_title(self, path: LearningPath, locale: str) -> str:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return path.title
        return LEARNING_PATH_TRANSLATIONS.get(path.slug, {}).get("title_en", path.title)

    def _get_localized_learning_path_description(self, path: LearningPath, locale: str) -> str:
        if locale == DEFAULT_TUTORIAL_LOCALE:
            return path.description
        return LEARNING_PATH_TRANSLATIONS.get(path.slug, {}).get("description_en", path.description)

    def _matches_search(self, tutorial: Tutorial, locale: str, query_text: str) -> bool:
        keyword = query_text.strip().lower()
        if not keyword:
            return True

        haystack = " ".join(
            [
                self._get_localized_tutorial_title(tutorial, locale),
                self._get_localized_tutorial_summary(tutorial, locale),
                self._get_localized_tutorial_keywords(tutorial, locale),
            ]
        ).lower()
        return keyword in haystack

    def _map_tags_by_tutorial(self, tutorial_ids: Sequence[UUID], locale: str) -> Dict[UUID, List[TutorialTagOut]]:
        if not tutorial_ids:
            return {}

        rows = self.db.execute(
            select(TutorialTagRelation.tutorial_id, TutorialTag)
            .join(TutorialTag, TutorialTagRelation.tag_id == TutorialTag.id)
            .where(
                TutorialTagRelation.tutorial_id.in_(list(tutorial_ids)),
                TutorialTag.deleted_at.is_(None),
                TutorialTag.is_enabled.is_(True),
            )
            .order_by(TutorialTag.sort_order.asc(), TutorialTag.created_at.asc())
        ).all()

        result: Dict[UUID, List[TutorialTagOut]] = {}
        for tutorial_id, tag in rows:
            result.setdefault(tutorial_id, []).append(
                TutorialTagOut(
                    id=str(tag.id),
                    name=self._get_localized_tag_name(tag, locale),
                    slug=tag.slug,
                )
            )
        return result

    def _get_prompt_blocks(self, tutorial: Tutorial, locale: str) -> List[TutorialPromptBlockOut]:
        rows = self.db.scalars(
            select(TutorialPromptBlock)
            .where(TutorialPromptBlock.tutorial_id == tutorial.id, TutorialPromptBlock.deleted_at.is_(None))
            .order_by(TutorialPromptBlock.sort_order.asc(), TutorialPromptBlock.created_at.asc())
        ).all()

        translations = get_detail_translation(tutorial.slug, locale).get("prompt_blocks_en", [])
        translated_blocks = translations if isinstance(translations, list) else []

        result: List[TutorialPromptBlockOut] = []
        for index, item in enumerate(rows):
            translated = translated_blocks[index] if locale != DEFAULT_TUTORIAL_LOCALE and index < len(translated_blocks) else {}
            if not isinstance(translated, dict):
                translated = {}
            result.append(
                TutorialPromptBlockOut(
                    id=str(item.id),
                    title=str(translated.get("title", item.title)),
                    description=str(translated["description"]) if translated.get("description") is not None else item.description,
                    content=str(translated.get("content", item.content)),
                    sortOrder=item.sort_order,
                )
            )
        return result

    def _get_related_tutorials(self, tutorial: Tutorial, locale: str) -> List[TutorialRelatedItemOut]:
        rows = self.db.execute(
            select(TutorialRelatedItem, Tutorial)
            .join(Tutorial, TutorialRelatedItem.related_tutorial_id == Tutorial.id)
            .where(
                TutorialRelatedItem.tutorial_id == tutorial.id,
                Tutorial.status == "published",
                Tutorial.deleted_at.is_(None),
            )
            .order_by(TutorialRelatedItem.sort_order.asc(), Tutorial.published_at.desc())
            .limit(4)
        ).all()

        tutorials = [item for _, item in rows]
        if not tutorials:
            tutorials = self.db.scalars(
                select(Tutorial)
                .where(
                    Tutorial.id != tutorial.id,
                    Tutorial.category_id == tutorial.category_id,
                    Tutorial.status == "published",
                    Tutorial.deleted_at.is_(None),
                )
                .order_by(Tutorial.view_count.desc(), Tutorial.published_at.desc())
                .limit(4)
            ).all()

        return [
            TutorialRelatedItemOut(
                id=str(item.id),
                title=self._get_localized_tutorial_title(item, locale),
                slug=item.slug,
                summary=self._get_localized_tutorial_summary(item, locale),
                coverImage=item.cover_image,
                readTimeMinutes=item.read_time_minutes,
                viewCount=item.view_count,
            )
            for item in tutorials
        ]

    def _get_prev_next(self, tutorial: Tutorial, locale: str) -> TutorialPrevNextOut:
        ordered = self.db.scalars(
            select(Tutorial)
            .where(Tutorial.status == "published", Tutorial.deleted_at.is_(None))
            .order_by(Tutorial.published_at.desc(), Tutorial.created_at.desc())
        ).all()

        index = next((idx for idx, item in enumerate(ordered) if item.id == tutorial.id), -1)
        if index < 0:
            return TutorialPrevNextOut()

        prev_item = ordered[index + 1] if index + 1 < len(ordered) else None
        next_item = ordered[index - 1] if index > 0 else None

        return TutorialPrevNextOut(
            prev=TutorialPrevNextItemOut(
                title=self._get_localized_tutorial_title(prev_item, locale),
                slug=prev_item.slug,
            )
            if prev_item
            else None,
            next=TutorialPrevNextItemOut(
                title=self._get_localized_tutorial_title(next_item, locale),
                slug=next_item.slug,
            )
            if next_item
            else None,
        )

    def get_tutorial_list(self, query: TutorialQueryIn) -> TutorialListOut:
        locale = normalize_tutorial_locale(query.locale)
        filtered_ids_stmt = self._apply_filters(self._base_query(), query)
        tutorial_ids = self.db.scalars(filtered_ids_stmt).all()
        rows = self.db.execute(
            select(Tutorial, TutorialCategory)
            .join(TutorialCategory, Tutorial.category_id == TutorialCategory.id)
            .where(Tutorial.id.in_(tutorial_ids))
        ).all()

        row_map: Dict[UUID, Tuple[Tutorial, TutorialCategory]] = {
            tutorial.id: (tutorial, category) for tutorial, category in rows
        }
        tags_map = self._map_tags_by_tutorial(tutorial_ids, locale)

        items: List[TutorialListItemOut] = []
        for tutorial_id in tutorial_ids:
            pair = row_map.get(tutorial_id)
            if pair is None:
                continue

            tutorial, category = pair
            if query.q and not self._matches_search(tutorial, locale, query.q):
                continue

            items.append(
                TutorialListItemOut(
                    id=str(tutorial.id),
                    title=self._get_localized_tutorial_title(tutorial, locale),
                    slug=tutorial.slug,
                    summary=self._get_localized_tutorial_summary(tutorial, locale),
                    coverImage=tutorial.cover_image,
                    coverIcon=tutorial.cover_icon,
                    category=TutorialCategoryOut(
                        id=str(category.id),
                        name=self._get_localized_category_name(category, locale),
                        slug=category.slug,
                        icon=category.icon,
                        color=category.color,
                        tutorialCount=category.tutorial_count,
                    ),
                    tags=tags_map.get(tutorial.id, []),
                    difficulty=tutorial.difficulty,
                    readTimeMinutes=tutorial.read_time_minutes,
                    viewCount=tutorial.view_count,
                    favoriteCount=tutorial.favorite_count,
                    publishedAt=tutorial.published_at or tutorial.created_at,
                    updatedAt=tutorial.updated_at,
                    isFeatured=tutorial.is_featured,
                    isBeginner=tutorial.is_beginner,
                )
            )

        if query.sort == "popular":
            items.sort(key=lambda item: (item.viewCount, item.favoriteCount, item.publishedAt), reverse=True)
        elif query.sort == "favorites":
            items.sort(key=lambda item: (item.favoriteCount, item.publishedAt), reverse=True)
        else:
            items.sort(key=lambda item: item.publishedAt, reverse=True)

        total = len(items)
        page = query.page
        page_size = query.pageSize
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = items[start:end]

        return TutorialListOut(list=paged_items, pagination=PaginationOut.from_total(page, page_size, total))

    def get_filters(self, locale: str) -> TutorialFiltersOut:
        normalized_locale = normalize_tutorial_locale(locale)
        categories = self.db.scalars(
            select(TutorialCategory)
            .where(TutorialCategory.deleted_at.is_(None), TutorialCategory.is_enabled.is_(True))
            .order_by(TutorialCategory.sort_order.asc(), TutorialCategory.created_at.asc())
        ).all()

        hot_tags = self.db.scalars(
            select(TutorialTag)
            .where(TutorialTag.deleted_at.is_(None), TutorialTag.is_enabled.is_(True), TutorialTag.is_hot.is_(True))
            .order_by(TutorialTag.sort_order.asc(), TutorialTag.created_at.asc())
            .limit(16)
        ).all()

        return TutorialFiltersOut(
            categories=[
                TutorialFilterOptionOut(
                    label="All Tutorials" if normalized_locale == "en" else "全部教程",
                    value="all",
                    icon="category-all-tutorials",
                    count=sum(item.tutorial_count for item in categories),
                )
            ]
            + [
                TutorialFilterOptionOut(
                    label=self._get_localized_category_name(item, normalized_locale),
                    value=item.slug,
                    icon=item.icon,
                    count=item.tutorial_count,
                )
                for item in categories
            ],
            hotKeywords=HOT_KEYWORDS_BY_LOCALE[normalized_locale],
            hotTags=[
                TutorialFilterOptionOut(
                    label=self._get_localized_tag_name(item, normalized_locale),
                    value=item.slug,
                    count=item.tutorial_count,
                )
                for item in hot_tags
            ],
        )

    def get_learning_paths(self, locale: str) -> List[LearningPathOut]:
        normalized_locale = normalize_tutorial_locale(locale)
        rows = self.db.scalars(
            select(LearningPath)
            .where(LearningPath.deleted_at.is_(None), LearningPath.is_enabled.is_(True))
            .order_by(LearningPath.sort_order.asc(), LearningPath.created_at.asc())
        ).all()
        return [
            LearningPathOut(
                id=str(item.id),
                title=self._get_localized_learning_path_title(item, normalized_locale),
                slug=item.slug,
                description=self._get_localized_learning_path_description(item, normalized_locale),
                icon=item.icon,
                tutorialCount=item.tutorial_count,
            )
            for item in rows
        ]

    def get_weekly_hot(self, locale: str) -> List[WeeklyHotTutorialOut]:
        normalized_locale = normalize_tutorial_locale(locale)
        rows = self.db.scalars(
            select(Tutorial)
            .where(Tutorial.status == "published", Tutorial.deleted_at.is_(None))
            .order_by(Tutorial.view_count.desc(), Tutorial.favorite_count.desc(), Tutorial.published_at.desc())
            .limit(5)
        ).all()

        return [
            WeeklyHotTutorialOut(
                id=str(item.id),
                title=self._get_localized_tutorial_title(item, normalized_locale),
                slug=item.slug,
                rank=index + 1,
                viewCount=item.view_count,
            )
            for index, item in enumerate(rows)
        ]

    def get_tutorial_detail(self, slug: str, locale: str) -> Optional[TutorialDetailOut]:
        normalized_locale = normalize_tutorial_locale(locale)
        row = self.db.execute(
            select(Tutorial, TutorialCategory)
            .join(TutorialCategory, Tutorial.category_id == TutorialCategory.id)
            .where(
                Tutorial.slug == slug,
                Tutorial.status == "published",
                Tutorial.deleted_at.is_(None),
                TutorialCategory.deleted_at.is_(None),
                TutorialCategory.is_enabled.is_(True),
            )
        ).first()

        if row is None:
            return None

        tutorial, category = row
        tags_map = self._map_tags_by_tutorial([tutorial.id], normalized_locale)
        author = AUTHOR_BY_LOCALE[normalized_locale]

        return TutorialDetailOut(
            id=str(tutorial.id),
            title=self._get_localized_tutorial_title(tutorial, normalized_locale),
            slug=tutorial.slug,
            summary=self._get_localized_tutorial_summary(tutorial, normalized_locale),
            contentMarkdown=self._get_localized_tutorial_content(tutorial, normalized_locale),
            coverImage=tutorial.cover_image,
            coverIcon=tutorial.cover_icon,
            category=TutorialCategoryOut(
                id=str(category.id),
                name=self._get_localized_category_name(category, normalized_locale),
                slug=category.slug,
                icon=category.icon,
                color=category.color,
                tutorialCount=category.tutorial_count,
            ),
            tags=tags_map.get(tutorial.id, []),
            author=TutorialAuthorOut(**author),
            difficulty=tutorial.difficulty,
            readTimeMinutes=tutorial.read_time_minutes,
            viewCount=tutorial.view_count,
            favoriteCount=tutorial.favorite_count,
            likeCount=tutorial.like_count,
            isBeginner=tutorial.is_beginner,
            publishedAt=tutorial.published_at or tutorial.created_at,
            updatedAt=tutorial.updated_at,
            learningPoints=self._get_localized_learning_points(tutorial, normalized_locale),
            suitableFor=self._get_localized_suitable_for(tutorial, normalized_locale),
            promptBlocks=self._get_prompt_blocks(tutorial, normalized_locale),
            relatedTutorials=self._get_related_tutorials(tutorial, normalized_locale),
            prevNext=self._get_prev_next(tutorial, normalized_locale),
            seoTitle=self._get_localized_tutorial_seo_title(tutorial, normalized_locale),
            seoDescription=self._get_localized_tutorial_seo_description(tutorial, normalized_locale),
        )

    def increment_view_count(self, tutorial_id: UUID) -> bool:
        tutorial = self.db.get(Tutorial, tutorial_id)
        if tutorial is None or tutorial.deleted_at is not None:
            return False
        tutorial.view_count += 1
        self.db.commit()
        return True

    def increment_favorite_count(self, tutorial_id: UUID) -> bool:
        tutorial = self.db.get(Tutorial, tutorial_id)
        if tutorial is None or tutorial.deleted_at is not None:
            return False
        tutorial.favorite_count += 1
        self.db.commit()
        return True

    def increment_like_count(self, tutorial_id: UUID) -> bool:
        tutorial = self.db.get(Tutorial, tutorial_id)
        if tutorial is None or tutorial.deleted_at is not None:
            return False
        tutorial.like_count += 1
        self.db.commit()
        return True

    def record_helpful_vote(self, tutorial_id: UUID, vote: TutorialHelpfulIn) -> bool:
        tutorial = self.db.get(Tutorial, tutorial_id)
        if tutorial is None or tutorial.deleted_at is not None:
            return False
        self.db.add(
            TrackingEvent(
                event_name="tutorial_detail_helpful_click",
                page_url=f"/tutorials/{tutorial.slug}",
                target_type="tutorial",
                target_id=str(tutorial.id),
                extra={"vote": vote.vote},
            )
        )
        self.db.commit()
        return True
