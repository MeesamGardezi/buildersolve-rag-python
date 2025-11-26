"""
Helper functions for BuilderSolve Agent tools
Shared utilities for text matching, formatting, and data transformation
"""
import re
from typing import Dict, Any, List, Optional
from datetime import datetime


def normalize_text(text: str) -> str:
    """
    Normalize text for better matching.
    - Converts to lowercase
    - Replaces multiple spaces/underscores/hyphens with single space
    - Removes special characters except alphanumeric and spaces
    - Strips whitespace
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text string
    """
    if not text:
        return ""
    
    # Convert to lowercase
    result = str(text).lower()
    
    # Replace underscores and hyphens with spaces
    result = re.sub(r'[_\-]+', ' ', result)
    
    # Remove special characters (keep alphanumeric and spaces)
    result = re.sub(r'[^a-z0-9\s]', '', result)
    
    # Replace multiple spaces with single space
    result = re.sub(r'\s+', ' ', result)
    
    # Strip whitespace
    return result.strip()


def fuzzy_match(query: str, text: str) -> bool:
    """
    Perform fuzzy matching between query and text.
    Handles variations like "cleanup" vs "clean up", "cleanUp" vs "clean_up".
    
    Args:
        query: Search query (will be normalized)
        text: Text to search in (will be normalized)
        
    Returns:
        True if query matches text with fuzzy logic
    """
    if not query or not text:
        return not query  # Empty query matches everything
    
    norm_query = normalize_text(query)
    norm_text = normalize_text(text)
    
    if not norm_query:
        return True
    
    # Direct substring match after normalization
    if norm_query in norm_text:
        return True
    
    # Token-based match: all query tokens must be present in text
    query_tokens = norm_query.split()
    if not query_tokens:
        return True
    
    # Check if all tokens are present
    if all(token in norm_text for token in query_tokens):
        return True
    
    # Concatenated match: "cleanup" should match "clean up"
    # Remove spaces from both and check
    query_no_space = norm_query.replace(' ', '')
    text_no_space = norm_text.replace(' ', '')
    
    if query_no_space in text_no_space:
        return True
    
    # Check if query tokens appear in order (not necessarily adjacent)
    # This handles "cabinet painting" matching "cabinet prep painting labor"
    if len(query_tokens) > 1:
        pattern = '.*'.join(re.escape(token) for token in query_tokens)
        if re.search(pattern, norm_text):
            return True
    
    return False


def build_searchable_context(
    task: Dict[str, Any],
    schedule: List[Dict[str, Any]] = None,
    include_parent: bool = True
) -> str:
    """
    Build a comprehensive searchable string for a task,
    optionally including parent task context.
    
    Args:
        task: Task dictionary
        schedule: Full schedule list (needed to find parent task)
        include_parent: Whether to include parent task name in context
        
    Returns:
        Concatenated searchable string
    """
    parts = []
    
    # Add task's own searchable fields
    searchable_fields = ["task", "remarks", "id", "taskType"]
    for field in searchable_fields:
        value = task.get(field)
        if value and isinstance(value, str):
            parts.append(value)
    
    # Add parent task context if available
    if include_parent and schedule:
        main_task_id = task.get("mainTaskId")
        main_task_index = task.get("mainTaskIndex")
        
        if main_task_id or main_task_index is not None:
            # Find parent task
            for parent in schedule:
                if parent.get("id") == main_task_id:
                    parent_name = parent.get("task", "")
                    if parent_name:
                        parts.append(f"under {parent_name}")
                        parts.append(parent_name)
                    break
                elif main_task_index is not None and parent.get("index") == main_task_index:
                    parent_name = parent.get("task", "")
                    if parent_name:
                        parts.append(f"under {parent_name}")
                        parts.append(parent_name)
                    break
    
    return ' '.join(parts)


def match_text(
    item: Dict[str, Any],
    search_query: str,
    fields: List[str],
    schedule: List[Dict[str, Any]] = None,
    include_parent_context: bool = True
) -> bool:
    """
    Smart text matcher for filtering items with fuzzy matching
    and optional hierarchical context.
    
    Args:
        item: Dictionary containing the data to search
        search_query: The search term
        fields: List of field names to search in
        schedule: Full schedule list (for parent context lookup)
        include_parent_context: Whether to include parent task in search
        
    Returns:
        True if match found, False otherwise
    """
    if not search_query:
        return True
    
    query = str(search_query).strip()
    if query.lower() in ['all', '*', '']:
        return True
    
    # Collect all searchable text from specified fields
    context_parts = []
    for field in fields:
        value = item.get(field)
        if value and isinstance(value, (str, int, float)):
            context_parts.append(str(value))
    
    # Add parent context for schedule tasks
    if include_parent_context and schedule and "mainTaskId" in item:
        parent_context = build_searchable_context(item, schedule, include_parent=True)
        context_parts.append(parent_context)
    
    # Join all context
    full_context = ' '.join(context_parts)
    
    # Use fuzzy matching
    return fuzzy_match(query, full_context)


def get_task_status(task: Dict[str, Any]) -> str:
    """
    Get human-readable status from percentageComplete.
    
    Args:
        task: Task dictionary with percentageComplete field
        
    Returns:
        Status string: 'completed', 'in_progress', or 'not_started'
    """
    pct = task.get('percentageComplete', 0)
    if pct >= 100:
        return 'completed'
    elif pct > 0:
        return 'in_progress'
    else:
        return 'not_started'


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO date string to datetime.
    
    Args:
        date_str: ISO format date string (e.g., '2024-05-01')
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None
    try:
        # Handle various ISO formats
        clean_str = date_str.replace('Z', '+00:00').split('T')[0]
        return datetime.fromisoformat(clean_str)
    except (ValueError, AttributeError):
        return None


def format_currency(amount: float) -> str:
    """
    Format a number as USD currency.
    
    Args:
        amount: Numeric amount
        
    Returns:
        Formatted string like '$1,234.56'
    """
    return f"${amount:,.2f}"


def format_task_summary(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a task for summary output (minimal fields).
    
    Args:
        task: Full task dictionary
        
    Returns:
        Dictionary with essential task fields
    """
    return {
        "id": task.get("id"),
        "task": task.get("task"),
        "taskType": task.get("taskType"),
        "status": get_task_status(task),
        "percentageComplete": task.get("percentageComplete", 0),
        "startDate": task.get("startDate"),
        "endDate": task.get("endDate"),
        "duration": task.get("duration", 0),
        "hours": task.get("hours", 0),
        "isCritical": task.get("isCritical", False),
        "isMainTask": task.get("isMainTask", False),
        "hasPayments": len(task.get("paymentStages", [])) > 0,
        "totalPaymentAmount": task.get("totalPaymentAmount", 0)
    }


def format_task_details(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a task with full details including dependencies and payments.
    
    Args:
        task: Full task dictionary
        
    Returns:
        Dictionary with all task fields and computed properties
    """
    # Format dependencies
    dependencies_formatted = []
    for dep in task.get("dependencies", []):
        dep_type = dep.get("type", "FS")
        dependencies_formatted.append({
            "predecessorId": dep.get("predecessorId") or dep.get("predecessorTaskId"),
            "type": dep_type,
            "typeMeaning": {
                "FS": "Finish-to-Start (predecessor must finish first)",
                "SS": "Start-to-Start (start together)",
                "FF": "Finish-to-Finish (finish together)",
                "SF": "Start-to-Finish (predecessor start triggers finish)"
            }.get(dep_type, "Unknown"),
            "lag": dep.get("lag", 0)
        })
    
    # Format payment stages
    payment_stages_formatted = []
    total_amount = task.get("totalPaymentAmount", 0)
    for stage in task.get("paymentStages", []):
        pct = stage.get("percentage", 0)
        amount = total_amount * (pct / 100)
        payment_stages_formatted.append({
            "name": stage.get("name"),
            "percentage": pct,
            "calculatedAmount": amount,
            "effectiveDate": stage.get("effectiveDate"),
            "isManualDate": stage.get("isManualDate", True),
            "linkedType": stage.get("linkedType"),
            "lagDays": stage.get("lagDays", 0)
        })
    
    # Format resources
    resources_formatted = []
    for key, res in task.get("resources", {}).items():
        if isinstance(res, dict):
            resources_formatted.append({
                "key": key,
                "name": res.get("name", "Unknown"),
                "role": res.get("role", "Unknown")
            })
    
    return {
        "id": task.get("id"),
        "index": task.get("index"),
        "task": task.get("task"),
        "taskType": task.get("taskType"),
        "status": get_task_status(task),
        "percentageComplete": task.get("percentageComplete", 0),
        # Dates
        "startDate": task.get("startDate"),
        "endDate": task.get("endDate"),
        "actualStart": task.get("actualStart"),
        "actualEnd": task.get("actualEnd"),
        "baselineStartDate": task.get("baselineStartDate"),
        "baselineEndDate": task.get("baselineEndDate"),
        # Time
        "duration": task.get("duration", 0),
        "hours": task.get("hours", 0),
        "consumed": task.get("consumed", 0),
        "hoursRemaining": max(0, task.get("hours", 0) - task.get("consumed", 0)),
        # Critical path
        "isCritical": task.get("isCritical", False),
        "totalSlack": task.get("totalSlack", 0),
        "schedulingMode": task.get("schedulingMode", "Automatic"),
        # Hierarchy
        "isMainTask": task.get("isMainTask", False),
        "mainTaskId": task.get("mainTaskId"),
        "subtaskIds": task.get("subtaskIds"),
        # Dependencies
        "dependencies": dependencies_formatted,
        "dependencyCount": len(dependencies_formatted),
        # Payments
        "paymentStages": payment_stages_formatted,
        "totalPaymentAmount": total_amount,
        "hasPayments": len(payment_stages_formatted) > 0,
        # Resources
        "resources": resources_formatted,
        # Other
        "remarks": task.get("remarks", ""),
        "isBaselineSet": task.get("isBaselineSet", False)
    }


def format_comparison_row_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a comparison row for summary output.
    
    Args:
        row: ComparisonRow as dictionary
        
    Returns:
        Dictionary with essential comparison fields
    """
    budgeted = row.get("budgetedAmount", 0)
    consumed = row.get("consumedAmount", 0)
    difference = budgeted - consumed
    progress = (consumed / budgeted * 100) if budgeted > 0 else 0
    
    return {
        "costCode": row.get("costCode"),
        "budgetedAmount": budgeted,
        "consumedAmount": consumed,
        "differenceAmount": difference,
        "progress": round(progress, 1),
        "isOverBudget": consumed > budgeted,
        "tags": row.get("tags", []),
        "isAllowance": "alw" in row.get("tags", []),
        "isChangeOrder": "co" in row.get("tags", []),
    }


def ensure_float(value: Any) -> float:
    """
    Ensure a value is converted to float.
    
    Args:
        value: Any numeric value (int, float, str, None)
        
    Returns:
        Float value, or 0.0 if conversion fails
    """
    if value is None:
        return 0.0
    try:
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value))
    except (ValueError, TypeError):
        return 0.0