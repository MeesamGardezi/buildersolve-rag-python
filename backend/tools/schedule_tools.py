"""
Schedule tool handlers for BuilderSolve Agent
"""
from typing import Dict, Any, List
from .helpers import (
    match_text,
    get_task_status,
    parse_date,
    format_task_summary,
    format_task_details,
    fuzzy_match,
    build_searchable_context,
)


async def execute_query_schedule(
    job_data: Dict[str, Any],
    args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute query_schedule tool.
    
    Query and filter schedule tasks with various criteria.
    Can count tasks, sum numeric fields, or list matching tasks.
    
    Args:
        job_data: Full job data dictionary
        args: Tool arguments for filtering
        
    Returns:
        Dictionary with filtered results based on returnType
    """
    schedule = job_data.get("schedule", [])
    
    # Apply filters
    filtered = schedule.copy()
    
    # Filter by taskType
    task_type = args.get("taskType")
    if task_type:
        filtered = [t for t in filtered if t.get("taskType") == task_type]
    
    # Filter by status
    status = args.get("status")
    if status:
        filtered = [t for t in filtered if get_task_status(t) == status]
    
    # Filter by isCritical
    is_critical = args.get("isCritical")
    if is_critical is not None:
        filtered = [t for t in filtered if t.get("isCritical") == is_critical]
    
    # Filter by isMainTask
    is_main_task = args.get("isMainTask")
    if is_main_task is not None:
        filtered = [t for t in filtered if t.get("isMainTask") == is_main_task]
    
    # Filter by text search (now with hierarchical context)
    search_query = args.get("searchQuery")
    if search_query:
        filtered = [
            t for t in filtered
            if match_text(
                t,
                search_query,
                ["task", "remarks"],
                schedule=schedule,  # Pass full schedule for parent context
                include_parent_context=True
            )
        ]
    
    # Filter by date range
    start_from = parse_date(args.get("startDateFrom"))
    start_to = parse_date(args.get("startDateTo"))
    
    if start_from or start_to:
        date_filtered = []
        for t in filtered:
            task_start = parse_date(t.get("startDate"))
            if not task_start:
                continue
            if start_from and task_start < start_from:
                continue
            if start_to and task_start > start_to:
                continue
            date_filtered.append(t)
        filtered = date_filtered
    
    # Determine return type
    return_type = args.get("returnType", "list")
    limit = args.get("limit", 10)
    
    # Build filters applied dict for response
    filters_applied = {
        k: v for k, v in args.items()
        if v is not None and k not in ["returnType", "limit", "fieldToSum"]
    }
    
    if return_type == "count":
        return {
            "count": len(filtered),
            "totalTasks": len(schedule),
            "filtersApplied": filters_applied
        }
    
    elif return_type == "sum":
        field_to_sum = args.get("fieldToSum", "hours")
        total_sum = 0.0
        for t in filtered:
            value = t.get(field_to_sum, 0)
            try:
                total_sum += float(value) if value else 0
            except (ValueError, TypeError):
                pass
        
        return {
            "sum": round(total_sum, 2),
            "fieldSummed": field_to_sum,
            "matchedTasks": len(filtered),
            "totalTasks": len(schedule),
            "filtersApplied": filters_applied
        }
    
    else:  # list
        tasks_output = [format_task_summary(t) for t in filtered[:limit]]
        return {
            "tasks": tasks_output,
            "matchedCount": len(filtered),
            "returnedCount": len(tasks_output),
            "totalTasks": len(schedule),
            "filtersApplied": filters_applied
        }


async def execute_get_task_details(
    job_data: Dict[str, Any],
    args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute get_task_details tool.
    
    Get full details of a specific task including payment stages,
    dependencies, dates, progress, and resources.
    
    Now includes hierarchical search - will find tasks by parent context.
    
    Args:
        job_data: Full job data dictionary
        args: Tool arguments containing searchQuery or taskId
        
    Returns:
        Dictionary with full task details or error message
    """
    schedule = job_data.get("schedule", [])
    task_id = args.get("taskId")
    search_query = args.get("searchQuery")
    only_payment_capable = args.get("onlyPaymentCapable", False)
    
    # Payment-capable task types
    PAYMENT_TASK_TYPES = ['material', 'subcontractor', 'milestone']
    
    # Filter schedule if only payment-capable tasks requested
    searchable_tasks = schedule
    if only_payment_capable:
        searchable_tasks = [
            t for t in schedule
            if t.get("taskType") in PAYMENT_TASK_TYPES
        ]
    
    # Find task by ID first (exact match)
    found_task = None
    
    if task_id:
        for t in searchable_tasks:
            if t.get("id") == task_id:
                found_task = t
                break
    
    # Fall back to search query with hierarchical context
    if not found_task and search_query:
        # Score tasks by match quality and return best match
        best_match = None
        best_score = 0
        
        for t in searchable_tasks:
            # Build searchable context including parent task
            context = build_searchable_context(t, schedule, include_parent=True)
            
            # Check if it matches
            if fuzzy_match(search_query, context):
                # Calculate a simple relevance score
                # Direct task name match scores higher than parent match
                task_name = t.get("task", "")
                score = 0
                
                # Direct match in task name (highest priority)
                if fuzzy_match(search_query, task_name):
                    score = 100
                # Match via parent context (lower priority but still valid)
                elif fuzzy_match(search_query, context):
                    score = 50
                
                # Prefer payment-capable tasks when searching for payments
                if only_payment_capable and t.get("taskType") in PAYMENT_TASK_TYPES:
                    score += 10
                
                if score > best_score:
                    best_score = score
                    best_match = t
        
        found_task = best_match
    
    if not found_task:
        # Provide helpful error message with available tasks
        if only_payment_capable:
            available = [
                f"{t.get('task')} ({t.get('taskType')})"
                for t in searchable_tasks[:10]
            ]
            return {
                "error": "No payment-capable task found matching your search",
                "searchedFor": task_id or search_query,
                "note": "Only material, subcontractor, and milestone tasks can have payment stages",
                "availablePaymentTasks": available,
                "hint": "Try searching with different keywords or check the task name spelling"
            }
        else:
            # Show tasks that partially match to help user
            partial_matches = []
            for t in schedule[:20]:
                context = build_searchable_context(t, schedule, include_parent=True)
                task_name = t.get("task", "")
                partial_matches.append({
                    "task": task_name,
                    "taskType": t.get("taskType"),
                    "parentContext": t.get("mainTaskId")
                })
            
            return {
                "error": "Task not found",
                "searchedFor": task_id or search_query,
                "availableTasks": [t.get("task") for t in schedule[:10]],
                "hint": "Try searching with the exact task name or parent task name"
            }
    
    # Add parent task info to the response
    result = format_task_details(found_task)
    
    # Add parent task name if this is a subtask
    main_task_id = found_task.get("mainTaskId")
    if main_task_id:
        for parent in schedule:
            if parent.get("id") == main_task_id:
                result["parentTaskName"] = parent.get("task")
                break
    
    return result


async def execute_query_task_hierarchy(
    job_data: Dict[str, Any],
    args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute query_task_hierarchy tool.
    
    Get a main task and all its subtasks.
    
    Args:
        job_data: Full job data dictionary
        args: Tool arguments containing mainTaskSearch or mainTaskId
        
    Returns:
        Dictionary with main task and subtasks
    """
    schedule = job_data.get("schedule", [])
    main_task_id = args.get("mainTaskId")
    main_task_search = args.get("mainTaskSearch")
    include_details = args.get("includeDetails", False)
    
    # Find main task by ID first
    main_task = None
    
    if main_task_id:
        for t in schedule:
            if t.get("id") == main_task_id and t.get("isMainTask"):
                main_task = t
                break
    
    # Fall back to search with fuzzy matching
    if not main_task and main_task_search:
        for t in schedule:
            if t.get("isMainTask"):
                task_name = t.get("task", "")
                if fuzzy_match(main_task_search, task_name):
                    main_task = t
                    break
    
    if not main_task:
        # List available main tasks
        main_tasks = [t.get("task") for t in schedule if t.get("isMainTask")]
        return {
            "error": "Main task not found",
            "searchedFor": main_task_id or main_task_search,
            "availableMainTasks": main_tasks
        }
    
    # Find subtasks
    subtask_ids = main_task.get("subtaskIds", [])
    subtask_indices = main_task.get("subtaskIndices", [])
    
    subtasks = []
    for t in schedule:
        # Match by static ID (preferred)
        if t.get("id") in subtask_ids:
            subtasks.append(t)
        # Fallback to index
        elif t.get("index") in subtask_indices:
            subtasks.append(t)
        # Or match by mainTaskId
        elif t.get("mainTaskId") == main_task.get("id"):
            subtasks.append(t)
    
    # Format output
    if include_details:
        subtasks_output = [format_task_details(t) for t in subtasks]
    else:
        subtasks_output = [format_task_summary(t) for t in subtasks]
    
    # Calculate totals
    total_hours = sum(t.get("hours", 0) for t in subtasks)
    total_consumed = sum(t.get("consumed", 0) for t in subtasks)
    total_duration = sum(t.get("duration", 0) for t in subtasks)
    avg_completion = (
        sum(t.get("percentageComplete", 0) for t in subtasks) / len(subtasks)
        if subtasks else 0
    )
    
    return {
        "mainTask": format_task_summary(main_task),
        "subtasks": subtasks_output,
        "subtaskCount": len(subtasks),
        "totals": {
            "hours": total_hours,
            "consumed": total_consumed,
            "duration": total_duration,
            "averageCompletion": round(avg_completion, 1)
        }
    }


async def execute_query_dependencies(
    job_data: Dict[str, Any],
    args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute query_dependencies tool.
    
    Find predecessors or successors of a task.
    
    Args:
        job_data: Full job data dictionary
        args: Tool arguments containing taskSearch or taskId and direction
        
    Returns:
        Dictionary with dependency chain
    """
    schedule = job_data.get("schedule", [])
    task_id = args.get("taskId")
    task_search = args.get("taskSearch")
    direction = args.get("direction", "predecessors")
    include_chain = args.get("includeChain", False)
    
    # Build lookup maps
    id_to_task = {t.get("id"): t for t in schedule}
    index_to_task = {str(t.get("index")): t for t in schedule}
    
    # Find target task with fuzzy matching and hierarchical context
    target_task = None
    
    if task_id:
        target_task = id_to_task.get(task_id)
    
    if not target_task and task_search:
        for t in schedule:
            # Use hierarchical search
            context = build_searchable_context(t, schedule, include_parent=True)
            if fuzzy_match(task_search, context):
                target_task = t
                break
    
    if not target_task:
        return {
            "error": "Task not found",
            "searchedFor": task_id or task_search,
            "availableTasks": [t.get("task") for t in schedule[:10]]
        }
    
    results = []
    
    if direction == "predecessors":
        # Find tasks that this task depends on
        def get_predecessors(task: Dict, visited: set = None) -> List[Dict]:
            if visited is None:
                visited = set()
            
            task_id = task.get("id")
            if task_id in visited:
                return []
            visited.add(task_id)
            
            preds = []
            for dep in task.get("dependencies", []):
                pred_id = dep.get("predecessorId") or dep.get("predecessorTaskId")
                pred_task = id_to_task.get(pred_id) or index_to_task.get(pred_id)
                
                if pred_task:
                    pred_info = {
                        "task": format_task_summary(pred_task),
                        "dependencyType": dep.get("type", "FS"),
                        "lag": dep.get("lag", 0)
                    }
                    preds.append(pred_info)
                    
                    if include_chain:
                        chain_preds = get_predecessors(pred_task, visited)
                        pred_info["predecessors"] = chain_preds
            
            return preds
        
        results = get_predecessors(target_task)
    
    else:  # successors
        # Find tasks that depend on this task
        target_id = target_task.get("id")
        target_index = str(target_task.get("index"))
        
        def get_successors(task_id: str, task_index: str, visited: set = None) -> List[Dict]:
            if visited is None:
                visited = set()
            
            if task_id in visited:
                return []
            visited.add(task_id)
            
            succs = []
            for t in schedule:
                for dep in t.get("dependencies", []):
                    pred_id = dep.get("predecessorId") or dep.get("predecessorTaskId")
                    if pred_id == task_id or pred_id == task_index:
                        succ_info = {
                            "task": format_task_summary(t),
                            "dependencyType": dep.get("type", "FS"),
                            "lag": dep.get("lag", 0)
                        }
                        succs.append(succ_info)
                        
                        if include_chain:
                            chain_succs = get_successors(
                                t.get("id"),
                                str(t.get("index")),
                                visited
                            )
                            succ_info["successors"] = chain_succs
                        break
            
            return succs
        
        results = get_successors(target_id, target_index)
    
    return {
        "targetTask": format_task_summary(target_task),
        "direction": direction,
        "includeChain": include_chain,
        direction: results,
        "count": len(results)
    }