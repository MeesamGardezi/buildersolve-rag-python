"""
Firebase Firestore service for job data retrieval
"""
import os
import sys
import json
from typing import List, Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import DEFAULT_COMPANY_ID, DEFAULT_JOB_ID, MOCK_JOB_DATA
from models.types import Job


# Initialize Firebase
db = None

try:
    # Check if Firebase is already initialized
    if not firebase_admin._apps:
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
                cred = None
        
        if cred:
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("✅ Firebase initialized successfully")
        
except Exception as e:
    print(f"❌ Error initializing Firebase: {e}")
    print("⚠️  Falling back to Mock Data")


def convert_timestamps(data: Any) -> Any:
    """
    Helper to convert Firestore Timestamp to ISO string
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


async def search_jobs(query: str, company_id: str = DEFAULT_COMPANY_ID) -> List[Dict[str, Any]]:
    """
    Searches for jobs in Firestore matching the query string.
    Performs a broad match on Project Title, Client Name, Site Street, or Job Prefix.
    """
    if not db:
        print("⚠️  Firebase not initialized. Cannot perform real search.")
        return []
    
    try:
        jobs_ref = db.collection("companies").document(company_id).collection("jobs")
        
        # For production with thousands of jobs, use Algolia or ElasticSearch
        # For this demo, fetching recent jobs and filtering in memory
        docs = jobs_ref.order_by("createdDate", direction=firestore.Query.DESCENDING).limit(50).stream()
        
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


async def fetch_job_data(company_id: str = DEFAULT_COMPANY_ID, job_id: str = DEFAULT_JOB_ID) -> Dict[str, Any]:
    """
    Fetches the full job document from Firestore.
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
            
            # Convert timestamps
            processed_data = convert_timestamps(raw_data)
            
            # Construct the Job object
            job = {
                "documentId": doc.id,
                **processed_data,
                "locations": locations,
                "estimate": processed_data.get("estimate", []),
                "milestones": processed_data.get("milestones", []),
                "schedule": processed_data.get("schedule", []),
                "costCodes": processed_data.get("costcodes", []),  # Note: Firestore uses lowercase
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