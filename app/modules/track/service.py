from sqlalchemy.orm import Session

from app.modules.track.models import TrackingEvent
from app.modules.track.schemas import TrackEventIn


ALLOWED_EVENT_NAMES = {
    "page_view_home",
    "home_search_submit",
    "home_category_click",
    "home_featured_skill_click",
    "home_latest_skill_click",
    "home_tutorial_click",
    "home_submit_skill_click",
    "home_register_click",
    "skills_page_view",
    "skills_search_submit",
    "skills_hot_keyword_click",
    "skills_category_shortcut_click",
    "skills_filter_category_click",
    "skills_filter_scene_click",
    "skills_filter_model_click",
    "skills_filter_difficulty_click",
    "skills_filter_type_click",
    "skills_sort_change",
    "skills_card_click",
    "skills_favorite_click",
    "skills_load_more_click",
    "skills_submit_skill_click",
    "tutorials_page_view",
    "tutorials_search_submit",
    "tutorials_hot_keyword_click",
    "tutorials_category_click",
    "tutorials_tag_click",
    "tutorials_sort_change",
    "tutorials_article_click",
    "tutorials_read_more_click",
    "tutorials_learning_path_click",
    "tutorials_weekly_hot_click",
    "tutorials_subscribe_submit",
    "categories_page_view",
    "categories_search_submit",
    "categories_filter_group_click",
    "categories_filter_scene_click",
    "categories_tab_click",
    "categories_sort_change",
    "categories_card_click",
    "categories_hot_tag_click",
    "tutorial_detail_page_view",
    "tutorial_detail_action_click",
    "tutorial_detail_prompt_copy",
    "tutorial_detail_related_click",
    "tutorial_detail_helpful_click",
    "submit_skill_page_view",
    "submit_skill_step_view",
    "submit_skill_next_step_click",
    "submit_skill_prev_step_click",
    "submit_skill_save_draft",
    "submit_skill_upload_cover",
    "submit_skill_add_tag",
    "submit_skill_add_variable",
    "submit_skill_remove_variable",
    "submit_skill_prompt_copy_preview",
    "submit_skill_submit_review",
    "submit_skill_submit_success",
    "submit_skill_submit_failed",
}


def validate_track_event(payload: TrackEventIn) -> None:
    if payload.eventName not in ALLOWED_EVENT_NAMES:
        raise ValueError("invalid eventName")


def create_track_event(db: Session, payload: TrackEventIn) -> None:
    event = TrackingEvent(
        event_name=payload.eventName,
        page_url=payload.pageUrl,
        target_type=payload.targetType,
        target_id=payload.targetId,
        extra=payload.extra,
    )
    db.add(event)
    db.commit()
