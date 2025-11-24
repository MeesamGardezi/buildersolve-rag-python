"""
Constants and configuration for BuilderSolve Agent
"""

DEFAULT_COMPANY_ID = "EcgWg9hK2Zdrd3joJ6Fd"
DEFAULT_JOB_ID = "4ZppggAAJuJMZNB8f2ZT"

GEMINI_MODEL = "gemini-2.5-flash"  # Excellent for tool calling and latency

# Fallback Mock Data if Firestore is not configured or fails
MOCK_JOB_DATA = {
    "documentId": DEFAULT_JOB_ID,
    "projectTitle": "MOCK: Smith Residence (Please Config Firebase)",
    "clientName": "John & Jane Smith",
    "status": "In Planning",
    "siteStreet": "123 Maple Avenue",
    "siteCity": "Springfield",
    "estimateType": "general",
    "estimate": [
        {
            "area": "Kitchen",
            "taskScope": "Demolition",
            "description": "Remove existing cabinets",
            "total": 1500.00,
            "budgetedTotal": 1200.00,
            "costCode": "02-100",
            "rowType": "estimate"
        },
        {
            "area": "Kitchen",
            "taskScope": "Flooring",
            "description": "Install new hardwood",
            "total": 4500.00,
            "budgetedTotal": 3800.00,
            "costCode": "09-600",
            "rowType": "estimate"
        },
        {
            "area": "Site",
            "taskScope": "Cleanup",
            "description": "General Site Cleanup Materials",
            "total": 655.50,
            "budgetedTotal": 475.00,
            "costCode": "01-100",
            "rowType": "estimate"
        }
    ],
    "schedule": [
        {
            "id": "task_1",
            "index": 0,
            "task": "Site Preparation",
            "startDate": "2024-05-01",
            "endDate": "2024-05-03",
            "duration": 3,
            "percentageComplete": 100,
            "isCritical": True,
            "hours": 24,
            "consumed": 24,
            "isMainTask": True,
            "dependencies": [],
            "resources": {},
            "schedulingMode": "Automatic",
            "taskType": "standard",
            "remarks": "",
            "totalSlack": 0,
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        {
            "id": "task_2",
            "index": 1,
            "task": "Kitchen Demolition",
            "startDate": "2024-05-04",
            "endDate": "2024-05-10",
            "duration": 7,
            "percentageComplete": 50,
            "isCritical": True,
            "hours": 56,
            "consumed": 28,
            "isMainTask": True,
            "dependencies": [{"predecessorTaskId": "task_1", "type": "FS", "lag": 0}],
            "resources": {},
            "schedulingMode": "Automatic",
            "taskType": "standard",
            "remarks": "",
            "totalSlack": 0,
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        }
    ],
    "milestones": [
        {"title": "Initial Deposit", "amount": 2000.00, "state": True},
        {"title": "Demolition Complete", "amount": 1500.00, "state": False},
        {"title": "Rough-In Complete", "amount": 2500.00, "state": False},
        {"title": "Final Payment", "amount": 3000.00, "state": False}
    ],
    "costCodes": [],
    "flooringEstimateData": [],
    "clientEmail1": "john.smith@email.com",
    "clientPhone": "(555) 123-4567",
    "siteState": "IL",
    "siteZip": "62701"
}

# System Instruction for Gemini Agent
SYSTEM_INSTRUCTION = """
You are an intelligent construction project manager agent for 'BuilderSolve'. 

OPERATIONAL WORKFLOW:
1. **JOB CONTEXT**: You have access to one job at a time. 
2. **SWITCHING JOBS**: If the user asks about a different job (e.g., "What about the Hammond job?"), you MUST:
   a. Call 'search_jobs' with the name.
   b. Look at the results.
   c. Call 'get_current_job_data' with the correct 'documentId'.
   d. Answer the question using the new data.

CRITICAL DATA INTERPRETATION RULES (FINANCIAL):
- **'total' Field**: This represents the **ESTIMATED PRICE** charged to the client.
- **'budgetedTotal' Field**: This represents the **INTERNAL BUDGET** or **EXPENSE** to the company.
- **Profit**: 'total' - 'budgetedTotal'.
- **RULE**: If the user asks for "Cost", "Price", or "Estimate" without explicitly saying "Budget", use **'total'**.

CRITICAL DATA INTERPRETATION RULES (SCHEDULE & MILESTONES):
- **SCHEDULE**: The 'schedule' list contains all tasks.
- **COMPLETED MILESTONES**: 
  - A task in the 'schedule' is considered a "Completed Milestone" or "Finished Phase" ONLY if **percentageComplete === 100**.
  - If the user asks "What milestones are complete?", look at the 'schedule' list and filter for 100% completion.
- **Dates**: 'startDate', 'endDate'.
- **Critical Path**: 'isCritical' = true.

FORMATTING:
- Money: $X,XXX.XX
- Dates: Month Day, Year (e.g. "Oct 12, 2024")
- Percentages: X%
"""