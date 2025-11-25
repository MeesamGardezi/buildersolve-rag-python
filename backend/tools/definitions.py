"""
Gemini Tool Definitions for BuilderSolve Agent
All function declarations for the AI agent
"""

# =============================================================================
# JOB TOOLS
# =============================================================================

search_jobs_tool = {
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
}

get_job_data_tool = {
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
}

JOB_TOOLS = [search_jobs_tool, get_job_data_tool]

# =============================================================================
# ESTIMATE TOOLS
# =============================================================================

calculate_estimate_sum_tool = {
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
}

ESTIMATE_TOOLS = [calculate_estimate_sum_tool]

# =============================================================================
# SCHEDULE TOOLS
# =============================================================================

query_schedule_tool = {
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
}

get_task_details_tool = {
    "name": "get_task_details",
    "description": "Get full details of a specific task including payment stages, dependencies, dates, progress, and resources. Use when user asks about a specific task. For PAYMENT-RELATED queries, set onlyPaymentCapable=true to exclude labour tasks.",
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
            },
            "onlyPaymentCapable": {
                "type": "BOOLEAN",
                "description": "If true, only search tasks that CAN have payment stages (material, subcontractor, milestone). Use this for payment-related queries. Default false."
            }
        },
        "required": []
    }
}

query_task_hierarchy_tool = {
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
}

query_dependencies_tool = {
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
}

SCHEDULE_TOOLS = [
    query_schedule_tool,
    get_task_details_tool,
    query_task_hierarchy_tool,
    query_dependencies_tool,
]

# =============================================================================
# PAYMENT TOOLS
# =============================================================================

query_payment_schedule_tool = {
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
}

PAYMENT_TOOLS = [query_payment_schedule_tool]

# =============================================================================
# COMPARISON TOOLS
# =============================================================================

get_comparison_data_tool = {
    "name": "get_comparison_data",
    "description": "Fetches the budget vs actual comparison data for the current job. Returns summary totals and detailed rows for labour, material, subcontractor, and other costs. Use for questions about budget tracking, cost overruns, or comparing estimated vs actual expenses.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "jobId": {
                "type": "STRING",
                "description": "Optional job ID. If not provided, uses the current job context."
            }
        },
        "required": []
    }
}

query_comparison_rows_tool = {
    "name": "query_comparison_rows",
    "description": "Query and filter comparison rows (budget vs actual line items). Filter by category, tags, or cost code search. Use for detailed budget analysis questions.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "category": {
                "type": "STRING",
                "description": "Filter by category: 'labour', 'material', 'subcontractor', 'other', 'allowance', 'all'. Default 'all'."
            },
            "tag": {
                "type": "STRING",
                "description": "Filter by tag: 'alw' (allowance), 'est' (estimate), 'co' (change order). Omit for all."
            },
            "costCodeSearch": {
                "type": "STRING",
                "description": "Search by cost code. E.g., '503S', 'Kitchen', 'Plumbing'."
            },
            "overBudgetOnly": {
                "type": "BOOLEAN",
                "description": "If true, only return rows where consumed > budgeted (over budget). Default false."
            },
            "returnType": {
                "type": "STRING",
                "description": "'list' (matching rows), 'summary' (totals by category), 'count'. Default 'list'."
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum number of rows to return. Default 20."
            }
        },
        "required": []
    }
}

get_comparison_summary_tool = {
    "name": "get_comparison_summary",
    "description": "Get a high-level summary of budget vs actual for all categories. Returns budgeted amounts, consumed amounts, variance, and percentage used for labour hours, material costs, subcontractor costs, and other costs.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "includeSubcategories": {
                "type": "BOOLEAN",
                "description": "If true, include labour subcategory breakdowns (painting, carpentry, etc.). Default false."
            }
        },
        "required": []
    }
}

COMPARISON_TOOLS = [
    get_comparison_data_tool,
    query_comparison_rows_tool,
    get_comparison_summary_tool,
]

# =============================================================================
# COMBINED TOOLS FOR GEMINI
# =============================================================================

ALL_TOOLS = {
    "function_declarations": [
        # Job tools
        search_jobs_tool,
        get_job_data_tool,
        # Estimate tools
        calculate_estimate_sum_tool,
        # Schedule tools
        query_schedule_tool,
        get_task_details_tool,
        query_task_hierarchy_tool,
        query_dependencies_tool,
        # Payment tools
        query_payment_schedule_tool,
        # Comparison tools
        get_comparison_data_tool,
        query_comparison_rows_tool,
        get_comparison_summary_tool,
    ]
}