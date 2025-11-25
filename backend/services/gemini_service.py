"""
Gemini AI service with agentic tool calling
Orchestrates tool execution for the BuilderSolve Agent
"""
import os
import sys
import time
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import DEFAULT_COMPANY_ID, DEFAULT_JOB_ID, GEMINI_MODEL, SYSTEM_INSTRUCTION
from models.chat import ToolExecution, ChatResponse
from services.firebase_service import fetch_job_data, search_jobs
from tools.definitions import ALL_TOOLS
from tools.helpers import match_text
from tools.estimate_tools import execute_calculate_estimate_sum
from tools.schedule_tools import (
    execute_query_schedule,
    execute_get_task_details,
    execute_query_task_hierarchy,
    execute_query_dependencies,
)
from tools.payment_tools import execute_query_payment_schedule
from tools.comparison_tools import (
    execute_get_comparison_data,
    execute_query_comparison_rows,
    execute_get_comparison_summary,
)


# =============================================================================
# GEMINI INITIALIZATION
# =============================================================================

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY environment variable is not set")

genai.configure(api_key=api_key)


# =============================================================================
# TOOL EXECUTION DISPATCHER
# =============================================================================

async def execute_tool(
    tool_name: str,
    args: Dict[str, Any],
    company_id: str,
    job_id: str,
    job_data: Optional[Dict[str, Any]] = None
) -> tuple[Any, Optional[str]]:
    """
    Execute a tool by name and return the result.
    
    Args:
        tool_name: Name of the tool to execute
        args: Tool arguments
        company_id: Current company ID
        job_id: Current job ID
        job_data: Cached job data (optional, will fetch if needed)
        
    Returns:
        Tuple of (result, new_job_id if switched)
    """
    switched_job_id = None
    result = None
    
    # Fetch job data if needed for most tools
    if job_data is None and tool_name not in ["search_jobs", "get_current_job_data", 
                                                "get_comparison_data", "query_comparison_rows", 
                                                "get_comparison_summary"]:
        job_data = await fetch_job_data(company_id, job_id)
    
    # ==========================================================================
    # JOB TOOLS
    # ==========================================================================
    if tool_name == "search_jobs":
        result = await search_jobs(args.get("query", ""), company_id)
    
    elif tool_name == "get_current_job_data":
        new_job_id = args.get("jobId")
        result = await fetch_job_data(company_id, new_job_id)
        switched_job_id = new_job_id
    
    # ==========================================================================
    # ESTIMATE TOOLS
    # ==========================================================================
    elif tool_name == "calculate_estimate_sum":
        if job_data is None:
            job_data = await fetch_job_data(company_id, job_id)
        result = await execute_calculate_estimate_sum(job_data, args)
    
    # ==========================================================================
    # SCHEDULE TOOLS
    # ==========================================================================
    elif tool_name == "query_schedule":
        if job_data is None:
            job_data = await fetch_job_data(company_id, job_id)
        result = await execute_query_schedule(job_data, args)
    
    elif tool_name == "get_task_details":
        if job_data is None:
            job_data = await fetch_job_data(company_id, job_id)
        result = await execute_get_task_details(job_data, args)
    
    elif tool_name == "query_task_hierarchy":
        if job_data is None:
            job_data = await fetch_job_data(company_id, job_id)
        result = await execute_query_task_hierarchy(job_data, args)
    
    elif tool_name == "query_dependencies":
        if job_data is None:
            job_data = await fetch_job_data(company_id, job_id)
        result = await execute_query_dependencies(job_data, args)
    
    # ==========================================================================
    # PAYMENT TOOLS
    # ==========================================================================
    elif tool_name == "query_payment_schedule":
        if job_data is None:
            job_data = await fetch_job_data(company_id, job_id)
        result = await execute_query_payment_schedule(job_data, args)
    
    # ==========================================================================
    # COMPARISON TOOLS
    # ==========================================================================
    elif tool_name == "get_comparison_data":
        result = await execute_get_comparison_data(company_id, job_id, args)
    
    elif tool_name == "query_comparison_rows":
        result = await execute_query_comparison_rows(company_id, job_id, args)
    
    elif tool_name == "get_comparison_summary":
        result = await execute_get_comparison_summary(company_id, job_id, args)
    
    # ==========================================================================
    # LEGACY TOOL (backward compatibility)
    # ==========================================================================
    elif tool_name == "calculate_field_sum":
        if job_data is None:
            job_data = await fetch_job_data(company_id, job_id)
            
        list_name = args.get("listName")
        field_name = args.get("fieldName")
        search_query = args.get("searchQuery", "")
        
        data_list = job_data.get(list_name, [])
        
        if isinstance(data_list, list):
            search_fields = [
                "area", "description", "taskScope", "costCode",
                "notesRemarks", "title", "task", "remarks"
            ]
            
            if search_query and search_query.lower() not in ['all', '*']:
                filtered_list = [
                    item for item in data_list
                    if match_text(item, search_query, search_fields)
                ]
            else:
                filtered_list = data_list
            
            total_sum = 0
            for item in filtered_list:
                value = item.get(field_name, 0)
                try:
                    total_sum += float(value) if value else 0
                except (ValueError, TypeError):
                    pass
            
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
    
    # ==========================================================================
    # UNKNOWN TOOL
    # ==========================================================================
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    
    return result, switched_job_id


# =============================================================================
# MAIN AGENT FUNCTION
# =============================================================================

async def send_message_to_agent(
    message: str,
    history: List[Dict[str, Any]] = None,
    current_job_id: str = DEFAULT_JOB_ID
) -> ChatResponse:
    """
    Main function to handle chat interaction with Gemini agent.
    
    Args:
        message: User message
        history: Conversation history
        current_job_id: Current job context ID
        
    Returns:
        ChatResponse with text, tool executions, and optional job switch
    """
    if history is None:
        history = []
    
    tool_executions: List[ToolExecution] = []
    switched_job_id: Optional[str] = None
    
    # Track the active Job ID during this conversation turn
    active_job_id = current_job_id
    company_id = DEFAULT_COMPANY_ID
    
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
            role = "user" if msg.get("role") == "user" else "model"
            parts = msg.get("parts", [])
            if parts and len(parts) > 0:
                text = parts[0].get("text", "") if isinstance(parts[0], dict) else str(parts[0])
                gemini_history.append({
                    "role": role,
                    "parts": [text]
                })
        
        # Start chat
        chat = model.start_chat(history=gemini_history)
        
        # Send message
        response = chat.send_message(message)
        
        # Handle function calls (tool execution loop)
        MAX_TURNS = 10
        turns = 0
        
        while hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            
            # Check for function calls
            if not hasattr(candidate.content, 'parts'):
                break
            
            function_calls = [
                part.function_call
                for part in candidate.content.parts
                if hasattr(part, 'function_call') and part.function_call.name
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
                
                try:
                    # Execute the tool
                    result, new_job_id = await execute_tool(
                        tool_name=name,
                        args=args,
                        company_id=company_id,
                        job_id=active_job_id
                    )
                    
                    # Update job ID if switched
                    if new_job_id:
                        active_job_id = new_job_id
                        switched_job_id = new_job_id
                    
                except Exception as err:
                    print(f"❌ Tool Error ({name}): {err}")
                    import traceback
                    traceback.print_exc()
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
        final_text = ""
        if hasattr(response, 'text'):
            final_text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate.content, 'parts'):
                for part in candidate.content.parts:
                    if hasattr(part, 'text'):
                        final_text += part.text
        
        if not final_text:
            final_text = "I processed the data but couldn't generate a text response."
        
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
            text=f"I'm sorry, I encountered an error: {str(e)}. Please try again.",
            toolExecutions=tool_executions
        )