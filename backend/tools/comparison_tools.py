"""
Comparison tool handlers for BuilderSolve Agent
Budget vs Actual comparison queries
"""
import os
import ssl
from typing import Dict, Any, List, Optional
import aiohttp
import certifi

from .helpers import fuzzy_match, match_text, ensure_float


# API base URL for comparison data
COMPARISON_API_BASE = "https://api.managi.tech/getjobcomparison"

# SSL context for API requests (handles certificate issues)
def get_ssl_context():
    """Get SSL context, with fallback for development environments."""
    try:
        # Try using certifi certificates first
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        return ssl_context
    except Exception:
        # Fallback: disable verification in development (NOT for production)
        if os.getenv("ENVIRONMENT", "development") == "development":
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
        raise


async def fetch_comparison_from_api(
    company_id: str,
    job_id: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch comparison data from the external API.
    
    Args:
        company_id: Company document ID
        job_id: Job document ID
        
    Returns:
        API response data or None if failed
    """
    url = f"{COMPARISON_API_BASE}/{company_id}/{job_id}"
    
    try:
        # Create connector with SSL context
        ssl_context = get_ssl_context()
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"❌ Comparison API error: {response.status}")
                    return None
    except aiohttp.ClientError as e:
        print(f"❌ Comparison API request failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Comparison API unexpected error: {e}")
        return None


def parse_comparison_rows(
    rows_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Parse and normalize comparison rows from API.
    
    Args:
        rows_data: List of row dictionaries from API
        
    Returns:
        List of normalized row dictionaries
    """
    parsed = []
    for row in rows_data:
        budgeted = ensure_float(row.get("budgetedAmount", 0))
        consumed = ensure_float(row.get("consumedAmount", 0))
        difference = budgeted - consumed
        progress = (consumed / budgeted * 100) if budgeted > 0 else 0
        
        # Parse tags
        tags = []
        if row.get("tags") and isinstance(row["tags"], list):
            tags = list(row["tags"])
        else:
            # Generate default tags
            if row.get("fromChangeOrder"):
                tags.append("co")
            else:
                tags.append("est")
            if row.get("rowType", "").lower() == "allowance":
                tags.append("alw")
        
        # Parse tag amounts
        tag_amounts = {}
        if row.get("tagAmounts") and isinstance(row["tagAmounts"], dict):
            for k, v in row["tagAmounts"].items():
                tag_amounts[k] = ensure_float(v)
        
        consumed_tag_amounts = {}
        if row.get("consumedTagAmounts") and isinstance(row["consumedTagAmounts"], dict):
            for k, v in row["consumedTagAmounts"].items():
                consumed_tag_amounts[k] = ensure_float(v)
        
        parsed.append({
            "costCode": row.get("costCode", ""),
            "budgetedAmount": budgeted,
            "consumedAmount": consumed,
            "differenceAmount": round(difference, 2),
            "progress": round(progress, 1),
            "rowType": row.get("rowType"),
            "fromChangeOrder": row.get("fromChangeOrder", False),
            "tags": tags,
            "tagAmounts": tag_amounts,
            "consumedTagAmounts": consumed_tag_amounts,
            "isOverBudget": consumed > budgeted,
            "isAllowance": "alw" in tags,
            "isChangeOrder": "co" in tags,
        })
    
    return parsed


async def execute_get_comparison_data(
    company_id: str,
    job_id: str,
    args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute get_comparison_data tool.
    
    Fetches the complete budget vs actual comparison data.
    
    Args:
        company_id: Company document ID
        job_id: Job document ID (can be overridden by args)
        args: Tool arguments
        
    Returns:
        Dictionary with summary and details
    """
    # Allow job_id override
    target_job_id = args.get("jobId") or job_id
    
    # Fetch from API
    api_data = await fetch_comparison_from_api(company_id, target_job_id)
    
    if not api_data:
        return {
            "error": "Failed to fetch comparison data from API. The service may be unavailable.",
            "jobId": target_job_id,
            "suggestion": "Try again later or check if the job has comparison data available."
        }
    
    # Parse summary
    summary = api_data.get("summary", {})
    
    # Parse details
    details = api_data.get("details", {})
    
    labour_rows = parse_comparison_rows(details.get("labour", []))
    material_rows = parse_comparison_rows(details.get("material", []))
    subcontractor_rows = parse_comparison_rows(details.get("subcontractor", []))
    other_rows = parse_comparison_rows(details.get("other", []))
    
    return {
        "summary": {
            "labour": {
                "budgetedHours": ensure_float(summary.get("labour", {}).get("budgetedHours", 0)),
                "actualHours": ensure_float(summary.get("labour", {}).get("actualHours", 0)),
                "percentageUsed": ensure_float(summary.get("labour", {}).get("percentageUsed", 0)),
            },
            "material": {
                "budgetedAmount": ensure_float(summary.get("material", {}).get("budgetedAmount", 0)),
                "consumedAmount": ensure_float(summary.get("material", {}).get("consumedAmount", 0)),
                "percentageUsed": ensure_float(summary.get("material", {}).get("percentageUsed", 0)),
            },
            "subcontractor": {
                "budgetedAmount": ensure_float(summary.get("subcontractor", {}).get("budgetedAmount", 0)),
                "consumedAmount": ensure_float(summary.get("subcontractor", {}).get("consumedAmount", 0)),
                "percentageUsed": ensure_float(summary.get("subcontractor", {}).get("percentageUsed", 0)),
            },
            "other": {
                "budgetedAmount": ensure_float(summary.get("other", {}).get("budgetedAmount", 0)),
                "consumedAmount": ensure_float(summary.get("other", {}).get("consumedAmount", 0)),
                "percentageUsed": ensure_float(summary.get("other", {}).get("percentageUsed", 0)),
            },
        },
        "details": {
            "labour": labour_rows,
            "material": material_rows,
            "subcontractor": subcontractor_rows,
            "other": other_rows,
        },
        "counts": {
            "labour": len(labour_rows),
            "material": len(material_rows),
            "subcontractor": len(subcontractor_rows),
            "other": len(other_rows),
            "total": len(labour_rows) + len(material_rows) + len(subcontractor_rows) + len(other_rows),
        },
        "jobId": target_job_id,
    }


async def execute_query_comparison_rows(
    company_id: str,
    job_id: str,
    args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute query_comparison_rows tool.
    
    Query and filter comparison rows with various criteria.
    
    Args:
        company_id: Company document ID
        job_id: Job document ID
        args: Tool arguments for filtering
        
    Returns:
        Dictionary with filtered results
    """
    # First fetch the full data
    full_data = await execute_get_comparison_data(company_id, job_id, {})
    
    if "error" in full_data:
        return full_data
    
    category = args.get("category", "all").lower()
    tag = args.get("tag")
    cost_code_search = args.get("costCodeSearch")
    over_budget_only = args.get("overBudgetOnly", False)
    return_type = args.get("returnType", "list")
    limit = args.get("limit", 20)
    
    # Get rows based on category
    details = full_data.get("details", {})
    
    if category == "all":
        all_rows = (
            details.get("labour", []) +
            details.get("material", []) +
            details.get("subcontractor", []) +
            details.get("other", [])
        )
    elif category == "allowance":
        # Get all allowance rows across categories
        all_rows = []
        for cat_rows in details.values():
            if isinstance(cat_rows, list):
                all_rows.extend([r for r in cat_rows if r.get("isAllowance")])
    elif category in details:
        all_rows = details.get(category, [])
    else:
        all_rows = details.get("other", [])  # fallback
    
    # Apply filters
    filtered = all_rows
    
    # Filter by tag
    if tag:
        tag_lower = tag.lower()
        filtered = [
            r for r in filtered 
            if tag_lower in [t.lower() for t in r.get("tags", [])]
        ]
    
    # Filter by cost code search (with fuzzy matching)
    if cost_code_search:
        filtered = [
            r for r in filtered
            if fuzzy_match(cost_code_search, r.get("costCode", ""))
        ]
    
    # Filter by over budget
    if over_budget_only:
        filtered = [r for r in filtered if r.get("isOverBudget")]
    
    # Build filters applied dict
    filters_applied = {
        k: v for k, v in args.items()
        if v is not None and k not in ["returnType", "limit"]
    }
    
    if return_type == "count":
        return {
            "count": len(filtered),
            "totalRows": len(all_rows),
            "filtersApplied": filters_applied
        }
    
    elif return_type == "summary":
        # Calculate totals by category
        by_category: Dict[str, Dict[str, Any]] = {}
        
        for row in filtered:
            # Determine category from the row data
            # We'll track it during iteration
            cat = "other"
            for cat_name in ["labour", "material", "subcontractor", "other"]:
                if row in details.get(cat_name, []):
                    cat = cat_name
                    break
            
            if cat not in by_category:
                by_category[cat] = {
                    "count": 0,
                    "budgetedTotal": 0.0,
                    "consumedTotal": 0.0,
                    "overBudgetCount": 0,
                }
            
            by_category[cat]["count"] += 1
            by_category[cat]["budgetedTotal"] += row.get("budgetedAmount", 0)
            by_category[cat]["consumedTotal"] += row.get("consumedAmount", 0)
            if row.get("isOverBudget"):
                by_category[cat]["overBudgetCount"] += 1
        
        # Round totals
        for cat in by_category:
            by_category[cat]["budgetedTotal"] = round(by_category[cat]["budgetedTotal"], 2)
            by_category[cat]["consumedTotal"] = round(by_category[cat]["consumedTotal"], 2)
        
        grand_budgeted = sum(c["budgetedTotal"] for c in by_category.values())
        grand_consumed = sum(c["consumedTotal"] for c in by_category.values())
        
        return {
            "byCategory": by_category,
            "grandBudgeted": round(grand_budgeted, 2),
            "grandConsumed": round(grand_consumed, 2),
            "grandDifference": round(grand_budgeted - grand_consumed, 2),
            "totalRows": len(filtered),
            "filtersApplied": filters_applied
        }
    
    else:  # list
        return {
            "rows": filtered[:limit],
            "matchedCount": len(filtered),
            "returnedCount": min(len(filtered), limit),
            "filtersApplied": filters_applied
        }


async def execute_get_comparison_summary(
    company_id: str,
    job_id: str,
    args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute get_comparison_summary tool.
    
    Get high-level budget vs actual summary for all categories.
    
    Args:
        company_id: Company document ID
        job_id: Job document ID
        args: Tool arguments
        
    Returns:
        Dictionary with category summaries
    """
    include_subcategories = args.get("includeSubcategories", False)
    
    # Fetch from API
    api_data = await fetch_comparison_from_api(company_id, job_id)
    
    if not api_data:
        return {
            "error": "Failed to fetch comparison data from API. The service may be unavailable.",
            "jobId": job_id,
            "suggestion": "Try again later or check if the job has comparison data available."
        }
    
    summary = api_data.get("summary", {})
    
    # Labour summary
    labour = summary.get("labour", {})
    labour_budgeted = ensure_float(labour.get("budgetedHours", 0))
    labour_actual = ensure_float(labour.get("actualHours", 0))
    labour_pct = (labour_actual / labour_budgeted * 100) if labour_budgeted > 0 else 0
    
    labour_result: Dict[str, Any] = {
        "budgetedHours": labour_budgeted,
        "actualHours": labour_actual,
        "variance": round(labour_actual - labour_budgeted, 2),
        "percentageUsed": round(labour_pct, 1),
        "isOverBudget": labour_actual > labour_budgeted,
    }
    
    # Add subcategories if requested
    if include_subcategories:
        labour_result["subcategories"] = {
            "projectPlanning": {
                "budgeted": ensure_float(labour.get("PPbudgetedHours", 0)),
                "actual": ensure_float(labour.get("PPactualHours", 0)),
            },
            "estimating": {
                "budgeted": ensure_float(labour.get("EPbudgetedHours", 0)),
                "actual": ensure_float(labour.get("EPactualHours", 0)),
            },
            "painting": {
                "budgeted": ensure_float(labour.get("PbudgetedHours", 0)),
                "actual": ensure_float(labour.get("PactualHours", 0)),
            },
            "carpentry": {
                "budgeted": ensure_float(labour.get("CbudgetedHours", 0)),
                "actual": ensure_float(labour.get("CactualHours", 0)),
            },
        }
    
    # Material summary
    material = summary.get("material", {})
    material_budgeted = ensure_float(material.get("budgetedAmount", 0))
    material_consumed = ensure_float(material.get("consumedAmount", 0))
    material_pct = (material_consumed / material_budgeted * 100) if material_budgeted > 0 else 0
    
    material_result = {
        "budgetedAmount": material_budgeted,
        "consumedAmount": material_consumed,
        "variance": round(material_consumed - material_budgeted, 2),
        "percentageUsed": round(material_pct, 1),
        "isOverBudget": material_consumed > material_budgeted,
    }
    
    # Subcontractor summary
    subcontractor = summary.get("subcontractor", {})
    sub_budgeted = ensure_float(subcontractor.get("budgetedAmount", 0))
    sub_consumed = ensure_float(subcontractor.get("consumedAmount", 0))
    sub_pct = (sub_consumed / sub_budgeted * 100) if sub_budgeted > 0 else 0
    
    subcontractor_result = {
        "budgetedAmount": sub_budgeted,
        "consumedAmount": sub_consumed,
        "variance": round(sub_consumed - sub_budgeted, 2),
        "percentageUsed": round(sub_pct, 1),
        "isOverBudget": sub_consumed > sub_budgeted,
    }
    
    # Other summary
    other = summary.get("other", {})
    other_budgeted = ensure_float(other.get("budgetedAmount", 0))
    other_consumed = ensure_float(other.get("consumedAmount", 0))
    other_pct = (other_consumed / other_budgeted * 100) if other_budgeted > 0 else 0
    
    other_result = {
        "budgetedAmount": other_budgeted,
        "consumedAmount": other_consumed,
        "variance": round(other_consumed - other_budgeted, 2),
        "percentageUsed": round(other_pct, 1),
        "isOverBudget": other_consumed > other_budgeted,
    }
    
    # Grand totals (excluding labour hours - those are separate)
    grand_budgeted = material_budgeted + sub_budgeted + other_budgeted
    grand_consumed = material_consumed + sub_consumed + other_consumed
    
    return {
        "labour": labour_result,
        "material": material_result,
        "subcontractor": subcontractor_result,
        "other": other_result,
        "grandTotals": {
            "budgetedAmount": round(grand_budgeted, 2),
            "consumedAmount": round(grand_consumed, 2),
            "variance": round(grand_consumed - grand_budgeted, 2),
            "percentageUsed": round((grand_consumed / grand_budgeted * 100) if grand_budgeted > 0 else 0, 1),
        },
        "labourHours": {
            "budgeted": labour_budgeted,
            "actual": labour_actual,
        },
        "jobId": job_id,
    }