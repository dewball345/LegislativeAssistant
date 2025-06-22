from fastapi import FastAPI
from typing import Any, Dict
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agent.types import (
    ChangeRecord, PorkRecord, TrojanHorseRecord, BeneficiaryRecord,
    AlignmentRecord, BillCost, Alternative,
    ChangeRecords, PorkRecords, TrojanHorseRecords, BeneficiaryRecords,
    AlignmentRecords
)
from agent import graph
from agent.graph import generate_letter, generate_score

def convert_to_json_serializable(obj: Any) -> Any:
    """Convert a langgraph output to JSON-serializable format."""
    if isinstance(obj, (
        ChangeRecord, PorkRecord, TrojanHorseRecord, BeneficiaryRecord,
        AlignmentRecord, BillCost, Alternative,
        ChangeRecords, PorkRecords, TrojanHorseRecords, BeneficiaryRecords,
        AlignmentRecords
    )):
        return convert_to_json_serializable(obj.model_dump())
    elif isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif hasattr(obj, 'model_dump'):  # For other Pydantic models
        return convert_to_json_serializable(obj.model_dump())
    elif hasattr(obj, '__dict__'):  # For other custom class instances
        return convert_to_json_serializable(obj.__dict__)
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        return str(obj)  # Fallback for other types

class WorkflowRequest(BaseModel):
    profile: str
    congress_num: int
    type: str
    bill_num: int

class LetterRequest(BaseModel):
    preferences: str
    bill_context: str

class ScoreRequest(BaseModel):
    preferences: str
    bill_context: str

app = FastAPI(
    title="API Server",
    description="FastAPI server for handling API requests",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Welcome to the API Server"}

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}

@app.post("/call_workflow")
async def call_workflow(request: WorkflowRequest) -> Dict[str, Any]:
    a_graph = graph
    # Example user profile
    initial_state = {
        "messages": [],
        "profile": f"""
        {request.profile}
        """,
        # Bill identifiers
        "congress_num": str(request.congress_num),
        "bill_type": str(request.type),
        "bill_number": str(request.bill_num),
        # Initialize other fields as empty
        "bill_metadata": {},
        "bill_status": "",
        "bill_text": "",
        "bill_history": [],
        "sponsors": [],
        "summaries": {},
        "media_analysis": [],  # Initialize with empty list even when media agent is disabled
        "pork_barrel_spending": [],
        "trojan_horses": [],
        "sleeper_provisions": [],
        "beneficiaries": {},
        "lobbying_info": {},
        "user_benefits": [],
        "user_drawbacks": [],
        "cost_analysis": {},
        "alternatives": [],
        # Initialize correction tracking
        "correction_attempts": 0,
        "correction_feedback": "",
        "should_revise": False,
        "investigation_correction_attempts": 0,
        "investigation_feedback": "",
        "should_revise_investigation": False
    }

    # Run the analysis workflow
    result = a_graph.invoke(initial_state)
    
    # Convert the result to JSON-serializable format
    print(result)
    json_result = convert_to_json_serializable(result)
    
    return {
        "status": "success",
        "result": json_result
    }

@app.post("/write_letter")
async def write_letter(request: LetterRequest) -> Dict[str, Any]:
    try:
        letter = generate_letter(request.preferences, request.bill_context)
        return {
            "status": "success",
            "letter": letter
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/generate_score")
async def generate_bill_score(request: ScoreRequest) -> Dict[str, Any]:
    """Generate impact scores for a bill based on preferences and context."""
    print("HIIIIIIII update")
    
    scores = generate_score(request.preferences, request.bill_context)
    print(scores)
    return {
        "status": "success",
        "scores": scores
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
