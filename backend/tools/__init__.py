"""
BuilderSolve Agent - Tools Package
Exports all tool definitions and handlers
"""

from .definitions import (
    ALL_TOOLS,
    JOB_TOOLS,
    ESTIMATE_TOOLS,
    SCHEDULE_TOOLS,
    PAYMENT_TOOLS,
    COMPARISON_TOOLS,
)

from .helpers import (
    match_text,
    get_task_status,
    parse_date,
    format_currency,
    format_task_summary,
    format_task_details,
    ensure_float,
    # New exports for enhanced matching
    normalize_text,
    fuzzy_match,
    build_searchable_context,
)

from .estimate_tools import execute_calculate_estimate_sum

from .schedule_tools import (
    execute_query_schedule,
    execute_get_task_details,
    execute_query_task_hierarchy,
    execute_query_dependencies,
)

from .payment_tools import execute_query_payment_schedule

from .comparison_tools import (
    execute_get_comparison_data,
    execute_query_comparison_rows,
    execute_get_comparison_summary,
)

__all__ = [
    # Definitions
    "ALL_TOOLS",
    "JOB_TOOLS",
    "ESTIMATE_TOOLS",
    "SCHEDULE_TOOLS",
    "PAYMENT_TOOLS",
    "COMPARISON_TOOLS",
    # Helpers
    "match_text",
    "get_task_status",
    "parse_date",
    "format_currency",
    "format_task_summary",
    "format_task_details",
    "ensure_float",
    "normalize_text",
    "fuzzy_match",
    "build_searchable_context",
    # Estimate
    "execute_calculate_estimate_sum",
    # Schedule
    "execute_query_schedule",
    "execute_get_task_details",
    "execute_query_task_hierarchy",
    "execute_query_dependencies",
    # Payment
    "execute_query_payment_schedule",
    # Comparison
    "execute_get_comparison_data",
    "execute_query_comparison_rows",
    "execute_get_comparison_summary",
]