"""
Job-related Pydantic models for BuilderSolve Agent
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


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
    
    # Arrays - imported as Any to avoid circular imports
    # Actual types: List[CostCode], List[EstimateRow], List[ScheduleRow], List[FlooringEstimateRow]
    costCodes: List[CostCode] = []
    estimate: List[EstimateRow] = []
    schedule: List[Any] = []  # ScheduleRow - defined in schedule.py
    flooringEstimateData: List[FlooringEstimateRow] = []
    
    # Dynamic totals
    totals: Optional[Dict[str, Any]] = None

    class Config:
        """Pydantic config"""
        arbitrary_types_allowed = Trues