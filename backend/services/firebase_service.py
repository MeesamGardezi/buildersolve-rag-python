"""
Firebase Firestore service for job data retrieval
Enhanced parsing for schedule, payment stages, and dependencies
"""
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import constants
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import DEFAULT_COMPANY_ID, DEFAULT_JOB_ID, MOCK_JOB_DATA


# =============================================================================
# FIREBASE INITIALIZATION
# =============================================================================

db = None

def initialize_firebase() -> Optional[firestore.Client]:
    """Initialize Firebase and return Firestore client."""
    global db
    
    try:
        # Check if Firebase is already initialized
        if firebase_admin._apps:
            db = firestore.client()
            return db
        
        # Try to get credentials from environment or file
        cred_json = os.getenv('FIREBASE_CREDENTIALS')
        
        if cred_json:
            # Parse JSON from environment variable
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # Try to load from file (for local development)
            cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'service-account-key.json')
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            else:
                print("⚠️  Firebase credentials not found. Using Mock Data.")
                return None
        
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase initialized successfully")
        return db
        
    except Exception as e:
        print(f"❌ Error initializing Firebase: {e}")
        print("⚠️  Falling back to Mock Data")
        return None


# Initialize on module load
initialize_firebase()


# =============================================================================
# PARSING HELPERS
# =============================================================================

def convert_timestamps(data: Any) -> Any:
    """
    Recursively convert Firestore Timestamps to ISO strings.
    Handles nested structures (lists and dicts).
    """
    if data is None:
        return data
    
    # Handle Firestore Timestamp
    if hasattr(data, 'timestamp'):
        return datetime.fromtimestamp(data.timestamp()).isoformat()
    
    # Handle datetime objects
    if isinstance(data, datetime):
        return data.isoformat()
    
    # Handle Arrays
    if isinstance(data, list):
        return [convert_timestamps(item) for item in data]
    
    # Handle Dictionaries
    if isinstance(data, dict):
        return {key: convert_timestamps(value) for key, value in data.items()}
    
    return data


def parse_date_field(value: Any) -> Optional[str]:
    """
    Parse various date formats to ISO string (YYYY-MM-DD).
    
    Handles:
    - String dates (already formatted)
    - Firestore Timestamps
    - Integer timestamps (milliseconds)
    - datetime objects
    """
    if value is None:
        return None
    
    if isinstance(value, str):
        return value
    
    if hasattr(value, 'timestamp'):
        # Firestore Timestamp
        dt = datetime.fromtimestamp(value.timestamp())
        return dt.strftime('%Y-%m-%d')
    
    if isinstance(value, int):
        # Milliseconds since epoch
        dt = datetime.fromtimestamp(value / 1000)
        return dt.strftime('%Y-%m-%d')
    
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    
    return None


def parse_dependency(dep_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a dependency object from Firestore."""
    return {
        "predecessorTaskId": str(dep_data.get("predecessorTaskId", "")),
        "predecessorId": dep_data.get("predecessorId"),
        "type": dep_data.get("type", "FS"),
        "lag": float(dep_data.get("lag", 0))
    }


def parse_payment_stage(stage_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a payment stage object from Firestore."""
    return {
        "id": stage_data.get("id", ""),
        "name": stage_data.get("name", ""),
        "percentage": float(stage_data.get("percentage", 0)),
        "isManualDate": stage_data.get("isManualDate", True),
        "linkedTaskId": stage_data.get("linkedTaskId"),
        "linkedType": stage_data.get("linkedType"),
        "lagDays": float(stage_data.get("lagDays", 0)),
        "manualDate": parse_date_field(stage_data.get("manualDate")),
        "baseDate": parse_date_field(stage_data.get("baseDate")),
        "effectiveDate": parse_date_field(stage_data.get("effectiveDate"))
    }


def parse_schedule_row(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a schedule row with full support for:
    - Task identification and typing
    - Date fields (with format normalization)
    - Dependencies
    - Payment stages
    - Hierarchy (main tasks / subtasks)
    """
    # Parse dependencies
    dependencies = []
    if task_data.get("dependencies"):
        for dep in task_data["dependencies"]:
            if isinstance(dep, dict):
                dependencies.append(parse_dependency(dep))
    
    # Parse payment stages
    payment_stages = []
    if task_data.get("paymentStages"):
        for stage in task_data["paymentStages"]:
            if isinstance(stage, dict):
                payment_stages.append(parse_payment_stage(stage))
    
    # Parse resources
    resources = {}
    if task_data.get("resources") and isinstance(task_data["resources"], dict):
        for key, value in task_data["resources"].items():
            if isinstance(value, dict):
                resources[key] = dict(value)
            else:
                resources[key] = {"name": str(value), "role": "Unknown"}
    
    return {
        # Identification
        "index": int(task_data.get("index", 0)),
        "id": task_data.get("id", f"task_{task_data.get('index', 0)}"),
        "task": task_data.get("task", ""),
        
        # Task type
        "taskType": task_data.get("taskType", "labour"),
        
        # Time fields
        "hours": float(task_data.get("hours", 0)),
        "consumed": float(task_data.get("consumed", 0)),
        "duration": float(task_data.get("duration", 0)),
        
        # Dates (normalized to ISO strings)
        "startDate": parse_date_field(task_data.get("startDate")),
        "endDate": parse_date_field(task_data.get("endDate")),
        "actualStart": parse_date_field(task_data.get("actualStart")),
        "actualEnd": parse_date_field(task_data.get("actualEnd")),
        "baselineStartDate": parse_date_field(task_data.get("baselineStartDate")),
        "baselineEndDate": parse_date_field(task_data.get("baselineEndDate")),
        
        # Progress
        "percentageComplete": float(task_data.get("percentageComplete", 0)),
        "schedulingMode": task_data.get("schedulingMode", "Automatic"),
        
        # Critical path
        "isCritical": bool(task_data.get("isCritical", False)),
        "totalSlack": float(task_data.get("totalSlack", 0)),
        
        # Hierarchy
        "isMainTask": bool(task_data.get("isMainTask", False)),
        "mainTaskIndex": task_data.get("mainTaskIndex"),
        "mainTaskId": task_data.get("mainTaskId"),
        "isExpanded": bool(task_data.get("isExpanded", True)),
        "subtaskIndices": task_data.get("subtaskIndices"),
        "subtaskIds": task_data.get("subtaskIds"),
        
        # Dependencies
        "dependencies": dependencies,
        
        # Resources
        "resources": resources,
        
        # Payments
        "paymentStages": payment_stages,
        "totalPaymentAmount": float(task_data.get("totalPaymentAmount", 0)),
        
        # Other
        "remarks": task_data.get("remarks", ""),
        "isBaselineSet": bool(task_data.get("isBaselineSet", False))
    }


# =============================================================================
# DATA FETCHING FUNCTIONS
# =============================================================================

async def search_jobs(
    query: str,
    company_id: str = DEFAULT_COMPANY_ID
) -> List[Dict[str, Any]]:
    """
    Search for jobs in Firestore matching the query string.
    Performs a broad match on Project Title, Client Name, Site Street, or Job Prefix.
    
    Args:
        query: Search term
        company_id: Company document ID
        
    Returns:
        List of matching job summaries
    """
    if not db:
        print("⚠️  Firebase not initialized. Cannot perform real search.")
        return []
    
    try:
        jobs_ref = db.collection("companies").document(company_id).collection("jobs")
        
        # For production with thousands of jobs, use Algolia or ElasticSearch
        # For this demo, fetching recent jobs and filtering in memory
        docs = jobs_ref.order_by(
            "createdDate",
            direction=firestore.Query.DESCENDING
        ).limit(50).stream()
        
        search_str = query.lower().strip()
        results = []
        
        for doc in docs:
            data = doc.to_dict()
            job_summary = {
                "documentId": doc.id,
                "projectTitle": data.get("projectTitle", "Untitled"),
                "clientName": data.get("clientName", ""),
                "siteStreet": data.get("siteStreet", ""),
                "siteCity": data.get("siteCity", ""),
                "jobPrefix": data.get("jobPrefix", ""),
                "status": data.get("status", "")
            }
            
            # Filter based on search query
            if (search_str in job_summary["projectTitle"].lower() or
                search_str in job_summary["clientName"].lower() or
                search_str in job_summary["siteStreet"].lower() or
                search_str in job_summary["jobPrefix"].lower()):
                results.append(job_summary)
        
        return results
    
    except Exception as e:
        print(f"❌ Error searching jobs: {e}")
        return []


async def fetch_job_data(
    company_id: str = DEFAULT_COMPANY_ID,
    job_id: str = DEFAULT_JOB_ID
) -> Dict[str, Any]:
    """
    Fetch the full job document from Firestore.
    Includes enhanced parsing for schedule, dependencies, and payment stages.
    
    Args:
        company_id: Company document ID
        job_id: Job document ID
        
    Returns:
        Complete job data dictionary
    """
    # Fallback to mock if DB not initialized
    if not db:
        print("⚠️  Returning Mock Data (Firebase not initialized)")
        return MOCK_JOB_DATA
    
    try:
        print(f"📥 Fetching job: companies/{company_id}/jobs/{job_id}")
        
        doc_ref = db.collection("companies").document(company_id).collection("jobs").document(job_id)
        doc = doc_ref.get()
        
        if doc.exists:
            raw_data = doc.to_dict()
            
            # Parse locations if not string
            locations = raw_data.get("locations")
            if not isinstance(locations, str):
                locations = json.dumps(locations) if locations else "[]"
            
            # Convert basic timestamps
            processed_data = convert_timestamps(raw_data)
            
            # Parse schedule with enhanced handling
            schedule = []
            raw_schedule = processed_data.get("schedule", [])
            if isinstance(raw_schedule, list):
                for task in raw_schedule:
                    if isinstance(task, dict):
                        schedule.append(parse_schedule_row(task))
            
            # Parse estimate
            estimate = processed_data.get("estimate", [])
            if not isinstance(estimate, list):
                estimate = []
            
            # Parse milestones
            milestones = processed_data.get("milestones", [])
            if not isinstance(milestones, list):
                milestones = []
            
            # Parse cost codes (note: Firestore might use lowercase)
            cost_codes = processed_data.get("costCodes", processed_data.get("costcodes", []))
            if not isinstance(cost_codes, list):
                cost_codes = []
            
            # Construct the Job object
            job = {
                "documentId": doc.id,
                **processed_data,
                "locations": locations,
                "estimate": estimate,
                "milestones": milestones,
                "schedule": schedule,
                "costCodes": cost_codes,
                "flooringEstimateData": processed_data.get("flooringEstimateData", []),
            }
            
            return job
        else:
            print("❌ No such job document!")
            raise Exception("Job not found")
    
    except Exception as e:
        print(f"❌ Error fetching job data: {e}")
        # Fallback to mock on error
        return MOCK_JOB_DATA


async def get_task_by_id(
    company_id: str,
    job_id: str,
    task_id: str
) -> Optional[Dict[str, Any]]:
    """
    Helper function to get a specific task by its static ID.
    
    Args:
        company_id: Company document ID
        job_id: Job document ID
        task_id: Task static ID
        
    Returns:
        Task dictionary or None if not found
    """
    job_data = await fetch_job_data(company_id, job_id)
    schedule = job_data.get("schedule", [])
    
    for task in schedule:
        if task.get("id") == task_id:
            return task
    
    return None


async def get_subtasks_for_main_task(
    company_id: str,
    job_id: str,
    main_task_id: str
) -> List[Dict[str, Any]]:
    """
    Helper function to get all subtasks for a main task.
    
    Args:
        company_id: Company document ID
        job_id: Job document ID
        main_task_id: Main task static ID
        
    Returns:
        List of subtask dictionaries
    """
    job_data = await fetch_job_data(company_id, job_id)
    schedule = job_data.get("schedule", [])
    
    # Find main task first
    main_task = None
    for task in schedule:
        if task.get("id") == main_task_id:
            main_task = task
            break
    
    if not main_task:
        return []
    
    # Get subtask IDs
    subtask_ids = main_task.get("subtaskIds", [])
    subtask_indices = main_task.get("subtaskIndices", [])
    
    # Find matching subtasks
    subtasks = []
    for task in schedule:
        if task.get("id") in subtask_ids:
            subtasks.append(task)
        elif task.get("index") in subtask_indices:
            subtasks.append(task)
        elif task.get("mainTaskId") == main_task_id:
            subtasks.append(task)
    
    return subtasks


def get_company_id() -> str:
    """Get the current company ID (for use in tools)."""
    return DEFAULT_COMPANY_ID