"""
Helper functions for BuilderSolve Agent tools
Shared utilities for text matching, formatting, and data transformation
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


def match_text(item: Dict[str, Any], search_query: str, fields: List[str]) -> bool:
    """
    Smart text matcher for filtering items.
    Returns True if search_query matches any of the specified fields.
    
    Args:
        item: Dictionary containing the data to search
        search_query: The search term
        fields: List of field names to search in
        
    Returns:
        True if match found, False otherwise
    """
    if not search_query:
        return True
    
    query = str(search_query).lower().strip()
    if query in ['all', '*', '']:
        return True
    
    # Collect all searchable text
    context_parts = []
    for field in fields:
        value = item.get(field)
        if value and isinstance(value, (str, int, float)):
            context_parts.append(str(value).lower())
    
    raw_context = ' '.join(context_parts)
    
    # Simple substring match
    if query in raw_context:
        return True
    
    # Token-based match (all query tokens must be present)
    query_tokens = [t for t in query.split() if len(t) > 0]
    if not query_tokens:
        return False
    
    return all(token in raw_context for token in query_tokens)


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