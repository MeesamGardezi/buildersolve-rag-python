"""
Payment tool handlers for BuilderSolve Agent
"""
from typing import Dict, Any, List
from .helpers import (
    match_text,
    get_task_status,
    parse_date,
    fuzzy_match,
    build_searchable_context,
)


async def execute_query_payment_schedule(
    job_data: Dict[str, Any],
    args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute query_payment_schedule tool.
    
    Get payment stages across tasks with optional filtering.
    Now supports hierarchical search - can find tasks by parent context.
    
    Args:
        job_data: Full job data dictionary
        args: Tool arguments for filtering
        
    Returns:
        Dictionary with payment schedule based on returnType
    """
    schedule = job_data.get("schedule", [])
    
    date_from = parse_date(args.get("dateFrom"))
    date_to = parse_date(args.get("dateTo"))
    task_type = args.get("taskType")
    task_search = args.get("taskSearch")
    return_type = args.get("returnType", "list")
    
    # Collect all payment stages
    all_payments: List[Dict[str, Any]] = []
    
    for task in schedule:
        # Apply task type filter
        if task_type and task.get("taskType") != task_type:
            continue
        
        # Apply task search filter with hierarchical context
        if task_search:
            # Build searchable context including parent task
            context = build_searchable_context(task, schedule, include_parent=True)
            if not fuzzy_match(task_search, context):
                continue
        
        total_amount = task.get("totalPaymentAmount", 0)
        if total_amount <= 0:
            continue
        
        # Get parent task name for context in results
        parent_task_name = None
        main_task_id = task.get("mainTaskId")
        if main_task_id:
            for parent in schedule:
                if parent.get("id") == main_task_id:
                    parent_task_name = parent.get("task")
                    break
        
        for stage in task.get("paymentStages", []):
            effective_date = parse_date(stage.get("effectiveDate"))
            
            # Apply date filters
            if date_from and effective_date and effective_date < date_from:
                continue
            if date_to and effective_date and effective_date > date_to:
                continue
            
            pct = stage.get("percentage", 0)
            amount = total_amount * (pct / 100)
            
            payment_entry = {
                "taskId": task.get("id"),
                "taskName": task.get("task"),
                "taskType": task.get("taskType"),
                "stageName": stage.get("name"),
                "percentage": pct,
                "amount": round(amount, 2),
                "effectiveDate": stage.get("effectiveDate"),
                "isManualDate": stage.get("isManualDate", True),
                "taskStatus": get_task_status(task)
            }
            
            # Add parent context if available
            if parent_task_name:
                payment_entry["parentTaskName"] = parent_task_name
            
            all_payments.append(payment_entry)
    
    # Sort by date
    all_payments.sort(key=lambda x: x.get("effectiveDate") or "9999-12-31")
    
    # Build filters applied dict
    filters_applied = {
        k: v for k, v in args.items()
        if v is not None and k != "returnType"
    }
    
    if return_type == "summary":
        # Group by task type
        by_type: Dict[str, Dict[str, Any]] = {}
        for p in all_payments:
            tt = p["taskType"]
            if tt not in by_type:
                by_type[tt] = {"count": 0, "total": 0}
            by_type[tt]["count"] += 1
            by_type[tt]["total"] += p["amount"]
        
        # Round totals
        for tt in by_type:
            by_type[tt]["total"] = round(by_type[tt]["total"], 2)
        
        grand_total = sum(p["amount"] for p in all_payments)
        
        return {
            "byTaskType": by_type,
            "grandTotal": round(grand_total, 2),
            "totalPayments": len(all_payments),
            "filtersApplied": filters_applied
        }
    
    elif return_type == "timeline":
        # Group by month
        by_month: Dict[str, Dict[str, Any]] = {}
        for p in all_payments:
            date_str = p.get("effectiveDate", "Unknown")
            if date_str and date_str != "Unknown":
                month_key = date_str[:7]  # "2024-05"
            else:
                month_key = "Unscheduled"
            
            if month_key not in by_month:
                by_month[month_key] = {"payments": [], "total": 0}
            by_month[month_key]["payments"].append(p)
            by_month[month_key]["total"] += p["amount"]
        
        # Round totals
        for m in by_month:
            by_month[m]["total"] = round(by_month[m]["total"], 2)
        
        grand_total = sum(p["amount"] for p in all_payments)
        
        return {
            "timeline": by_month,
            "grandTotal": round(grand_total, 2),
            "totalPayments": len(all_payments),
            "filtersApplied": filters_applied
        }
    
    else:  # list
        grand_total = sum(p["amount"] for p in all_payments)
        
        return {
            "payments": all_payments,
            "totalPayments": len(all_payments),
            "grandTotal": round(grand_total, 2),
            "filtersApplied": filters_applied
        }