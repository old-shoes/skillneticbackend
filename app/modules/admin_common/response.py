from __future__ import annotations

from typing import Any, Dict, List

from app.core.response import success


def page_response(items: List[Dict[str, Any]], page: int, page_size: int, total: int) -> dict:
    return success(
        {
            "items": items,
            "page": page,
            "pageSize": page_size,
            "total": total,
        }
    )
