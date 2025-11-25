"""
Constants and configuration for BuilderSolve Agent
"""

DEFAULT_COMPANY_ID = "EcgWg9hK2Zdrd3joJ6Fd"
DEFAULT_JOB_ID = "4ZppggAAJuJMZNB8f2ZT"

GEMINI_MODEL = "gemini-2.5-flash"  # Excellent for tool calling and latency

# =============================================================================
# SYSTEM INSTRUCTION FOR GEMINI AGENT
# =============================================================================

SYSTEM_INSTRUCTION = """
You are an intelligent construction project manager agent for 'BuilderSolve'.

═══════════════════════════════════════════════════════════════════════════════
OPERATIONAL WORKFLOW
═══════════════════════════════════════════════════════════════════════════════

1. **JOB CONTEXT**: You have access to one job at a time.
2. **SWITCHING JOBS**: If the user asks about a different job (e.g., "What about the Hammond job?"), you MUST:
   a. Call 'search_jobs' with the name.
   b. Look at the results.
   c. Call 'get_current_job_data' with the correct 'documentId'.
   d. Answer the question using the new data.

═══════════════════════════════════════════════════════════════════════════════
AVAILABLE TOOLS - USE THE RIGHT TOOL FOR THE RIGHT QUESTION
═══════════════════════════════════════════════════════════════════════════════

**JOB TOOLS:**
- `search_jobs` - Find jobs by name, client, address
- `get_current_job_data` - Load full job context (switch jobs)

**ESTIMATE TOOLS:**
- `calculate_estimate_sum` - Sum estimate fields (total, budgetedTotal, qty, rate)

**SCHEDULE TOOLS:**
- `query_schedule` - Query/filter/sum tasks by type, status, dates, critical path
- `get_task_details` - Get full details of a specific task including payment stages and dependencies
- `query_task_hierarchy` - Get a main task and all its subtasks
- `query_dependencies` - Find predecessors or successors of a task

**PAYMENT TOOLS:**
- `query_payment_schedule` - Get payment stages by date range, task type, or task name

**COMPARISON TOOLS (Budget vs Actual):**
- `get_comparison_data` - Fetch full comparison data (summary + details) for budget tracking
- `query_comparison_rows` - Query/filter comparison line items by category, tag, cost code
- `get_comparison_summary` - Get high-level budget vs actual summary for all categories

═══════════════════════════════════════════════════════════════════════════════
ESTIMATE DATA INTERPRETATION
═══════════════════════════════════════════════════════════════════════════════

The 'estimate' list contains line items for the project quote.

**FIELDS:**
- `area` - Location/zone (Kitchen, Bathroom, Site, Exterior)
- `taskScope` - Work category (Demolition, Flooring, Electrical, Plumbing)
- `description` - Detailed description of the work
- `costCode` - Cost code reference (e.g., "02-100", "09-600")
- `qty` - Quantity of units
- `rate` - Rate per unit (price to client)
- `total` - **PRICE TO CLIENT** (Estimate amount)
- `budgetedRate` - Internal rate per unit
- `budgetedTotal` - **INTERNAL COST** (Budget/Expense to company)
- `rowType` - 'estimate' or 'allowance'
- `notesRemarks` - Additional notes

**CRITICAL RULES:**
- If user asks for "Cost", "Price", or "Estimate" → use `total`
- If user explicitly says "Budget" or "Internal Cost" → use `budgetedTotal`
- Profit = `total` - `budgetedTotal`

═══════════════════════════════════════════════════════════════════════════════
SCHEDULE DATA INTERPRETATION
═══════════════════════════════════════════════════════════════════════════════

The 'schedule' list contains all project tasks.

**IDENTIFICATION FIELDS:**
- `index` - UI position (can change when reordered)
- `id` - **PERMANENT STATIC ID** - used for dependencies and references
- `task` - Task name/description

**TASK TYPE FIELD (taskType):**
| Type           | Purpose                                      |
|----------------|----------------------------------------------|
| `labour`       | Standard work tasks performed by workers     |
| `milestone`    | Payment/progress markers (often zero duration)|
| `material`     | Material procurement tasks                   |
| `subcontractor`| Work performed by subcontractors             |
| `others`       | Miscellaneous tasks                          |

**TIME FIELDS:**
- `hours` - Planned/budgeted hours for the task
- `consumed` - Hours already used/spent
- `duration` - Duration in DAYS (not hours)
- `startDate` - Planned start date (ISO string: "2024-05-01")
- `endDate` - Planned end date
- `actualStart` - When work actually started
- `actualEnd` - When work actually finished
- `baselineStartDate` - Original planned start (for variance tracking)
- `baselineEndDate` - Original planned end

**PROGRESS FIELDS:**
- `percentageComplete` - Progress from 0 to 100
  - 0 = Not started
  - 1-99 = In progress
  - 100 = **COMPLETED**
- `schedulingMode` - 'Manual' or 'Automatic'

**CRITICAL PATH FIELDS:**
- `isCritical` - true if task is on the critical path (delays affect project end)
- `totalSlack` - Float time in days (flexibility before affecting project end)
  - 0 slack = Critical task
  - Positive slack = Can be delayed without affecting project

**HIERARCHY FIELDS (Main Tasks & Subtasks):**
- `isMainTask` - true if this is a parent/group task
- `mainTaskIndex` - Index of parent task (if this is a subtask)
- `mainTaskId` - **STATIC ID** of parent task (preferred reference)
- `subtaskIndices` - List of child task indices (if main task)
- `subtaskIds` - **STATIC IDs** of child tasks (preferred reference)

**OTHER FIELDS:**
- `remarks` - Notes/comments about the task
- `resources` - Map of assigned resources
- `isBaselineSet` - Whether baseline has been captured
- `isExpanded` - UI state for main tasks

**COMPLETION RULES:**
- A task is "COMPLETED" ONLY if `percentageComplete === 100`
- A task is "IN PROGRESS" if `percentageComplete` is between 1 and 99
- A task is "NOT STARTED" if `percentageComplete === 0`

═══════════════════════════════════════════════════════════════════════════════
DEPENDENCIES DATA INTERPRETATION
═══════════════════════════════════════════════════════════════════════════════

Each task can have a `dependencies` list defining predecessor relationships.

**DEPENDENCY FIELDS:**
- `predecessorTaskId` - Index-based reference (legacy, can change)
- `predecessorId` - **STATIC ID** reference (preferred, stable)
- `type` - Dependency type (see below)
- `lag` - Offset in days (can be positive or negative)

**DEPENDENCY TYPES:**
| Type | Name              | Meaning                                    |
|------|-------------------|---------------------------------------------|
| `FS` | Finish-to-Start   | B starts after A finishes (MOST COMMON)    |
| `SS` | Start-to-Start    | B starts when A starts                     |
| `FF` | Finish-to-Finish  | B finishes when A finishes                 |
| `SF` | Start-to-Finish   | B finishes when A starts (rare)            |

**LAG EXAMPLES:**
- FS with lag=0: B starts immediately after A finishes
- FS with lag=2: B starts 2 days after A finishes
- FS with lag=-1: B starts 1 day before A finishes (overlap)

═══════════════════════════════════════════════════════════════════════════════
PAYMENT STAGES DATA INTERPRETATION
═══════════════════════════════════════════════════════════════════════════════

Tasks (especially material, subcontractor, milestone types) can have `paymentStages`.

**PAYMENT STAGE FIELDS:**
- `id` - Unique identifier for the payment stage
- `name` - Stage name (e.g., "Initial Payment", "Final Payment", "Downpayment")
- `percentage` - Percentage of total amount (e.g., 50.0 = 50%)
- `isManualDate` - true if user manually set the date, false if linked to task
- `linkedTaskId` - If linked, which task's dates to use
- `linkedType` - 'start' or 'completion' (which date of linked task)
- `lagDays` - Offset from base date in days
- `manualDate` - User-specified payment date (if isManualDate=true)
- `baseDate` - Source date for calculation
- `effectiveDate` - **FINAL CALCULATED DUE DATE** for the payment

**TASK-LEVEL PAYMENT FIELDS:**
- `paymentStages` - List of PaymentStage objects
- `totalPaymentAmount` - Total dollar amount for all stages

**PAYMENT CALCULATION:**
- Stage Amount = `totalPaymentAmount` × (`percentage` / 100)
- Example: $10,000 total with 50% stage = $5,000 payment

**TYPICAL PAYMENT PATTERNS:**
| Task Type      | Typical Stages                                |
|----------------|-----------------------------------------------|
| Material       | 50% Initial (at start) + 50% Final (at end)  |
| Subcontractor  | 25% Downpayment + 75% on Completion          |
| Milestone      | 100% at milestone date                        |


═══════════════════════════════════════════════════════════════════════════════
PAYMENT QUERY INTELLIGENCE
═══════════════════════════════════════════════════════════════════════════════

**CRITICAL RULE:** Labour tasks NEVER have payment stages. Only these task types can have payments:
- `material` - Material procurement (e.g., Cabinet Order, Countertop Order)
- `subcontractor` - Subcontracted work (e.g., Electrical, Plumbing, Countertop Installation)
- `milestone` - Payment milestones

**When user asks about "payment stages for X":**
1. ALWAYS filter to taskType in ['material', 'subcontractor', 'milestone']
2. Use `query_payment_schedule(taskSearch='X')` OR `get_task_details` with payment-capable task types
3. NEVER return a labour task and say "no payment stages" - instead search for related material/sub/milestone tasks

**Example Interpretations:**
| User Says | Correct Interpretation |
|-----------|------------------------|
| "Payment stages for countertop" | Find material OR subcontractor tasks containing "countertop" |
| "Payment for electrical" | Find subcontractor task for electrical work |
| "When is cabinet payment due?" | Find material task for cabinet order |


═══════════════════════════════════════════════════════════════════════════════
MILESTONES - CRITICAL INTERPRETATION RULES
═══════════════════════════════════════════════════════════════════════════════

**DEFAULT BEHAVIOR: When user asks about "milestones", ALWAYS use SCHEDULE MILESTONES.**

There are two types of milestones in the system:

1. **SCHEDULE MILESTONES (PRIMARY - USE BY DEFAULT)**
   - Location: `schedule` list where `taskType='milestone'`
   - These are the main milestones users care about
   - They have dates, payment stages, completion status
   - Use `query_schedule(taskType='milestone')` or `query_payment_schedule(taskType='milestone')`

2. **PROJECT PAYMENT MILESTONES (SECONDARY - ONLY WHEN EXPLICITLY ASKED)**
   - Location: `milestones` list
   - Simple payment tracking: `title`, `amount`, `state` (paid/unpaid)
   - ONLY use when user explicitly says "project payment milestones" or "payment milestone list"

**INTERPRETATION RULES:**
| User Says | Tool to Use | Filter |
|-----------|-------------|--------|
| "What milestones are coming up?" | query_schedule OR query_payment_schedule | taskType='milestone' |
| "Upcoming milestones" | query_schedule | taskType='milestone', status='not_started' |
| "Completed milestones" | query_schedule | taskType='milestone', status='completed' |
| "Milestone payments" | query_payment_schedule | taskType='milestone' |
| "When is the next milestone?" | query_payment_schedule | taskType='milestone' (filter by date) |
| "What milestones have been paid?" | query_schedule | taskType='milestone', status='completed' |
| "Project payment milestones" | Use `milestones` list directly (rare) |

**IMPORTANT:** 
- 99 percent of the time, "milestone" means schedule milestones with `taskType='milestone'`
- These schedule milestones have `paymentStages` with amounts and due dates
- Do NOT default to the `milestones` list unless user explicitly mentions "project payment milestones"


═══════════════════════════════════════════════════════════════════════════════
COMPARISON DATA INTERPRETATION (Budget vs Actual)
═══════════════════════════════════════════════════════════════════════════════

The comparison data tracks budgeted vs consumed/actual amounts across categories.

**CATEGORIES:**
- `labour` - Labour hours (budgetedHours vs actualHours)
- `material` - Material costs (budgetedAmount vs consumedAmount)  
- `subcontractor` - Subcontractor costs (budgetedAmount vs consumedAmount)
- `other` - Other costs (budgetedAmount vs consumedAmount)

**COMPARISON ROW FIELDS:**
- `costCode` - Cost code identifier (e.g., "503S-Kitchen", "09-600")
- `budgetedAmount` - Originally budgeted amount
- `consumedAmount` - Amount actually spent/consumed
- `differenceAmount` - budgetedAmount - consumedAmount (positive = under budget)
- `progress` - Percentage consumed (consumedAmount / budgetedAmount * 100)
- `isOverBudget` - true if consumed > budgeted

**TAGS (Source Tracking):**
- `alw` - Allowance item
- `est` - From original estimate
- `co` - From change order

**TAG AMOUNTS:**
- `tagAmounts` - Budgeted amounts broken down by tag source
- `consumedTagAmounts` - Consumed amounts broken down by tag source

**COMMON QUESTIONS:**
| User Says | Tool to Use |
|-----------|-------------|
| "How are we tracking against budget?" | get_comparison_summary |
| "What items are over budget?" | query_comparison_rows(overBudgetOnly=true) |
| "Show me all allowance items" | query_comparison_rows(tag='alw') |
| "Material cost comparison" | query_comparison_rows(category='material') |
| "Budget breakdown by category" | get_comparison_summary |
| "Labour hours used vs budgeted" | get_comparison_summary(includeSubcategories=true) |


═══════════════════════════════════════════════════════════════════════════════
FORMATTING RULES
═══════════════════════════════════════════════════════════════════════════════

- Money: $X,XXX.XX (e.g., $1,500.00)
- Dates: Month Day, Year (e.g., "May 15, 2024")
- Percentages: X% (e.g., 50%)
- Duration: X days (e.g., 5 days)
- Hours: X hours (e.g., 40 hours)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE QUESTIONS AND TOOL USAGE
═══════════════════════════════════════════════════════════════════════════════

**Estimate Questions:**
- "Total estimate for Kitchen?" → calculate_estimate_sum(fieldName='total', searchQuery='Kitchen')
- "Internal budget for demolition?" → calculate_estimate_sum(fieldName='budgetedTotal', searchQuery='Demolition')

**Schedule Questions:**
- "How many labour tasks?" → query_schedule(taskType='labour', returnType='count')
- "Total hours for material tasks?" → query_schedule(taskType='material', fieldToSum='hours')
- "Which tasks are on critical path?" → query_schedule(isCritical=true, returnType='list')
- "Tasks starting next week?" → query_schedule(startDateFrom='2024-05-20', startDateTo='2024-05-27', returnType='list')
- "Completed milestones?" → query_schedule(taskType='milestone', status='completed', returnType='list')

**Task Detail Questions:**
- "Tell me about the Framing task" → get_task_details(searchQuery='Framing')
- "Payment schedule for Electrical?" → get_task_details(searchQuery='Electrical')

**Hierarchy Questions:**
- "Subtasks under Site Preparation?" → query_task_hierarchy(mainTaskSearch='Site Preparation')

**Dependency Questions:**
- "What comes before Kitchen Flooring?" → query_dependencies(taskSearch='Kitchen Flooring', direction='predecessors')
- "What depends on Demolition?" → query_dependencies(taskSearch='Demolition', direction='successors')

**Payment Questions:**
- "Payments due this month?" → query_payment_schedule(dateFrom='2024-05-01', dateTo='2024-05-31')
- "Total material payments?" → query_payment_schedule(taskType='material')
- "When is next payment for Electrical?" → query_payment_schedule(taskSearch='Electrical')

**Comparison Questions (Budget vs Actual):**
- "How are we tracking against budget?" → get_comparison_summary()
- "What's over budget?" → query_comparison_rows(overBudgetOnly=true)
- "Show allowance items" → query_comparison_rows(tag='alw')
- "Material budget breakdown" → query_comparison_rows(category='material')
- "Labour hours comparison with details" → get_comparison_summary(includeSubcategories=true)
"""

# =============================================================================
# MOCK JOB DATA (Unchanged from original)
# =============================================================================

MOCK_JOB_DATA = {
    "documentId": DEFAULT_JOB_ID,
    "projectTitle": "MOCK: Smith Residence Kitchen Remodel",
    "clientName": "John & Jane Smith",
    "status": "Production",
    "siteStreet": "123 Maple Avenue",
    "siteCity": "Springfield",
    "siteState": "IL",
    "siteZip": "62701",
    "clientEmail1": "john.smith@email.com",
    "clientPhone": "(555) 123-4567",
    "estimateType": "general",
    "jobPrefix": "SMT-2024",
    
    # =========================================================================
    # ESTIMATE DATA
    # =========================================================================
    "estimate": [
        {
            "area": "Kitchen",
            "taskScope": "Demolition",
            "description": "Remove existing cabinets and countertops",
            "total": 2500.00,
            "budgetedTotal": 1800.00,
            "costCode": "02-100",
            "rowType": "estimate",
            "qty": 1,
            "rate": 2500.00,
            "budgetedRate": 1800.00
        },
        {
            "area": "Kitchen",
            "taskScope": "Electrical",
            "description": "Rewire kitchen circuits and add outlets",
            "total": 4200.00,
            "budgetedTotal": 3200.00,
            "costCode": "16-100",
            "rowType": "estimate",
            "qty": 1,
            "rate": 4200.00,
            "budgetedRate": 3200.00
        },
        {
            "area": "Kitchen",
            "taskScope": "Plumbing",
            "description": "Install new sink and dishwasher connections",
            "total": 3500.00,
            "budgetedTotal": 2600.00,
            "costCode": "15-100",
            "rowType": "estimate",
            "qty": 1,
            "rate": 3500.00,
            "budgetedRate": 2600.00
        },
        {
            "area": "Kitchen",
            "taskScope": "Flooring",
            "description": "Install hardwood flooring - 200 sq ft",
            "total": 6000.00,
            "budgetedTotal": 4500.00,
            "costCode": "09-600",
            "rowType": "estimate",
            "qty": 200,
            "rate": 30.00,
            "budgetedRate": 22.50
        },
        {
            "area": "Kitchen",
            "taskScope": "Cabinets",
            "description": "Custom cabinet installation",
            "total": 12000.00,
            "budgetedTotal": 9000.00,
            "costCode": "06-400",
            "rowType": "estimate",
            "qty": 1,
            "rate": 12000.00,
            "budgetedRate": 9000.00
        },
        {
            "area": "Kitchen",
            "taskScope": "Countertops",
            "description": "Granite countertop installation",
            "total": 5500.00,
            "budgetedTotal": 4000.00,
            "costCode": "06-600",
            "rowType": "allowance",
            "qty": 40,
            "rate": 137.50,
            "budgetedRate": 100.00
        },
        {
            "area": "Site",
            "taskScope": "Cleanup",
            "description": "Final cleanup and debris removal",
            "total": 800.00,
            "budgetedTotal": 500.00,
            "costCode": "01-100",
            "rowType": "estimate",
            "qty": 1,
            "rate": 800.00,
            "budgetedRate": 500.00
        }
    ],
    
    # =========================================================================
    # MILESTONES (Payment Milestones)
    # =========================================================================
    "milestones": [
        {"title": "Contract Signing Deposit", "amount": 5000.00, "state": True},
        {"title": "Demolition Complete", "amount": 5000.00, "state": True},
        {"title": "Rough-In Complete", "amount": 8000.00, "state": False},
        {"title": "Cabinets Installed", "amount": 8000.00, "state": False},
        {"title": "Final Completion", "amount": 8500.00, "state": False}
    ],
    
    # =========================================================================
    # SCHEDULE DATA (with various task types, dependencies, payment stages)
    # =========================================================================
    "schedule": [
        # MAIN TASK: Site Preparation (with subtasks)
        {
            "index": 0,
            "id": "task_main_site_prep",
            "task": "Site Preparation",
            "taskType": "labour",
            "isMainTask": True,
            "subtaskIndices": [1, 2],
            "subtaskIds": ["task_permit", "task_protection"],
            "dependencies": [],
            "hours": 0,
            "consumed": 0,
            "duration": 3,
            "startDate": "2024-05-01",
            "endDate": "2024-05-03",
            "percentageComplete": 100,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {},
            "remarks": "",
            "isBaselineSet": True,
            "isExpanded": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        {
            "index": 1,
            "id": "task_permit",
            "task": "Obtain permits",
            "taskType": "labour",
            "isMainTask": False,
            "mainTaskIndex": 0,
            "mainTaskId": "task_main_site_prep",
            "dependencies": [],
            "hours": 8,
            "consumed": 8,
            "duration": 1,
            "startDate": "2024-05-01",
            "endDate": "2024-05-01",
            "percentageComplete": 100,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {"pm": {"name": "Mike Johnson", "role": "Project Manager"}},
            "remarks": "Permits approved",
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        {
            "index": 2,
            "id": "task_protection",
            "task": "Floor and wall protection",
            "taskType": "labour",
            "isMainTask": False,
            "mainTaskIndex": 0,
            "mainTaskId": "task_main_site_prep",
            "dependencies": [
                {"predecessorTaskId": "1", "predecessorId": "task_permit", "type": "FS", "lag": 0}
            ],
            "hours": 16,
            "consumed": 16,
            "duration": 2,
            "startDate": "2024-05-02",
            "endDate": "2024-05-03",
            "percentageComplete": 100,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {"crew1": {"name": "Labor Crew A", "role": "General Labor"}},
            "remarks": "",
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        
        # DEMOLITION TASK
        {
            "index": 3,
            "id": "task_demo",
            "task": "Kitchen Demolition",
            "taskType": "labour",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "2", "predecessorId": "task_protection", "type": "FS", "lag": 0}
            ],
            "hours": 40,
            "consumed": 40,
            "duration": 5,
            "startDate": "2024-05-06",
            "endDate": "2024-05-10",
            "percentageComplete": 100,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {"crew1": {"name": "Demo Crew", "role": "Demolition"}},
            "remarks": "Demo complete, debris hauled",
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        
        # ELECTRICAL (Subcontractor with payments)
        {
            "index": 4,
            "id": "task_electrical",
            "task": "Electrical Rough-In",
            "taskType": "subcontractor",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "3", "predecessorId": "task_demo", "type": "FS", "lag": 0}
            ],
            "hours": 32,
            "consumed": 32,
            "duration": 4,
            "startDate": "2024-05-13",
            "endDate": "2024-05-16",
            "percentageComplete": 100,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {"elec": {"name": "Sparks Electric LLC", "role": "Electrical Contractor"}},
            "remarks": "Passed inspection",
            "isBaselineSet": True,
            "paymentStages": [
                {
                    "id": "ps_elec_1",
                    "name": "Downpayment",
                    "percentage": 25.0,
                    "isManualDate": False,
                    "linkedTaskId": "task_electrical",
                    "linkedType": "start",
                    "lagDays": 0,
                    "manualDate": None,
                    "baseDate": "2024-05-13",
                    "effectiveDate": "2024-05-13"
                },
                {
                    "id": "ps_elec_2",
                    "name": "Completion Payment",
                    "percentage": 75.0,
                    "isManualDate": False,
                    "linkedTaskId": "task_electrical",
                    "linkedType": "completion",
                    "lagDays": 7,
                    "manualDate": None,
                    "baseDate": "2024-05-16",
                    "effectiveDate": "2024-05-23"
                }
            ],
            "totalPaymentAmount": 4200.00
        },
        
        # PLUMBING (Subcontractor)
        {
            "index": 5,
            "id": "task_plumbing",
            "task": "Plumbing Rough-In",
            "taskType": "subcontractor",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "3", "predecessorId": "task_demo", "type": "FS", "lag": 0}
            ],
            "hours": 24,
            "consumed": 24,
            "duration": 3,
            "startDate": "2024-05-13",
            "endDate": "2024-05-15",
            "percentageComplete": 100,
            "isCritical": False,
            "totalSlack": 1,
            "schedulingMode": "Automatic",
            "resources": {"plumb": {"name": "Quality Plumbing Co", "role": "Plumbing Contractor"}},
            "remarks": "Passed inspection",
            "isBaselineSet": True,
            "paymentStages": [
                {
                    "id": "ps_plumb_1",
                    "name": "Downpayment",
                    "percentage": 25.0,
                    "isManualDate": False,
                    "linkedTaskId": "task_plumbing",
                    "linkedType": "start",
                    "lagDays": 0,
                    "manualDate": None,
                    "baseDate": "2024-05-13",
                    "effectiveDate": "2024-05-13"
                },
                {
                    "id": "ps_plumb_2",
                    "name": "Completion Payment",
                    "percentage": 75.0,
                    "isManualDate": False,
                    "linkedTaskId": "task_plumbing",
                    "linkedType": "completion",
                    "lagDays": 7,
                    "manualDate": None,
                    "baseDate": "2024-05-15",
                    "effectiveDate": "2024-05-22"
                }
            ],
            "totalPaymentAmount": 3500.00
        },
        
        # CABINET ORDER (Material with payments)
        {
            "index": 6,
            "id": "task_cabinet_order",
            "task": "Cabinet Order & Delivery",
            "taskType": "material",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "3", "predecessorId": "task_demo", "type": "SS", "lag": 0}
            ],
            "hours": 0,
            "consumed": 0,
            "duration": 21,
            "startDate": "2024-05-06",
            "endDate": "2024-05-27",
            "percentageComplete": 100,
            "isCritical": False,
            "totalSlack": 5,
            "schedulingMode": "Automatic",
            "resources": {"vendor": {"name": "Custom Cabinets Inc", "role": "Cabinet Supplier"}},
            "remarks": "3-week lead time, delivered on schedule",
            "isBaselineSet": True,
            "paymentStages": [
                {
                    "id": "ps_cab_1",
                    "name": "Initial Deposit",
                    "percentage": 50.0,
                    "isManualDate": False,
                    "linkedTaskId": "task_cabinet_order",
                    "linkedType": "start",
                    "lagDays": 0,
                    "manualDate": None,
                    "baseDate": "2024-05-06",
                    "effectiveDate": "2024-05-06"
                },
                {
                    "id": "ps_cab_2",
                    "name": "Balance on Delivery",
                    "percentage": 50.0,
                    "isManualDate": False,
                    "linkedTaskId": "task_cabinet_order",
                    "linkedType": "completion",
                    "lagDays": 0,
                    "manualDate": None,
                    "baseDate": "2024-05-27",
                    "effectiveDate": "2024-05-27"
                }
            ],
            "totalPaymentAmount": 9000.00
        },
        
        # COUNTERTOP ORDER (Material)
        {
            "index": 7,
            "id": "task_countertop_order",
            "task": "Countertop Template & Order",
            "taskType": "material",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "6", "predecessorId": "task_cabinet_order", "type": "FS", "lag": -7}
            ],
            "hours": 0,
            "consumed": 0,
            "duration": 14,
            "startDate": "2024-05-20",
            "endDate": "2024-06-03",
            "percentageComplete": 50,
            "isCritical": False,
            "totalSlack": 3,
            "schedulingMode": "Automatic",
            "resources": {"vendor": {"name": "Granite Masters", "role": "Countertop Supplier"}},
            "remarks": "Template done, fabrication in progress",
            "isBaselineSet": True,
            "paymentStages": [
                {
                    "id": "ps_counter_1",
                    "name": "Deposit",
                    "percentage": 50.0,
                    "isManualDate": False,
                    "linkedTaskId": "task_countertop_order",
                    "linkedType": "start",
                    "lagDays": 0,
                    "manualDate": None,
                    "baseDate": "2024-05-20",
                    "effectiveDate": "2024-05-20"
                },
                {
                    "id": "ps_counter_2",
                    "name": "Balance Due",
                    "percentage": 50.0,
                    "isManualDate": False,
                    "linkedTaskId": "task_countertop_order",
                    "linkedType": "completion",
                    "lagDays": 0,
                    "manualDate": None,
                    "baseDate": "2024-06-03",
                    "effectiveDate": "2024-06-03"
                }
            ],
            "totalPaymentAmount": 4000.00
        },
        
        # FLOORING
        {
            "index": 8,
            "id": "task_flooring",
            "task": "Hardwood Flooring Installation",
            "taskType": "labour",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "4", "predecessorId": "task_electrical", "type": "FS", "lag": 0},
                {"predecessorTaskId": "5", "predecessorId": "task_plumbing", "type": "FS", "lag": 0}
            ],
            "hours": 24,
            "consumed": 16,
            "duration": 3,
            "startDate": "2024-05-17",
            "endDate": "2024-05-20",
            "percentageComplete": 65,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {"floor": {"name": "Precision Floors", "role": "Flooring Installer"}},
            "remarks": "Hardwood acclimating, installation started",
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        
        # DRYWALL
        {
            "index": 9,
            "id": "task_drywall",
            "task": "Drywall Repair & Paint",
            "taskType": "labour",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "4", "predecessorId": "task_electrical", "type": "FS", "lag": 0}
            ],
            "hours": 32,
            "consumed": 0,
            "duration": 4,
            "startDate": "2024-05-17",
            "endDate": "2024-05-21",
            "percentageComplete": 0,
            "isCritical": False,
            "totalSlack": 6,
            "schedulingMode": "Automatic",
            "resources": {"paint": {"name": "Pro Painters", "role": "Drywall/Paint"}},
            "remarks": "",
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        
        # CABINET INSTALLATION
        {
            "index": 10,
            "id": "task_cabinet_install",
            "task": "Cabinet Installation",
            "taskType": "labour",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "6", "predecessorId": "task_cabinet_order", "type": "FS", "lag": 0},
                {"predecessorTaskId": "8", "predecessorId": "task_flooring", "type": "FS", "lag": 0}
            ],
            "hours": 40,
            "consumed": 0,
            "duration": 5,
            "startDate": "2024-05-28",
            "endDate": "2024-06-03",
            "percentageComplete": 0,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {"cab": {"name": "Cabinet Pros", "role": "Cabinet Installer"}},
            "remarks": "",
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        
        # COUNTERTOP INSTALLATION
        {
            "index": 11,
            "id": "task_countertop_install",
            "task": "Countertop Installation",
            "taskType": "subcontractor",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "7", "predecessorId": "task_countertop_order", "type": "FS", "lag": 0},
                {"predecessorTaskId": "10", "predecessorId": "task_cabinet_install", "type": "FS", "lag": 0}
            ],
            "hours": 8,
            "consumed": 0,
            "duration": 1,
            "startDate": "2024-06-04",
            "endDate": "2024-06-04",
            "percentageComplete": 0,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {"granite": {"name": "Granite Masters", "role": "Countertop Installer"}},
            "remarks": "",
            "isBaselineSet": True,
            "paymentStages": [
                {
                    "id": "ps_ctinst_1",
                    "name": "Installation Payment",
                    "percentage": 100.0,
                    "isManualDate": False,
                    "linkedTaskId": "task_countertop_install",
                    "linkedType": "completion",
                    "lagDays": 0,
                    "manualDate": None,
                    "baseDate": "2024-06-04",
                    "effectiveDate": "2024-06-04"
                }
            ],
            "totalPaymentAmount": 1500.00
        },
        
        # FINAL FINISHES (Main Task)
        {
            "index": 12,
            "id": "task_main_finishes",
            "task": "Final Finishes",
            "taskType": "labour",
            "isMainTask": True,
            "subtaskIndices": [13, 14],
            "subtaskIds": ["task_hardware", "task_appliances"],
            "dependencies": [
                {"predecessorTaskId": "11", "predecessorId": "task_countertop_install", "type": "FS", "lag": 0}
            ],
            "hours": 0,
            "consumed": 0,
            "duration": 3,
            "startDate": "2024-06-05",
            "endDate": "2024-06-07",
            "percentageComplete": 0,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {},
            "remarks": "",
            "isBaselineSet": True,
            "isExpanded": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        {
            "index": 13,
            "id": "task_hardware",
            "task": "Hardware & Fixtures Installation",
            "taskType": "labour",
            "isMainTask": False,
            "mainTaskIndex": 12,
            "mainTaskId": "task_main_finishes",
            "dependencies": [
                {"predecessorTaskId": "11", "predecessorId": "task_countertop_install", "type": "FS", "lag": 0}
            ],
            "hours": 8,
            "consumed": 0,
            "duration": 1,
            "startDate": "2024-06-05",
            "endDate": "2024-06-05",
            "percentageComplete": 0,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {"crew1": {"name": "Finish Crew", "role": "Finishes"}},
            "remarks": "",
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        {
            "index": 14,
            "id": "task_appliances",
            "task": "Appliance Installation",
            "taskType": "labour",
            "isMainTask": False,
            "mainTaskIndex": 12,
            "mainTaskId": "task_main_finishes",
            "dependencies": [
                {"predecessorTaskId": "13", "predecessorId": "task_hardware", "type": "FS", "lag": 0}
            ],
            "hours": 16,
            "consumed": 0,
            "duration": 2,
            "startDate": "2024-06-06",
            "endDate": "2024-06-07",
            "percentageComplete": 0,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {"crew1": {"name": "Appliance Team", "role": "Appliance Installer"}},
            "remarks": "",
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        },
        
        # MILESTONES
        {
            "index": 15,
            "id": "task_milestone_roughin",
            "task": "Milestone: Rough-In Complete",
            "taskType": "milestone",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "4", "predecessorId": "task_electrical", "type": "FS", "lag": 0},
                {"predecessorTaskId": "5", "predecessorId": "task_plumbing", "type": "FS", "lag": 0}
            ],
            "hours": 0,
            "consumed": 0,
            "duration": 0,
            "startDate": "2024-05-16",
            "endDate": "2024-05-16",
            "percentageComplete": 100,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {},
            "remarks": "All rough-in inspections passed",
            "isBaselineSet": True,
            "paymentStages": [
                {
                    "id": "ps_ms_roughin",
                    "name": "Rough-In Milestone Payment",
                    "percentage": 100.0,
                    "isManualDate": True,
                    "linkedTaskId": None,
                    "linkedType": None,
                    "lagDays": 0,
                    "manualDate": "2024-05-16",
                    "baseDate": "2024-05-16",
                    "effectiveDate": "2024-05-16"
                }
            ],
            "totalPaymentAmount": 8000.00
        },
        {
            "index": 16,
            "id": "task_milestone_complete",
            "task": "Milestone: Project Complete",
            "taskType": "milestone",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "14", "predecessorId": "task_appliances", "type": "FS", "lag": 0}
            ],
            "hours": 0,
            "consumed": 0,
            "duration": 0,
            "startDate": "2024-06-07",
            "endDate": "2024-06-07",
            "percentageComplete": 0,
            "isCritical": True,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {},
            "remarks": "",
            "isBaselineSet": True,
            "paymentStages": [
                {
                    "id": "ps_ms_complete",
                    "name": "Final Project Payment",
                    "percentage": 100.0,
                    "isManualDate": True,
                    "linkedTaskId": None,
                    "linkedType": None,
                    "lagDays": 0,
                    "manualDate": "2024-06-07",
                    "baseDate": "2024-06-07",
                    "effectiveDate": "2024-06-07"
                }
            ],
            "totalPaymentAmount": 8500.00
        },
        
        # FINAL CLEANUP
        {
            "index": 17,
            "id": "task_cleanup",
            "task": "Final Cleanup & Punchlist",
            "taskType": "others",
            "isMainTask": False,
            "dependencies": [
                {"predecessorTaskId": "16", "predecessorId": "task_milestone_complete", "type": "FS", "lag": 0}
            ],
            "hours": 8,
            "consumed": 0,
            "duration": 1,
            "startDate": "2024-06-10",
            "endDate": "2024-06-10",
            "percentageComplete": 0,
            "isCritical": False,
            "totalSlack": 0,
            "schedulingMode": "Automatic",
            "resources": {"crew1": {"name": "Cleanup Crew", "role": "Cleanup"}},
            "remarks": "",
            "isBaselineSet": True,
            "paymentStages": [],
            "totalPaymentAmount": 0
        }
    ],
    
    # =========================================================================
    # OTHER FIELDS
    # =========================================================================
    "costCodes": [
        {"code": "01-100", "description": "General Requirements"},
        {"code": "02-100", "description": "Demolition"},
        {"code": "06-400", "description": "Cabinetry"},
        {"code": "06-600", "description": "Countertops"},
        {"code": "09-600", "description": "Flooring"},
        {"code": "15-100", "description": "Plumbing"},
        {"code": "16-100", "description": "Electrical"}
    ],
    "flooringEstimateData": [],
    "scheduleActive": True
}