"""
Gemini AI service with agentic tool calling
"""
import os
import sys
import time
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import DEFAULT_COMPANY_ID, DEFAULT_JOB_ID, GEMINI_MODEL, SYSTEM_INSTRUCTION
from models.types import ToolExecution, ChatResponse
from services.firebase_service import fetch_job_data, search_jobs


# Initialize Gemini
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY environment variable is not set")

genai.configure(api_key=api_key)


# Define the Tools using proper Google AI SDK format
get_job_data_tool = {
    "function_declarations": [{
        "name": "get_current_job_data",
        "description": "Retrieves the full details, estimates, schedule, and milestones for a specific construction job. Use this to load a job context.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "jobId": {
                    "type": "STRING",
                    "description": "The specific document ID of the job to fetch."
                }
            },
            "required": ["jobId"]
        }
    }]
}

search_jobs_tool = {
    "function_declarations": [{
        "name": "search_jobs",
        "description": "Searches for construction jobs in the database by name, client, address, or ID. Use this when the user mentions a new job or wants to switch projects.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The search term (e.g. 'Smith', 'Hammond', 'Kitchen Remodel')."
                }
            },
            "required": ["query"]
        }
    }]
}

calculate_tool = {
    "function_declarations": [{
        "name": "calculate_field_sum",
        "description": "Calculates the sum of a numeric field within a list, with 'Smart Search' filtering. Use this for questions like 'How much is the Kitchen?', 'Total hours for plumbing', or 'Total duration of framing'.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "listName": {
                    "type": "STRING",
                    "description": "The name of the list to iterate over. Options: 'estimate', 'schedule', 'milestones', 'flooringEstimateData'."
                },
                "fieldName": {
                    "type": "STRING",
                    "description": "The numeric field key to sum up. CRITICAL: Use 'total' for Estimates/Prices. Use 'budgetedTotal' for Internal Budgets/Costs. Use 'hours', 'duration', 'amount' for others."
                },
                "searchQuery": {
                    "type": "STRING",
                    "description": "The text to filter by. The tool will search across description, area, task name, and remarks. E.g., 'Kitchen', 'Demolition'."
                }
            },
            "required": ["listName", "fieldName"]
        }
    }]
}

# Combine all tools
ALL_TOOLS = {
    "function_declarations": [
        get_job_data_tool["function_declarations"][0],
        search_jobs_tool["function_declarations"][0],
        calculate_tool["function_declarations"][0]
    ]
}


def match_item(item: Dict[str, Any], search_query: str) -> bool:
    """
    Helper: Smart Matcher for Item Context
    """
    if not search_query:
        return True
    
    query = str(search_query).lower().strip()
    if query in ['all', '*']:
        return True
    
    # Collect all searchable fields
    context_parts = [
        item.get('area'),
        item.get('description'),
        item.get('taskScope'),
        item.get('costCode'),
        item.get('notesRemarks'),
        item.get('title'),
        item.get('task'),
        item.get('remarks'),
        item.get('itemMaterialName'),
        item.get('vendor'),
        item.get('rowType')
    ]
    
    # Build context string
    raw_context = ' '.join(
        str(part).lower() for part in context_parts 
        if part and isinstance(part, (str, int, float))
    )
    
    # Simple substring match
    if query in raw_context:
        return True
    
    # Token-based match (all query tokens must be present)
    query_tokens = [t for t in query.split() if len(t) > 0]
    if not query_tokens:
        return False
    
    has_all_tokens = all(token in raw_context for token in query_tokens)
    return has_all_tokens


async def send_message_to_agent(
    message: str,
    history: List[Dict[str, Any]] = None,
    current_job_id: str = DEFAULT_JOB_ID
) -> ChatResponse:
    """
    Main function to handle chat interaction with Gemini agent
    """
    if history is None:
        history = []
    
    tool_executions: List[ToolExecution] = []
    switched_job_id: Optional[str] = None
    
    # Track the active Job ID during this conversation turn
    active_job_id_for_turn = current_job_id
    
    try:
        # Create model with tools
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            tools=[ALL_TOOLS],
            system_instruction=SYSTEM_INSTRUCTION
        )
        
        # Convert history to Gemini format
        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({
                "role": role,
                "parts": [msg["parts"][0]["text"]]
            })
        
        # Start chat
        chat = model.start_chat(history=gemini_history)
        
        # Send message
        response = chat.send_message(message)
        
        # Handle function calls (tool execution loop)
        MAX_TURNS = 5
        turns = 0
        
        while hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            
            # Check for function calls
            if not hasattr(candidate.content, 'parts'):
                break
            
            function_calls = [
                part.function_call 
                for part in candidate.content.parts 
                if hasattr(part, 'function_call')
            ]
            
            if not function_calls or turns >= MAX_TURNS:
                break
            
            turns += 1
            tool_responses = []
            
            for function_call in function_calls:
                name = function_call.name
                args = dict(function_call.args) if function_call.args else {}
                
                # Skip invalid function calls (empty name)
                if not name:
                    print(f"⚠️ [Agent] Skipping invalid function call with empty name")
                    continue
                
                print(f"🔧 [Agent] Calling Tool: {name}", args)
                
                result = None
                
                try:
                    if name == "search_jobs":
                        result = await search_jobs(args.get("query", ""), DEFAULT_COMPANY_ID)
                    
                    elif name == "get_current_job_data":
                        job_id = args.get("jobId")
                        result = await fetch_job_data(DEFAULT_COMPANY_ID, job_id)
                        
                        # Update active job tracker
                        active_job_id_for_turn = job_id
                        switched_job_id = job_id
                    
                    elif name == "calculate_field_sum":
                        # Fetch current job data
                        job_data = await fetch_job_data(DEFAULT_COMPANY_ID, active_job_id_for_turn)
                        list_name = args.get("listName")
                        field_name = args.get("fieldName")
                        search_query = args.get("searchQuery", "")
                        
                        data_list = job_data.get(list_name, [])
                        
                        if isinstance(data_list, list):
                            # Filter items based on search query
                            if search_query:
                                filtered_list = [
                                    item for item in data_list 
                                    if match_item(item, search_query)
                                ]
                            else:
                                filtered_list = data_list
                            
                            # Calculate sum
                            total_sum = 0
                            for item in filtered_list:
                                value = item.get(field_name, 0)
                                try:
                                    total_sum += float(value) if value else 0
                                except (ValueError, TypeError):
                                    pass
                            
                            # Get sample matched items
                            matched_examples = [
                                item.get("description") or item.get("task") or item.get("title")
                                for item in filtered_list[:5]
                            ]
                            
                            result = {
                                "sum": total_sum,
                                "currency": "USD",
                                "itemsCount": len(data_list),
                                "matchesFound": len(filtered_list),
                                "searchQueryUsed": search_query or "ALL",
                                "matchedExamples": matched_examples
                            }
                        else:
                            result = {"error": f"List '{list_name}' not found or is not an array."}
                    
                    else:
                        result = {"error": "Unknown tool"}
                
                except Exception as err:
                    result = {"error": str(err)}
                
                # Store tool execution
                tool_executions.append(ToolExecution(
                    id=str(time.time()),
                    toolName=name,
                    args=args,
                    result=result,
                    timestamp=time.time()
                ))
                
                # Prepare response for Gemini
                tool_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=name,
                            response={"result": result}
                        )
                    )
                )
            
            # Send tool responses back to model
            if tool_responses:
                response = chat.send_message(tool_responses)
        
        # Extract final text response
        final_text = response.text if hasattr(response, 'text') else "I processed the data but couldn't generate a text response."
        
        return ChatResponse(
            text=final_text,
            toolExecutions=tool_executions,
            switchedJobId=switched_job_id
        )
    
    except Exception as e:
        print(f"❌ Agent Error: {e}")
        import traceback
        traceback.print_exc()
        return ChatResponse(
            text="I'm sorry, I encountered an error. Please try again.",
            toolExecutions=tool_executions
        )