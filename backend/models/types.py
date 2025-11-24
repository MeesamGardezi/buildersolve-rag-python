"""
Pydantic models for BuilderSolve Agent
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Basic Data Structure Models
# ============================================================================

class Milestone(BaseModel):
    """Payment milestone model"""
    title: str
    amount: float
    state: bool


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


class Dependency(BaseModel):
    """Task dependency model"""
    predecessorTaskId: str
    predecessorId: Optional[str] = None
    type: str  # 'FS', 'SS', etc.
    lag: int = 0


class PaymentStage(BaseModel):
    """Payment stage model"""
    id: str
    name: str
    percentage: float
    isManualDate: bool
    manualDate: Optional[str] = None
    baseDate: Optional[str] = None
    effectiveDate: Optional[str] = None
    linkedTaskId: Optional[str] = None
    linkedType: Optional[str] = None
    lagDays: Optional[int] = None


class ScheduleRow(BaseModel):
    """Schedule row model"""
    index: int
    id: str  # Static ID
    task: str
    dependencies: List[Dependency] = []
    hours: float = 0.0
    consumed: float = 0.0
    duration: float = 0.0
    
    # Dates (ISO Strings)
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    actualStart: Optional[str] = None
    actualEnd: Optional[str] = None
    baselineStartDate: Optional[str] = None
    baselineEndDate: Optional[str] = None
    
    resources: Dict[str, Any] = {}
    percentageComplete: float = 0.0
    schedulingMode: str = "Automatic"  # 'Manual' | 'Automatic'
    taskType: str = "standard"
    remarks: Optional[str] = None
    
    # Structure
    isMainTask: bool = True
    mainTaskIndex: Optional[int] = None
    mainTaskId: Optional[str] = None
    isExpanded: Optional[bool] = None
    subtaskIndices: Optional[List[int]] = None
    subtaskIds: Optional[List[str]] = None
    
    # Analysis
    totalSlack: float = 0.0
    isCritical: bool = False
    isBaselineSet: bool = False
    
    paymentStages: List[PaymentStage] = []
    totalPaymentAmount: float = 0.0


# ============================================================================
# Main Job Model
# ============================================================================

class Job(BaseModel):
    """Complete job/project model"""
    documentId: str
    estimateType: str
    hasFlooring: Optional[bool] = None
    isLocked: Optional[bool] = None
    
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