"""
Comparison-related Pydantic models for BuilderSolve Agent
Aligned with Flutter ComparisonPage and comparison_models.dart
"""
from typing import List, Optional, Dict, Set, Any
from pydantic import BaseModel, Field


# =============================================================================
# SUMMARY MODELS
# =============================================================================

class LabourSummary(BaseModel):
    """Labour hours summary with subcategories"""
    budgetedHours: float = 0.0
    actualHours: float = 0.0
    
    # Project Planning subcategories
    PPbudgetedHours: float = 0.0  # Project Planning Principal
    PPactualHours: float = 0.0
    EPbudgetedHours: float = 0.0  # Estimating/Planning
    EPactualHours: float = 0.0
    
    # Painting subcategories
    PbudgetedHours: float = 0.0  # Painting
    PactualHours: float = 0.0
    IPbudgetedHours: float = 0.0  # Interior Painting
    IPactualHours: float = 0.0
    otherPaintingBudgetedHours: float = 0.0
    otherPaintingActualHours: float = 0.0
    
    # Carpentry subcategories
    CbudgetedHours: float = 0.0  # Carpentry
    CactualHours: float = 0.0
    CabinetBbudgetedHours: float = 0.0  # Cabinet Build
    CabinetBactualHours: float = 0.0
    CabinetIbudgetedHours: float = 0.0  # Cabinet Install
    CabinetIactualHours: float = 0.0
    CabinetPbudgetedHours: float = 0.0  # Cabinet Prep
    CabinetPactualHours: float = 0.0
    otherCarpentryBudgetedHours: float = 0.0
    otherCarpentryActualHours: float = 0.0
    
    @property
    def variance(self) -> float:
        """Difference between actual and budgeted hours"""
        return self.actualHours - self.budgetedHours
    
    @property
    def percentageUsed(self) -> float:
        """Percentage of budget consumed"""
        if self.budgetedHours > 0:
            return (self.actualHours / self.budgetedHours) * 100
        return 0.0
    
    @property
    def PPvariance(self) -> float:
        return self.PPactualHours - self.PPbudgetedHours
    
    @property
    def PPpercentageUsed(self) -> float:
        if self.PPbudgetedHours > 0:
            return (self.PPactualHours / self.PPbudgetedHours) * 100
        return 0.0
    
    @property
    def EPvariance(self) -> float:
        return self.EPactualHours - self.EPbudgetedHours
    
    @property
    def EPpercentageUsed(self) -> float:
        if self.EPbudgetedHours > 0:
            return (self.EPactualHours / self.EPbudgetedHours) * 100
        return 0.0
    
    @property
    def Pvariance(self) -> float:
        return self.PactualHours - self.PbudgetedHours
    
    @property
    def PpercentageUsed(self) -> float:
        if self.PbudgetedHours > 0:
            return (self.PactualHours / self.PbudgetedHours) * 100
        return 0.0
    
    @property
    def IPvariance(self) -> float:
        return self.IPactualHours - self.IPbudgetedHours
    
    @property
    def IPpercentageUsed(self) -> float:
        if self.IPbudgetedHours > 0:
            return (self.IPactualHours / self.IPbudgetedHours) * 100
        return 0.0
    
    @property
    def Cvariance(self) -> float:
        return self.CactualHours - self.CbudgetedHours
    
    @property
    def CpercentageUsed(self) -> float:
        if self.CbudgetedHours > 0:
            return (self.CactualHours / self.CbudgetedHours) * 100
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed properties"""
        return {
            "budgetedHours": self.budgetedHours,
            "actualHours": self.actualHours,
            "variance": self.variance,
            "percentageUsed": self.percentageUsed,
            "subcategories": {
                "projectPlanning": {
                    "budgeted": self.PPbudgetedHours,
                    "actual": self.PPactualHours,
                    "variance": self.PPvariance,
                    "percentageUsed": self.PPpercentageUsed,
                },
                "estimating": {
                    "budgeted": self.EPbudgetedHours,
                    "actual": self.EPactualHours,
                    "variance": self.EPvariance,
                    "percentageUsed": self.EPpercentageUsed,
                },
                "painting": {
                    "budgeted": self.PbudgetedHours,
                    "actual": self.PactualHours,
                    "variance": self.Pvariance,
                    "percentageUsed": self.PpercentageUsed,
                },
                "carpentry": {
                    "budgeted": self.CbudgetedHours,
                    "actual": self.CactualHours,
                    "variance": self.Cvariance,
                    "percentageUsed": self.CpercentageUsed,
                },
            }
        }


class MaterialSummary(BaseModel):
    """Material costs summary"""
    budgetedAmount: float = 0.0
    consumedAmount: float = 0.0
    
    @property
    def variance(self) -> float:
        """Difference between consumed and budgeted"""
        return self.consumedAmount - self.budgetedAmount
    
    @property
    def percentageUsed(self) -> float:
        """Percentage of budget consumed"""
        if self.budgetedAmount > 0:
            return (self.consumedAmount / self.budgetedAmount) * 100
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed properties"""
        return {
            "budgetedAmount": self.budgetedAmount,
            "consumedAmount": self.consumedAmount,
            "variance": self.variance,
            "percentageUsed": self.percentageUsed,
        }


class SubcontractorSummary(BaseModel):
    """Subcontractor costs summary"""
    budgetedAmount: float = 0.0
    consumedAmount: float = 0.0
    
    @property
    def variance(self) -> float:
        """Difference between consumed and budgeted"""
        return self.consumedAmount - self.budgetedAmount
    
    @property
    def percentageUsed(self) -> float:
        """Percentage of budget consumed"""
        if self.budgetedAmount > 0:
            return (self.consumedAmount / self.budgetedAmount) * 100
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed properties"""
        return {
            "budgetedAmount": self.budgetedAmount,
            "consumedAmount": self.consumedAmount,
            "variance": self.variance,
            "percentageUsed": self.percentageUsed,
        }


class OtherSummary(BaseModel):
    """Other costs summary"""
    budgetedAmount: float = 0.0
    consumedAmount: float = 0.0
    
    @property
    def variance(self) -> float:
        """Difference between consumed and budgeted"""
        return self.consumedAmount - self.budgetedAmount
    
    @property
    def percentageUsed(self) -> float:
        """Percentage of budget consumed"""
        if self.budgetedAmount > 0:
            return (self.consumedAmount / self.budgetedAmount) * 100
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed properties"""
        return {
            "budgetedAmount": self.budgetedAmount,
            "consumedAmount": self.consumedAmount,
            "variance": self.variance,
            "percentageUsed": self.percentageUsed,
        }


class ComparisonSummary(BaseModel):
    """Top-level comparison summary containing all category summaries"""
    labour: LabourSummary
    material: MaterialSummary
    subcontractor: SubcontractorSummary
    other: OtherSummary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with all computed properties"""
        return {
            "labour": self.labour.to_dict(),
            "material": self.material.to_dict(),
            "subcontractor": self.subcontractor.to_dict(),
            "other": self.other.to_dict(),
        }
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "ComparisonSummary":
        """Create from API response"""
        return cls(
            labour=LabourSummary(**data.get("labour", {})),
            material=MaterialSummary(**data.get("material", {})),
            subcontractor=SubcontractorSummary(**data.get("subcontractor", {})),
            other=OtherSummary(**data.get("other", {})),
        )


# =============================================================================
# ROW MODELS
# =============================================================================

class ComparisonRow(BaseModel):
    """
    Individual comparison row with cost code, amounts, and tags.
    
    Tags:
    - 'alw': Allowance
    - 'est': Estimate (original)
    - 'co': Change Order
    """
    costCode: str
    budgetedAmount: float = 0.0
    consumedAmount: float = 0.0
    rowType: Optional[str] = None  # 'estimate' | 'allowance'
    fromChangeOrder: bool = False
    tags: List[str] = Field(default_factory=list)  # ['alw', 'est', 'co']
    tagAmounts: Dict[str, float] = Field(default_factory=dict)  # {'alw': 1000.0, 'est': 500.0}
    consumedTagAmounts: Dict[str, float] = Field(default_factory=dict)
    
    @property
    def differenceAmount(self) -> float:
        """Budgeted minus consumed (positive = under budget)"""
        return self.budgetedAmount - self.consumedAmount
    
    @property
    def progress(self) -> float:
        """Percentage of budget consumed"""
        if self.budgetedAmount > 0:
            return (self.consumedAmount / self.budgetedAmount) * 100
        return 0.0
    
    @property
    def isAllowance(self) -> bool:
        """Check if this row is an allowance"""
        return (
            (self.rowType and self.rowType.lower() == "allowance") or
            "alw" in self.tags
        )
    
    @property
    def isChangeOrder(self) -> bool:
        """Check if this row is from a change order"""
        return self.fromChangeOrder or "co" in self.tags
    
    @property
    def isEstimate(self) -> bool:
        """Check if this row is from original estimate"""
        return not self.fromChangeOrder or "est" in self.tags
    
    def has_tag(self, tag: str) -> bool:
        """Check if this row has a specific tag"""
        return tag.lower() in [t.lower() for t in self.tags]
    
    def get_tag_amount(self, tag: str) -> float:
        """Get the budgeted amount for a specific tag"""
        return self.tagAmounts.get(tag.lower(), 0.0)
    
    def get_consumed_tag_amount(self, tag: str) -> float:
        """Get the consumed amount for a specific tag"""
        return self.consumedTagAmounts.get(tag.lower(), 0.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed properties"""
        return {
            "costCode": self.costCode,
            "budgetedAmount": self.budgetedAmount,
            "consumedAmount": self.consumedAmount,
            "differenceAmount": self.differenceAmount,
            "progress": self.progress,
            "rowType": self.rowType,
            "fromChangeOrder": self.fromChangeOrder,
            "tags": self.tags,
            "tagAmounts": self.tagAmounts,
            "consumedTagAmounts": self.consumedTagAmounts,
            "isAllowance": self.isAllowance,
            "isChangeOrder": self.isChangeOrder,
        }
    
    def merge_with(self, other: "ComparisonRow") -> "ComparisonRow":
        """Create a new row by merging this row with another"""
        # Combine amounts
        new_budgeted = self.budgetedAmount + other.budgetedAmount
        new_consumed = self.consumedAmount + other.consumedAmount
        
        # Determine row type
        new_row_type = "allowance" if (self.isAllowance or other.isAllowance) else (self.rowType or other.rowType)
        
        # Combine tags
        new_tags = list(set(self.tags) | set(other.tags))
        
        # Add source tags
        if self.fromChangeOrder or other.fromChangeOrder:
            if "co" not in new_tags:
                new_tags.append("co")
        else:
            if "est" not in new_tags:
                new_tags.append("est")
        
        if self.isAllowance or other.isAllowance:
            if "alw" not in new_tags:
                new_tags.append("alw")
        
        # Merge tag amounts
        new_tag_amounts = dict(self.tagAmounts)
        for tag, amount in other.tagAmounts.items():
            new_tag_amounts[tag] = new_tag_amounts.get(tag, 0.0) + amount
        
        # Merge consumed tag amounts
        new_consumed_tag_amounts = dict(self.consumedTagAmounts)
        for tag, amount in other.consumedTagAmounts.items():
            new_consumed_tag_amounts[tag] = new_consumed_tag_amounts.get(tag, 0.0) + amount
        
        return ComparisonRow(
            costCode=self.costCode,
            budgetedAmount=new_budgeted,
            consumedAmount=new_consumed,
            rowType=new_row_type,
            fromChangeOrder=self.fromChangeOrder or other.fromChangeOrder,
            tags=new_tags,
            tagAmounts=new_tag_amounts,
            consumedTagAmounts=new_consumed_tag_amounts,
        )
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "ComparisonRow":
        """Create from API response with proper type conversion"""
        # Ensure numeric values are floats
        budgeted = data.get("budgetedAmount", 0)
        consumed = data.get("consumedAmount", 0)
        
        if isinstance(budgeted, int):
            budgeted = float(budgeted)
        if isinstance(consumed, int):
            consumed = float(consumed)
        
        # Parse tags
        tags = []
        if data.get("tags") and isinstance(data["tags"], list):
            tags = list(data["tags"])
        else:
            # Generate default tags
            if data.get("fromChangeOrder"):
                tags.append("co")
            else:
                tags.append("est")
            
            if data.get("rowType", "").lower() == "allowance":
                tags.append("alw")
        
        # Parse tag amounts
        tag_amounts = {}
        if data.get("tagAmounts") and isinstance(data["tagAmounts"], dict):
            for k, v in data["tagAmounts"].items():
                tag_amounts[k] = float(v) if v is not None else 0.0
        
        # Parse consumed tag amounts
        consumed_tag_amounts = {}
        if data.get("consumedTagAmounts") and isinstance(data["consumedTagAmounts"], dict):
            for k, v in data["consumedTagAmounts"].items():
                consumed_tag_amounts[k] = float(v) if v is not None else 0.0
        
        return cls(
            costCode=data.get("costCode", ""),
            budgetedAmount=budgeted,
            consumedAmount=consumed,
            rowType=data.get("rowType"),
            fromChangeOrder=data.get("fromChangeOrder", False),
            tags=tags,
            tagAmounts=tag_amounts,
            consumedTagAmounts=consumed_tag_amounts,
        )


class CategorizedRows(BaseModel):
    """Container for comparison rows grouped by category"""
    labour: List[ComparisonRow] = Field(default_factory=list)
    material: List[ComparisonRow] = Field(default_factory=list)
    subcontractor: List[ComparisonRow] = Field(default_factory=list)
    others: List[ComparisonRow] = Field(default_factory=list)
    
    def get_all_rows(self) -> List[ComparisonRow]:
        """Get all rows from all categories"""
        return self.labour + self.material + self.subcontractor + self.others
    
    def get_allowance_rows(self) -> List[ComparisonRow]:
        """Get all rows that are allowances"""
        all_rows = self.get_all_rows()
        return [row for row in all_rows if row.has_tag("alw")]
    
    def get_change_order_rows(self) -> List[ComparisonRow]:
        """Get all rows that are from change orders"""
        all_rows = self.get_all_rows()
        return [row for row in all_rows if row.has_tag("co")]
    
    def filter_by_tag(self, tag: str) -> List[ComparisonRow]:
        """Get all rows with a specific tag"""
        all_rows = self.get_all_rows()
        return [row for row in all_rows if row.has_tag(tag)]
    
    def filter_by_cost_code(self, search_query: str) -> "CategorizedRows":
        """Filter all categories by cost code search"""
        query = search_query.lower()
        return CategorizedRows(
            labour=[r for r in self.labour if query in r.costCode.lower()],
            material=[r for r in self.material if query in r.costCode.lower()],
            subcontractor=[r for r in self.subcontractor if query in r.costCode.lower()],
            others=[r for r in self.others if query in r.costCode.lower()],
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "labour": [r.to_dict() for r in self.labour],
            "material": [r.to_dict() for r in self.material],
            "subcontractor": [r.to_dict() for r in self.subcontractor],
            "others": [r.to_dict() for r in self.others],
            "counts": {
                "labour": len(self.labour),
                "material": len(self.material),
                "subcontractor": len(self.subcontractor),
                "others": len(self.others),
                "total": len(self.get_all_rows()),
            }
        }
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "CategorizedRows":
        """Create from API response"""
        return cls(
            labour=[
                ComparisonRow.from_api_response(row)
                for row in data.get("labour", [])
            ],
            material=[
                ComparisonRow.from_api_response(row)
                for row in data.get("material", [])
            ],
            subcontractor=[
                ComparisonRow.from_api_response(row)
                for row in data.get("subcontractor", [])
            ],
            others=[
                ComparisonRow.from_api_response(row)
                for row in data.get("other", [])  # Note: API uses "other" not "others"
            ],
        )


# =============================================================================
# FULL COMPARISON DATA MODEL
# =============================================================================

class ComparisonData(BaseModel):
    """Complete comparison data including summary and details"""
    summary: ComparisonSummary
    details: CategorizedRows
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "summary": self.summary.to_dict(),
            "details": self.details.to_dict(),
        }
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "ComparisonData":
        """Create from API response"""
        return cls(
            summary=ComparisonSummary.from_api_response(data.get("summary", {})),
            details=CategorizedRows.from_api_response(data.get("details", {})),
        )