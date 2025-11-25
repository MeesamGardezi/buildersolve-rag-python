"""
Pydantic models for BuilderSolve Agent
Aligned with Flutter ScheduleRow, PaymentStage, and Dependency models
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Basic Data Structure Models
# ============================================================================

class Milestone(BaseModel):
    """Payment milestone model (project-level)"""
    title: str
    amount: float
    state: bool  # True = paid, False = unpaid


class CostCode(BaseModel):
    """Cost code model"""
    code: str
    description: str


class EstimateRow(BaseModel):
    """Estimate row model"""
    area: Optional[str] = None
    taskScope: Optional[str] = None
    costCode: Optional[str] = None
    description: Optional[str] = None
    units: Optional[str] = None
    qty: Optional[float] = None
    rate: Optional[float] = None
    total: float = 0.0  # Price to Client (ESTIMATE)
    budgetedRate: Optional[float] = None
    budgetedTotal: float = 0.0  # Internal Cost (BUDGET)
    notesRemarks: Optional[str] = None
    rowType: str = "estimate"  # 'estimate' | 'allowance'
    materials: Optional[List[Any]] = []


class FlooringEstimateRow(BaseModel):
    """Flooring estimate row model"""
    floorTypeId: Optional[str] = None
    vendor: Optional[str] = None
    itemMaterialName: Optional[str] = None
    brand: Optional[str] = None
    unit: Optional[str] = None
    measuredQty: Optional[float] = None
    supplierQty: Optional[float] = None
    wasteFactor: Optional[float] = None
    qtyIncludingWaste: Optional[float] = None
    unitPrice: Optional[float] = None
    costPrice: Optional[float] = None
    taxFreight: Optional[float] = None
    totalCost: Optional[float] = None
    salePrice: Optional[float] = None
    notesRemarks: Optional[str] = None


# ============================================================================
# Dependency Model (Aligned with Flutter)
# ============================================================================

class Dependency(BaseModel):
    """
    Task dependency model.
    
    Dependency Types:
    - FS (Finish-to-Start): B starts after A finishes (most common)
    - SS (Start-to-Start): B starts when A starts
    - FF (Finish-to-Finish): B finishes when A finishes
    - SF (Start-to-Finish): B finishes when A starts (rare)
    
    Lag: Offset in days (positive = delay, negative = overlap)
    """
    predecessorTaskId: str  # Index-based reference (legacy, can change)
    predecessorId: Optional[str] = None  # Static ID reference (preferred, stable)
    type: str = "FS"  # FS, SS, FF, SF
    lag: float = 0.0  # Offset in days
    
    @property
    def effective_predecessor_id(self) -> str:
        """Get the most appropriate ID to use"""
        return self.predecessorId if self.predecessorId else self.predecessorTaskId


# ============================================================================
# Payment Stage Model (Aligned with Flutter)
# ============================================================================

class PaymentStage(BaseModel):
    """
    Payment stage model for task-level payments.
    
    Typical patterns:
    - Material: 50% Initial + 50% Final
    - Subcontractor: 25% Downpayment + 75% Completion
    - Milestone: 100% at milestone date
    """
    id: str
    name: str  # e.g., "Initial Payment", "Final Payment", "Downpayment"
    percentage: float  # e.g., 50.0 = 50%
    isManualDate: bool = True  # True = user set date, False = linked to task
    linkedTaskId: Optional[str] = None  # If linked, which task's dates to use
    linkedType: Optional[str] = None  # 'start' or 'completion'
    lagDays: float = 0.0  # Offset from base date in days
    manualDate: Optional[str] = None  # User-specified date (ISO string)
    baseDate: Optional[str] = None  # Source date for calculation (ISO string)
    effectiveDate: Optional[str] = None  # Final calculated due date (ISO string)
    
    def calculate_amount(self, total_payment_amount: float) -> float:
        """Calculate the payment amount for this stage"""
        return total_payment_amount * (self.percentage / 100.0)


# ============================================================================
# Schedule Row Model (Aligned with Flutter)
# ============================================================================

class ScheduleRow(BaseModel):
    """
    Schedule task model - represents a single task in the project schedule.
    
    Task Types:
    - labour: Standard work tasks
    - milestone: Payment/progress markers (often zero duration)
    - material: Material procurement tasks
    - subcontractor: Work performed by subcontractors
    - others: Miscellaneous tasks
    """
    # Identification
    index: int  # UI position (can change when reordered)
    id: str  # Permanent static ID for dependencies
    task: str  # Task name/description
    
    # Task Classification
    taskType: str = "labour"  # labour, milestone, material, subcontractor, others
    
    # Time Fields
    hours: float = 0.0  # Planned/budgeted hours
    consumed: float = 0.0  # Hours already used
    duration: float = 0.0  # Duration in days
    
    # Dates (ISO Strings: "2024-05-01")
    startDate: Optional[str] = None  # Planned start
    endDate: Optional[str] = None  # Planned end
    actualStart: Optional[str] = None  # When work actually started
    actualEnd: Optional[str] = None  # When work actually finished
    baselineStartDate: Optional[str] = None  # Original planned start
    baselineEndDate: Optional[str] = None  # Original planned end
    
    # Progress
    percentageComplete: float = 0.0  # 0-100 (100 = completed)
    schedulingMode: str = "Automatic"  # 'Manual' | 'Automatic'
    
    # Critical Path
    isCritical: bool = False  # On critical path?
    totalSlack: float = 0.0  # Float time (days of flexibility)
    
    # Hierarchy (Main Tasks & Subtasks)
    isMainTask: bool = False  # True if parent/group task
    mainTaskIndex: Optional[int] = None  # Index of parent (if subtask)
    mainTaskId: Optional[str] = None  # Static ID of parent (preferred)
    isExpanded: Optional[bool] = True  # UI state
    subtaskIndices: Optional[List[int]] = None  # Child indices (if main task)
    subtaskIds: Optional[List[str]] = None  # Child static IDs (preferred)
    
    # Dependencies
    dependencies: List[Dependency] = []
    
    # Resources
    resources: Dict[str, Any] = {}
    
    # Payment
    paymentStages: List[PaymentStage] = []
    totalPaymentAmount: float = 0.0
    
    # Other
    remarks: str = ""
    isBaselineSet: bool = False
    
    def get_status(self) -> str:
        """Get human-readable status"""
        if self.percentageComplete >= 100:
            return "completed"
        elif self.percentageComplete > 0:
            return "in_progress"
        else:
            return "not_started"
    
    def get_payment_summary(self) -> Dict[str, Any]:
        """Get summary of payment stages"""
        if not self.paymentStages:
            return {"hasPayments": False, "stages": [], "totalAmount": 0}
        
        stages_summary = []
        for stage in self.paymentStages:
            stage_amount = stage.calculate_amount(self.totalPaymentAmount)
            stages_summary.append({
                "name": stage.name,
                "percentage": stage.percentage,
                "amount": stage_amount,
                "effectiveDate": stage.effectiveDate,
                "isManualDate": stage.isManualDate
            })
        
        return {
            "hasPayments": True,
            "totalAmount": self.totalPaymentAmount,
            "stageCount": len(self.paymentStages),
            "stages": stages_summary
        }

    class Config:
        """Pydantic config"""
        arbitrary_types_allowed = True


# ============================================================================
# Main Job Model
# ============================================================================

class Job(BaseModel):
    """Complete job/project model"""
    documentId: str
    estimateType: str
    hasFlooring: Optional[bool] = None
    isLocked: Optional[bool] = None
    scheduleActive: Optional[bool] = None
    
    # Rate Fields
    actualCarpentry: Optional[float] = None
    actualMaterialsSalesTax: Optional[float] = None
    actualOther: Optional[float] = None
    actualPainting: Optional[float] = None
    actualProjectManagementAssociate: Optional[float] = None
    actualProjectManagementPrincipal: Optional[float] = None
    actualProjectPlanningAssociate: Optional[float] = None
    actualProjectPlanningPrincipal: Optional[float] = None
    actualSupervisor: Optional[float] = None
    
    carpentry: Optional[float] = None
    materialMarkup: Optional[float] = None
    materialsSalesTax: Optional[float] = None
    other: Optional[float] = None
    subcontractorMarkup: Optional[float] = None
    otherJobCostsMarkup: Optional[float] = None
    painting: Optional[float] = None
    projectManagementAssociate: Optional[float] = None
    projectManagementPrincipal: Optional[float] = None
    projectPlanningAssociate: Optional[float] = None
    projectPlanningPrincipal: Optional[float] = None
    supervisor: Optional[float] = None
    
    # Project Info
    createdBy: Optional[str] = None
    createdDate: Optional[str] = None
    jobIndex: Optional[int] = None
    locations: Optional[str] = "[]"  # JSON string
    milestones: List[Milestone] = []
    projectDescription: Optional[str] = None
    projectTitle: str
    status: str
    taskIndex: Optional[int] = None
    
    # Client Fields
    clientEmail1: Optional[str] = None
    clientEmail2: Optional[str] = None
    clientName: str
    clientPhone: Optional[str] = None
    clientPhone2: Optional[str] = None
    contractDate: Optional[str] = None
    contractType: Optional[str] = None
    jobPrefix: Optional[str] = None
    proposalTitle: Optional[str] = None
    
    # Site Fields
    siteCity: Optional[str] = None
    siteState: Optional[str] = None
    siteStreet: Optional[str] = None
    siteZip: Optional[str] = None
    
    # Arrays
    costCodes: List[CostCode] = []
    estimate: List[EstimateRow] = []
    schedule: List[ScheduleRow] = []
    flooringEstimateData: List[FlooringEstimateRow] = []
    
    # Dynamic totals
    totals: Optional[Dict[str, Any]] = None

    class Config:
        """Pydantic config"""
        arbitrary_types_allowed = True


# ============================================================================
# Chat & API Models
# ============================================================================

class ChatMessagePart(BaseModel):
    """Part of a chat message"""
    text: str


class ChatMessageContent(BaseModel):
    """Chat message format for API"""
    role: str  # 'user' | 'model'
    parts: List[ChatMessagePart]


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str
    history: List[ChatMessageContent] = []
    currentJobId: Optional[str] = None


class ToolExecution(BaseModel):
    """Tool execution record"""
    id: str
    toolName: str
    args: Dict[str, Any]
    result: Any
    timestamp: float


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    text: str
    toolExecutions: List[ToolExecution] = []
    switchedJobId: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message model (for internal use)"""
    id: str
    role: str  # 'user' | 'model' | 'system'
    content: str
    timestamp: datetime
    isThinking: Optional[bool] = None
    toolExecutions: Optional[List[ToolExecution]] = None