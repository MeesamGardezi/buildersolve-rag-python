"""
Estimate tool handlers for BuilderSolve Agent
"""
from typing import Dict, Any
from .helpers import match_text


async def execute_calculate_estimate_sum(
    job_data: Dict[str, Any],
    args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute calculate_estimate_sum tool.
    
    Calculates the sum of a numeric field within the estimate list,
    with optional text filtering.
    
    Args:
        job_data: Full job data dictionary
        args: Tool arguments containing fieldName and optional searchQuery
        
    Returns:
        Dictionary with sum, matched items count, and examples
    """
    field_name = args.get("fieldName", "total")
    search_query = args.get("searchQuery", "")
    
    estimate_list = job_data.get("estimate", [])
    search_fields = ["area", "taskScope", "description", "costCode", "notesRemarks", "rowType"]
    
    # Filter items
    if search_query and search_query.lower() not in ['all', '*']:
        filtered = [
            item for item in estimate_list
            if match_text(item, search_query, search_fields)
        ]
    else:
        filtered = estimate_list
    
    # Calculate sum
    total_sum = 0.0
    for item in filtered:
        value = item.get(field_name, 0)
        try:
            total_sum += float(value) if value else 0
        except (ValueError, TypeError):
            pass
    
    # Get examples for context
    examples = []
    for item in filtered[:5]:
        area = item.get('area', '')
        description = item.get('description', '')
        example = f"{area} - {description}"[:50]
        examples.append(example)
    
    return {
        "sum": round(total_sum, 2),
        "currency": "USD",
        "fieldSummed": field_name,
        "totalItems": len(estimate_list),
        "matchedItems": len(filtered),
        "searchQuery": search_query or "ALL",
        "matchedExamples": examples
    }