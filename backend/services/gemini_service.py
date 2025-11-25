"""
Gemini AI service with agentic tool calling
Includes tools for estimates, schedule, payments, dependencies, and hierarchy
"""
import os
import sys
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import DEFAULT_COMPANY_ID, DEFAULT_JOB_ID, GEMINI_MODEL, SYSTEM_INSTRUCTION
from models.types import ToolExecution, ChatResponse
from services.firebase_service import fetch_job_data, search_jobs


# Initialize Gemini
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY environment variable is not set")

genai.configure(api_key=api_key)


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

# -----------------------------------------------------------------------------
# JOB TOOLS
# -----------------------------------------------------------------------------

search_jobs_tool = {
    "function_declarations": [{
        "name": "search_jobs",
        "description": "Searches for construction jobs in the database by name, client, address, or ID. Use this when the user mentions a new job or wants to switch projects.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The search term (e.g. 'Smith', 'Hammond', 'Kitchen Remodel')."
                }
            },
            "required": ["query"]
        }
    }]
}

get_job_data_tool = {
    "function_declarations": [{
        "name": "get_current_job_data",
        "description": "Retrieves the full details, estimates, schedule, and milestones for a specific construction job. Use this to load a job context or switch to a different job.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "jobId": {
                    "type": "STRING",
                    "description": "The specific document ID of the job to fetch."
                }
            },
            "required": ["jobId"]
        }
    }]
}

# -----------------------------------------------------------------------------
# ESTIMATE TOOLS
# -----------------------------------------------------------------------------

calculate_estimate_sum_tool = {
    "function_declarations": [{
        "name": "calculate_estimate_sum",
        "description": "Calculates the sum of a numeric field within the ESTIMATE list, with optional text filtering. Use for questions about estimate costs, prices, budgets, quantities.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "fieldName": {
                    "type": "STRING",
                    "description": "The numeric field to sum. Options: 'total' (price to client), 'budgetedTotal' (internal cost), 'qty', 'rate', 'budgetedRate'."
                },
                "searchQuery": {
                    "type": "STRING",
                    "description": "Optional text filter. Searches across area, taskScope, description, costCode. E.g., 'Kitchen', 'Demolition', 'Flooring'. Use 'all' or omit for no filter."
                }
            },
            "required": ["fieldName"]
        }
    }]
}

# -----------------------------------------------------------------------------
# SCHEDULE TOOLS
# -----------------------------------------------------------------------------

query_schedule_tool = {
    "function_declarations": [{
        "name": "query_schedule",
        "description": "Query and filter schedule tasks. Can count tasks, sum numeric fields, or list tasks matching criteria. Use for questions about tasks, hours, duration, progress, critical path.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "taskType": {
                    "type": "STRING",
                    "description": "Filter by task type: 'labour', 'milestone', 'material', 'subcontractor', 'others'. Omit for all types."
                },
                "status": {
                    "type": "STRING",
                    "description": "Filter by status: 'completed' (100%), 'in_progress' (1-99%), 'not_started' (0%). Omit for all."
                },
                "isCritical": {
                    "type": "BOOLEAN",
                    "description": "Filter by critical path. true = only critical tasks, false = only non-critical."
                },
                "isMainTask": {
                    "type": "BOOLEAN",
                    "description": "Filter by hierarchy. true = only main/parent tasks, false = only subtasks."
                },
                "searchQuery": {
                    "type": "STRING",
                    "description": "Text search across task name and remarks. E.g., 'Electrical', 'Cabinet'."
                },
                "startDateFrom": {
                    "type": "STRING",
                    "description": "Filter tasks starting on or after this date (ISO format: '2024-05-01')."
                },
                "startDateTo": {
                    "type": "STRING",
                    "description": "Filter tasks starting on or before this date (ISO format: '2024-05-31')."
                },
                "fieldToSum": {
                    "type": "STRING",
                    "description": "If provided, sum this numeric field: 'hours', 'consumed', 'duration', 'percentageComplete', 'totalSlack', 'totalPaymentAmount'."
                },
                "returnType": {
                    "type": "STRING",
                    "description": "What to return: 'count' (number of matching tasks), 'sum' (requires fieldToSum), 'list' (task details). Default is 'list'."
                },
                "limit": {
                    "type": "INTEGER",
                    "description": "Maximum number of tasks to return when returnType='list'. Default 10."
                }
            },
            "required": []
        }
    }]
}

get_task_details_tool = {
    "function_declarations": [{
        "name": "get_task_details",
        "description": "Get full details of a specific task including payment stages, dependencies, dates, progress, and resources. Use when user asks about a specific task.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "searchQuery": {
                    "type": "STRING",
                    "description": "Task name to search for. E.g., 'Electrical', 'Framing', 'Cabinet Installation'."
                },
                "taskId": {
                    "type": "STRING",
                    "description": "Exact task ID if known (e.g., 'task_electrical'). Takes precedence over searchQuery."
                }
            },
            "required": []
        }
    }]
}

query_task_hierarchy_tool = {
    "function_declarations": [{
        "name": "query_task_hierarchy",
        "description": "Get a main task and all its subtasks. Use for questions about task groups, phases, or parent-child relationships.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mainTaskSearch": {
                    "type": "STRING",
                    "description": "Name of the main/parent task to find. E.g., 'Site Preparation', 'Final Finishes'."
                },
                "mainTaskId": {
                    "type": "STRING",
                    "description": "Exact ID of the main task if known. Takes precedence over mainTaskSearch."
                },
                "includeDetails": {
                    "type": "BOOLEAN",
                    "description": "If true, include full details of each subtask. Default false (summary only)."
                }
            },
            "required": []
        }
    }]
}

query_dependencies_tool = {
    "function_declarations": [{
        "name": "query_dependencies",
        "description": "Find predecessors (what comes before) or successors (what comes after) of a task. Use for dependency chain questions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "taskSearch": {
                    "type": "STRING",
                    "description": "Name of the task to find dependencies for. E.g., 'Kitchen Flooring', 'Demolition'."
                },
                "taskId": {
                    "type": "STRING",
                    "description": "Exact task ID if known. Takes precedence over taskSearch."
                },
                "direction": {
                    "type": "STRING",
                    "description": "'predecessors' (what must finish before this task) or 'successors' (what depends on this task). Default 'predecessors'."
                },
                "includeChain": {
                    "type": "BOOLEAN",
                    "description": "If true, recursively find the full dependency chain. Default false (direct dependencies only)."
                }
            },
            "required": []
        }
    }]
}

# -----------------------------------------------------------------------------
# PAYMENT TOOLS
# -----------------------------------------------------------------------------

query_payment_schedule_tool = {
    "function_declarations": [{
        "name": "query_payment_schedule",
        "description": "Get payment stages across tasks. Can filter by date range, task type, or specific task. Use for cashflow and payment questions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "dateFrom": {
                    "type": "STRING",
                    "description": "Filter payments due on or after this date (ISO format: '2024-05-01')."
                },
                "dateTo": {
                    "type": "STRING",
                    "description": "Filter payments due on or before this date (ISO format: '2024-05-31')."
                },
                "taskType": {
                    "type": "STRING",
                    "description": "Filter by task type: 'labour', 'milestone', 'material', 'subcontractor', 'others'."
                },
                "taskSearch": {
                    "type": "STRING",
                    "description": "Filter by task name. E.g., 'Electrical', 'Cabinet'."
                },
                "returnType": {
                    "type": "STRING",
                    "description": "'list' (all matching payments), 'summary' (totals by task type), 'timeline' (ordered by date). Default 'list'."
                }
            },
            "required": []
        }
    }]
}

# -----------------------------------------------------------------------------
# COMBINE ALL TOOLS
# -----------------------------------------------------------------------------

ALL_TOOLS = {
    "function_declarations": [
        # Job tools
        search_jobs_tool["function_declarations"][0],
        get_job_data_tool["function_declarations"][0],
        # Estimate tools
        calculate_estimate_sum_tool["function_declarations"][0],
        # Schedule tools
        query_schedule_tool["function_declarations"][0],
        get_task_details_tool["function_declarations"][0],
        query_task_hierarchy_tool["function_declarations"][0],
        query_dependencies_tool["function_declarations"][0],
        # Payment tools
        query_payment_schedule_tool["function_declarations"][0],
    ]
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def match_text(item: Dict[str, Any], search_query: str, fields: List[str]) -> bool:
    """
    Smart text matcher for filtering items.
    Returns True if search_query matches any of the specified fields.
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
    """Get human-readable status from percentageComplete"""
    pct = task.get('percentageComplete', 0)
    if pct >= 100:
        return 'completed'
    elif pct > 0:
        return 'in_progress'
    else:
        return 'not_started'


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO date string to datetime"""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00').split('T')[0])
    except:
        return None


def format_task_summary(task: Dict[str, Any]) -> Dict[str, Any]:
    """Format a task for summary output"""
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
    """Format a task with full details"""
    # Format dependencies
    dependencies_formatted = []
    for dep in task.get("dependencies", []):
        dependencies_formatted.append({
            "predecessorId": dep.get("predecessorId") or dep.get("predecessorTaskId"),
            "type": dep.get("type", "FS"),
            "typeMeaning": {
                "FS": "Finish-to-Start (predecessor must finish first)",
                "SS": "Start-to-Start (start together)",
                "FF": "Finish-to-Finish (finish together)",
                "SF": "Start-to-Finish (predecessor start triggers finish)"
            }.get(dep.get("type", "FS"), "Unknown"),
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


# =============================================================================
# TOOL EXECUTION HANDLERS
# =============================================================================

async def execute_calculate_estimate_sum(job_data: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute calculate_estimate_sum tool"""
    field_name = args.get("fieldName", "total")
    search_query = args.get("searchQuery", "")
    
    estimate_list = job_data.get("estimate", [])
    search_fields = ["area", "taskScope", "description", "costCode", "notesRemarks", "rowType"]
    
    # Filter items
    if search_query and search_query.lower() not in ['all', '*']:
        filtered = [item for item in estimate_list if match_text(item, search_query, search_fields)]
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
    
    # Get examples
    examples = [
        f"{item.get('area', '')} - {item.get('description', '')}"[:50]
        for item in filtered[:5]
    ]
    
    return {
        "sum": round(total_sum, 2),
        "currency": "USD",
        "fieldSummed": field_name,
        "totalItems": len(estimate_list),
        "matchedItems": len(filtered),
        "searchQuery": search_query or "ALL",
        "matchedExamples": examples
    }


async def execute_query_schedule(job_data: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute query_schedule tool"""
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
    
    # Filter by text search
    search_query = args.get("searchQuery")
    if search_query:
        filtered = [t for t in filtered if match_text(t, search_query, ["task", "remarks"])]
    
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
    
    if return_type == "count":
        return {
            "count": len(filtered),
            "totalTasks": len(schedule),
            "filtersApplied": {k: v for k, v in args.items() if v is not None and k != "returnType"}
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
            "filtersApplied": {k: v for k, v in args.items() if v is not None and k not in ["returnType", "fieldToSum"]}
        }
    
    else:  # list
        tasks_output = [format_task_summary(t) for t in filtered[:limit]]
        return {
            "tasks": tasks_output,
            "matchedCount": len(filtered),
            "returnedCount": len(tasks_output),
            "totalTasks": len(schedule),
            "filtersApplied": {k: v for k, v in args.items() if v is not None and k not in ["returnType", "limit"]}
        }


async def execute_get_task_details(job_data: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute get_task_details tool"""
    schedule = job_data.get("schedule", [])
    task_id = args.get("taskId")
    search_query = args.get("searchQuery")
    
    # Find task
    found_task = None
    
    if task_id:
        for t in schedule:
            if t.get("id") == task_id:
                found_task = t
                break
    
    if not found_task and search_query:
        for t in schedule:
            if match_text(t, search_query, ["task", "id"]):
                found_task = t
                break
    
    if not found_task:
        return {
            "error": "Task not found",
            "searchedFor": task_id or search_query,
            "availableTasks": [t.get("task") for t in schedule[:10]]
        }
    
    return format_task_details(found_task)


async def execute_query_task_hierarchy(job_data: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute query_task_hierarchy tool"""
    schedule = job_data.get("schedule", [])
    main_task_id = args.get("mainTaskId")
    main_task_search = args.get("mainTaskSearch")
    include_details = args.get("includeDetails", False)
    
    # Find main task
    main_task = None
    
    if main_task_id:
        for t in schedule:
            if t.get("id") == main_task_id and t.get("isMainTask"):
                main_task = t
                break
    
    if not main_task and main_task_search:
        for t in schedule:
            if t.get("isMainTask") and match_text(t, main_task_search, ["task"]):
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
    avg_completion = sum(t.get("percentageComplete", 0) for t in subtasks) / len(subtasks) if subtasks else 0
    
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


async def execute_query_dependencies(job_data: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute query_dependencies tool"""
    schedule = job_data.get("schedule", [])
    task_id = args.get("taskId")
    task_search = args.get("taskSearch")
    direction = args.get("direction", "predecessors")
    include_chain = args.get("includeChain", False)
    
    # Build lookup maps
    id_to_task = {t.get("id"): t for t in schedule}
    index_to_task = {str(t.get("index")): t for t in schedule}
    
    # Find target task
    target_task = None
    
    if task_id:
        target_task = id_to_task.get(task_id)
    
    if not target_task and task_search:
        for t in schedule:
            if match_text(t, task_search, ["task", "id"]):
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
        def get_predecessors(task, visited=None):
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
        
        def get_successors(task_id, task_index, visited=None):
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
                            chain_succs = get_successors(t.get("id"), str(t.get("index")), visited)
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


async def execute_query_payment_schedule(job_data: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute query_payment_schedule tool"""
    schedule = job_data.get("schedule", [])
    
    date_from = parse_date(args.get("dateFrom"))
    date_to = parse_date(args.get("dateTo"))
    task_type = args.get("taskType")
    task_search = args.get("taskSearch")
    return_type = args.get("returnType", "list")
    
    # Collect all payment stages
    all_payments = []
    
    for task in schedule:
        # Apply task filters
        if task_type and task.get("taskType") != task_type:
            continue
        
        if task_search and not match_text(task, task_search, ["task"]):
            continue
        
        total_amount = task.get("totalPaymentAmount", 0)
        if total_amount <= 0:
            continue
        
        for stage in task.get("paymentStages", []):
            effective_date = parse_date(stage.get("effectiveDate"))
            
            # Apply date filters
            if date_from and effective_date and effective_date < date_from:
                continue
            if date_to and effective_date and effective_date > date_to:
                continue
            
            pct = stage.get("percentage", 0)
            amount = total_amount * (pct / 100)
            
            all_payments.append({
                "taskId": task.get("id"),
                "taskName": task.get("task"),
                "taskType": task.get("taskType"),
                "stageName": stage.get("name"),
                "percentage": pct,
                "amount": round(amount, 2),
                "effectiveDate": stage.get("effectiveDate"),
                "isManualDate": stage.get("isManualDate", True),
                "taskStatus": get_task_status(task)
            })
    
    # Sort by date
    all_payments.sort(key=lambda x: x.get("effectiveDate") or "9999-12-31")
    
    if return_type == "summary":
        # Group by task type
        by_type = {}
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
            "filtersApplied": {k: v for k, v in args.items() if v is not None and k != "returnType"}
        }
    
    elif return_type == "timeline":
        # Group by month
        by_month = {}
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
            "filtersApplied": {k: v for k, v in args.items() if v is not None and k != "returnType"}
        }
    
    else:  # list
        grand_total = sum(p["amount"] for p in all_payments)
        
        return {
            "payments": all_payments,
            "totalPayments": len(all_payments),
            "grandTotal": round(grand_total, 2),
            "filtersApplied": {k: v for k, v in args.items() if v is not None and k != "returnType"}
        }


# =============================================================================
# MAIN AGENT FUNCTION
# =============================================================================

async def send_message_to_agent(
    message: str,
    history: List[Dict[str, Any]] = None,
    current_job_id: str = DEFAULT_JOB_ID
) -> ChatResponse:
    """
    Main function to handle chat interaction with Gemini agent
    """
    if history is None:
        history = []
    
    tool_executions: List[ToolExecution] = []
    switched_job_id: Optional[str] = None
    
    # Track the active Job ID during this conversation turn
    active_job_id_for_turn = current_job_id
    
    try:
        # Create model with tools
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            tools=[ALL_TOOLS],
            system_instruction=SYSTEM_INSTRUCTION
        )
        
        # Convert history to Gemini format
        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({
                "role": role,
                "parts": [msg["parts"][0]["text"]]
            })
        
        # Start chat
        chat = model.start_chat(history=gemini_history)
        
        # Send message
        response = chat.send_message(message)
        
        # Handle function calls (tool execution loop)
        MAX_TURNS = 10  # Increased for complex queries
        turns = 0
        
        while hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            
            # Check for function calls
            if not hasattr(candidate.content, 'parts'):
                break
            
            function_calls = [
                part.function_call 
                for part in candidate.content.parts 
                if hasattr(part, 'function_call')
            ]
            
            if not function_calls or turns >= MAX_TURNS:
                break
            
            turns += 1
            tool_responses = []
            
            for function_call in function_calls:
                name = function_call.name
                args = dict(function_call.args) if function_call.args else {}
                
                # Skip invalid function calls (empty name)
                if not name:
                    print(f"⚠️ [Agent] Skipping invalid function call with empty name")
                    continue
                
                print(f"🔧 [Agent] Calling Tool: {name}", args)
                
                result = None
                
                try:
                    # -----------------------------------------------------
                    # JOB TOOLS
                    # -----------------------------------------------------
                    if name == "search_jobs":
                        result = await search_jobs(args.get("query", ""), DEFAULT_COMPANY_ID)
                    
                    elif name == "get_current_job_data":
                        job_id = args.get("jobId")
                        result = await fetch_job_data(DEFAULT_COMPANY_ID, job_id)
                        active_job_id_for_turn = job_id
                        switched_job_id = job_id
                    
                    # -----------------------------------------------------
                    # ESTIMATE TOOLS
                    # -----------------------------------------------------
                    elif name == "calculate_estimate_sum":
                        job_data = await fetch_job_data(DEFAULT_COMPANY_ID, active_job_id_for_turn)
                        result = await execute_calculate_estimate_sum(job_data, args)
                    
                    # -----------------------------------------------------
                    # SCHEDULE TOOLS
                    # -----------------------------------------------------
                    elif name == "query_schedule":
                        job_data = await fetch_job_data(DEFAULT_COMPANY_ID, active_job_id_for_turn)
                        result = await execute_query_schedule(job_data, args)
                    
                    elif name == "get_task_details":
                        job_data = await fetch_job_data(DEFAULT_COMPANY_ID, active_job_id_for_turn)
                        result = await execute_get_task_details(job_data, args)
                    
                    elif name == "query_task_hierarchy":
                        job_data = await fetch_job_data(DEFAULT_COMPANY_ID, active_job_id_for_turn)
                        result = await execute_query_task_hierarchy(job_data, args)
                    
                    elif name == "query_dependencies":
                        job_data = await fetch_job_data(DEFAULT_COMPANY_ID, active_job_id_for_turn)
                        result = await execute_query_dependencies(job_data, args)
                    
                    # -----------------------------------------------------
                    # PAYMENT TOOLS
                    # -----------------------------------------------------
                    elif name == "query_payment_schedule":
                        job_data = await fetch_job_data(DEFAULT_COMPANY_ID, active_job_id_for_turn)
                        result = await execute_query_payment_schedule(job_data, args)
                    
                    # -----------------------------------------------------
                    # LEGACY TOOL (backward compatibility)
                    # -----------------------------------------------------
                    elif name == "calculate_field_sum":
                        job_data = await fetch_job_data(DEFAULT_COMPANY_ID, active_job_id_for_turn)
                        list_name = args.get("listName")
                        field_name = args.get("fieldName")
                        search_query = args.get("searchQuery", "")
                        
                        data_list = job_data.get(list_name, [])
                        
                        if isinstance(data_list, list):
                            search_fields = ["area", "description", "taskScope", "costCode", 
                                           "notesRemarks", "title", "task", "remarks"]
                            
                            if search_query and search_query.lower() not in ['all', '*']:
                                filtered_list = [item for item in data_list 
                                               if match_text(item, search_query, search_fields)]
                            else:
                                filtered_list = data_list
                            
                            total_sum = 0
                            for item in filtered_list:
                                value = item.get(field_name, 0)
                                try:
                                    total_sum += float(value) if value else 0
                                except (ValueError, TypeError):
                                    pass
                            
                            matched_examples = [
                                item.get("description") or item.get("task") or item.get("title")
                                for item in filtered_list[:5]
                            ]
                            
                            result = {
                                "sum": total_sum,
                                "currency": "USD",
                                "itemsCount": len(data_list),
                                "matchesFound": len(filtered_list),
                                "searchQueryUsed": search_query or "ALL",
                                "matchedExamples": matched_examples
                            }
                        else:
                            result = {"error": f"List '{list_name}' not found or is not an array."}
                    
                    else:
                        result = {"error": f"Unknown tool: {name}"}
                
                except Exception as err:
                    print(f"❌ Tool Error ({name}): {err}")
                    import traceback
                    traceback.print_exc()
                    result = {"error": str(err)}
                
                # Store tool execution
                tool_executions.append(ToolExecution(
                    id=str(time.time()),
                    toolName=name,
                    args=args,
                    result=result,
                    timestamp=time.time()
                ))
                
                # Prepare response for Gemini
                tool_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=name,
                            response={"result": result}
                        )
                    )
                )
            
            # Send tool responses back to model
            if tool_responses:
                response = chat.send_message(tool_responses)
        
        # Extract final text response
        final_text = response.text if hasattr(response, 'text') else "I processed the data but couldn't generate a text response."
        
        return ChatResponse(
            text=final_text,
            toolExecutions=tool_executions,
            switchedJobId=switched_job_id
        )
    
    except Exception as e:
        print(f"❌ Agent Error: {e}")
        import traceback
        traceback.print_exc()
        return ChatResponse(
            text="I'm sorry, I encountered an error. Please try again.",
            toolExecutions=tool_executions
        )