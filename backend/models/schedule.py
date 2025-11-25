"""
Schedule-related Pydantic models for BuilderSolve Agent
Aligned with Flutter ScheduleRow, PaymentStage, and Dependency models
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


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