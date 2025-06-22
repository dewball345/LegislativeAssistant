from typing import Annotated, Callable, TypeVar, Generic
from typing_extensions import TypedDict
from langchain_core.pydantic_v1 import BaseModel, Field
import requests
import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_tavily import TavilySearch
from dotenv import load_dotenv

from agent.types import AlignmentRecords, BeneficiaryRecords, BillCost, ChangeRecords, PorkRecords, TrojanHorseRecords
from agent.prompts import (
    BILL_SUMMARY_PROMPTS,
    REPRESENTATIVE_PROFILE_PROMPT,
    AMENDMENT_ANALYSIS_PROMPT,
    MEDIA_ANALYSIS_PROMPTS,
    PORK_BARREL_PROMPT,
    TROJAN_HORSE_PROMPT,
    SLEEPER_PROVISION_PROMPT,
    BENEFICIARY_ANALYSIS_PROMPT,
    USER_ALIGNMENT_PROMPTS
)

# Configuration

'''
TODOS:
- try out claude and see performance
- refine prompts to ensure better alignment because seems little overlappy
- create MCP/FastAPI server
-----------conversion to JSON
- create frontend ui
-----------utilize localstorage, spoof auth
-----------cache few json values of nice bills for demo

can manage order how you like
'''

USE_CLAUDE = False  # Set to False to use Gemini
ENABLE_CHUNKING = True  # Set to False to process full text without chunking
MAX_CORRECTION_ATTEMPTS = 3  # Maximum number of times alignment can be corrected
ENABLE_INVESTIGATION_CORRECTION = False #True  # Enable/disable investigation correction workflow
ENABLE_ALIGNMENT_CORRECTION = False #True  # Enable/disable alignment correction workflow

def split_bill_text(text: str) -> list[Document]:
    """Split bill text into chunks using LangChain's text splitter."""
    if not ENABLE_CHUNKING:
        return [Document(page_content=text)]
    
    # large chunk size for claude
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=50000, # Average words per chunk
        chunk_overlap=200, # Words of overlap
        length_function=lambda x: len(x.split()), # Count words instead of chars
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.create_documents([text])

### Helpers ###
class BillHelper:
    def __init__(self, congress_num, bill_type, bill_number):
        self.congress_num = congress_num
        self.bill_type = bill_type
        self.bill_number = bill_number

    def bill_api_call(self, suffix="/text"):
        api_key = "gL8knMuwndZ6omgUPhecOBXcIPFgVrwnGjhV8XMK"
        base_url = "https://api.congress.gov/v3"
        url = f"{base_url}/bill/{self.congress_num}/{self.bill_type}/{self.bill_number}{suffix}?api_key={api_key}"

        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            return None

    def get_bill_sponsors(self):
        res = self.bill_api_call("/")

        # print(json.dumps(res, indent=4))

        return res["bill"]["sponsors"]

    # TODO idk if summaries important

    def get_bill_versions(self):
        res_text = self.bill_api_call("/text")

        bill_versions = res_text["textVersions"]

        all_versions = []
        for version in bill_versions:
            text_url = [ty for ty in version["formats"] if ty["type"] == "Formatted XML"][0]

            text_res = requests.get(text_url["url"])
            text_res.raise_for_status()
            all_versions.append(text_res.text)
        
        # TODO verify this is the most recent
        return all_versions[0]
    
    def get_bill_amendments(self):
        res_text = self.bill_api_call("/amendments")

        return res_text["amendments"]



# Agent
load_dotenv()

if USE_CLAUDE:
    llm = init_chat_model("anthropic:claude-3-5-sonnet-latest" if USE_CLAUDE else "gemini-2.0-flash")
else:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        # other params...
    )


class State(TypedDict):
    # Messages and user profile
    messages: Annotated[list, add_messages]
    profile: str = """
        Name: Jane Doe
        Location: Phoenix, Arizona
        Occupation: Small business owner (Local coffee shop)
        Family: Married with 2 children
        Interests: 
        - Small business growth
        - Education funding
        - Healthcare costs
        - Environmental sustainability
    """
    
    # Bill identifiers
    congress_num: str = 119
    bill_type: str = "hr"
    bill_number: str = 3852
    
    # Bill metadata and analysis
    bill_metadata: dict
    bill_status: str
    bill_text: str
    bill_history: list
    sponsors: list
    summaries: dict  # Will contain different levels of summaries
    
    # Analysis results
    media_analysis: list
    pork_barrel_spending: list
    trojan_horses: list
    sleeper_provisions: list
    beneficiaries: dict  # Individuals, corporations, foreign nations
    lobbying_info: dict
    
    # User impact analysis
    user_benefits: list
    user_drawbacks: list
    cost_analysis: dict
    alternatives: list
    
    # Correction tracking - Alignment
    correction_attempts: int  # Track number of alignment correction attempts
    should_revise: bool
    correction_feedback: bool
    
    # Correction tracking - Investigation
    investigation_correction_attempts: int  # Track number of investigation correction attempts
    should_revise_investigation: bool
    investigation_feedback: str


graph_builder = StateGraph(State)

def init_state_agent(state: State):
    """Initialize the state with bill metadata and user profile."""
    bill_helper = BillHelper(state["congress_num"], state["bill_type"], state["bill_number"])
    
    # Get initial bill metadata
    metadata = bill_helper.bill_api_call("/")
    bill_text = bill_helper.get_bill_versions()
    sponsors = bill_helper.get_bill_sponsors()
    amendments = bill_helper.get_bill_amendments()
    
    # Update state with initial data
    return {
        **state,
        "bill_metadata": metadata,
        "bill_text": bill_text,
        "bill_history": amendments,
        "sponsors": sponsors,
        "bill_status": metadata.get("status", {}).get("phase", "Unknown")
    }

def summarizer_agent(state: State):
    """Generate multi-level summaries of the bill and analyze representatives."""
    
    bill_text = state["bill_text"]
    sponsors = state["sponsors"]

    print("SPONSORS")
    print(json.dumps(sponsors, indent=4))

    # Split text for detailed analysis
    text_chunks = split_bill_text(bill_text)
    
    summaries = {}
    # First two prompts use beginning of text
    for prompt in BILL_SUMMARY_PROMPTS[:2]:
        response = llm.invoke([
            prompt,
            {"role": "user", "content": f"Bill text: {bill_text[:10000]}"}
        ])
        summaries[prompt["content"]] = response.content
    
    # Detailed section analysis uses chunks
    section_analyses = []
    for chunk in text_chunks:
        response = llm.invoke([
            BILL_SUMMARY_PROMPTS[2],
            {"role": "user", "content": f"Bill text section: {chunk.page_content}"}
        ])
        section_analyses.append(response.content)
    summaries[BILL_SUMMARY_PROMPTS[2]["content"]] = "\n\n".join(section_analyses)
    
    # Generate profiles for representatives
    rep_profiles = {}
    
    # Initialize Tavily Search Tool
    tavily_search_tool = TavilySearch(
        max_results=5,
        topic="general",
    )
    
    search_agent = create_react_agent(
        llm,
        tools=[tavily_search_tool],
        prompt=REPRESENTATIVE_PROFILE_PROMPT
    )

    for sponsor in sponsors:
        inputs = {
            "messages": [
                {
                    "role": "user", 
                    "content": f"Representative Info: {sponsor}"
                }
            ]
        }
        response = search_agent.invoke(inputs)
        rep_profiles[sponsor['fullName']] = response
    
    return {
        **state,
        "summaries": {
            "levels": summaries,
            "rep_profiles": rep_profiles
        }
    }

def bill_history_checker_agent(state: State):
    """Analyze bill history and changes over time."""
    
    bill_history = state["bill_history"]
    current_text = state["bill_text"]

    llm_struc = llm.with_structured_output(ChangeRecords)
    
    # Analyze each amendment and version
    history_analysis = []
    for amendment in bill_history:
        response = llm_struc.invoke([
            AMENDMENT_ANALYSIS_PROMPT,
            {"role": "user", "content": f"Amendment details: {amendment}"}
        ])
        history_analysis.append({
            "amendment": amendment,
            "analysis": response  # Remove .content since response is already the structured output
        })
    
    return {
        "bill_history_analysis": history_analysis
    }

def search_news_api(query: str) -> list:
    """Search NewsAPI for articles."""
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    if not NEWS_API_KEY:
        return []
    
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "sortBy": "relevancy",
        "language": "en",
        "apiKey": NEWS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("articles", [])
    except Exception as e:
        print(f"NewsAPI error: {e}")
        return []

def search_tavily(query: str) -> list:
    """Search using Tavily's AI-optimized search engine."""
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    if not TAVILY_API_KEY:
        return []
    
    try:
        tavily = TavilySearch(max_results=5, 
                            include_raw_content=True,
                            search_depth="advanced")
        results = tavily.invoke({"query": query})
        return results.get("results", [])
    except Exception as e:
        print(f"Tavily search error: {e}")
        return []

# TODO URGENT verify THIS part is working because seems a little suspicious
# TODO refine media_search_agent with other featuers like refined prompts react_agent etc
def media_search_agent(state: State):
    """Search and analyze media coverage and expert opinions."""
    
    bill_metadata = state["bill_metadata"]
    bill_number = bill_metadata.get("number")
    congress = bill_metadata.get("congress")
    bill_title = bill_metadata.get("title", "")
    
    # Construct search queries
    base_query = f"Bill {bill_number} Congress {congress} {bill_title}"
    
    media_analysis = []
    
    # Search major news outlets via NewsAPI
    news_articles = search_news_api(base_query)
    if news_articles:
        response = llm.invoke([
            MEDIA_ANALYSIS_PROMPTS["news_analysis"],
            {"role": "user", "content": f"Articles: {json.dumps(news_articles[:5])}"}
        ])
        media_analysis.append({
            "source": "major_news_outlets",
            "articles": news_articles,
            "analysis": response  # Remove .content
        })
    
    # Use Tavily for comprehensive search including news and analysis
    tavily_results = search_tavily(base_query)
    if tavily_results:
        response = llm.invoke([
            MEDIA_ANALYSIS_PROMPTS["search_analysis"],
            {"role": "user", "content": f"Search results: {json.dumps(tavily_results)}"}
        ])
        media_analysis.append({
            "source": "tavily",
            "articles": tavily_results,
            "analysis": response.content
        })
        
    # Expert opinions search through Tavily
    expert_query = f"{base_query} analysis expert opinion think tank research institute"
    expert_results = search_tavily(expert_query)
    if expert_results:
        response = llm.invoke([
            MEDIA_ANALYSIS_PROMPTS["expert_analysis"],
            {"role": "user", "content": f"Expert analyses: {json.dumps(expert_results)}"}
        ])
        media_analysis.append({
            "source": "expert_opinions",
            "articles": expert_results,
            "analysis": response.content
        })
    
    # Watchdog and oversight search through Tavily
    watchdog_query = f"{base_query} watchdog oversight accountability GAO CBO analysis report"
    watchdog_results = search_tavily(watchdog_query)
    if watchdog_results:
        response = llm.invoke([
            MEDIA_ANALYSIS_PROMPTS["watchdog_analysis"],
            {"role": "user", "content": f"Watchdog reports: {json.dumps(watchdog_results)}"}
        ])
        media_analysis.append({
            "source": "watchdog_groups",
            "articles": watchdog_results,
            "analysis": response.content
        })
    
    return {
        "media_analysis": media_analysis
    }

# investigative agent tasks
def investigative_agent_subworkflow(state: State):
    """Coordinate investigative analysis of the bill."""
    
    # If there's feedback from correction node, include it in the prompts
    investigation_feedback = state.get("investigation_feedback", "")
    feedback_context = f"\nPrevious feedback: {investigation_feedback}" if investigation_feedback else ""
    
    def check_pork_barrel(chunks: list[Document]) -> list:
        """Identify potential pork-barrel spending and pork_barrel_spending."""
        findings = []
        llm_struc = llm.with_structured_output(PorkRecords)
        for chunk in chunks:
            response = llm_struc.invoke([
                PORK_BARREL_PROMPT,
                {"role": "user", "content": f"{chunk.page_content}{feedback_context}\nImportant: Only include details that are explicitly mentioned in the text with specific evidence."}
            ])
            findings.append(response)
        return findings

    def identify_trojan_horses(chunks: list[Document], original_purpose: str) -> list:
        """Identify provisions unrelated to bill's original purpose."""
        findings = []
        llm_struc = llm.with_structured_output(TrojanHorseRecords)
        for chunk in chunks:
            response = llm_struc.invoke([
                TROJAN_HORSE_PROMPT,
                {"role": "user", "content": f"Original purpose: {original_purpose}\nBill text: {chunk.page_content}{feedback_context}\nImportant: Only include details that are explicitly mentioned in the text with specific evidence."}
            ])
            findings.append(response)
        return findings

    def identify_sleeper_provisions(chunks: list[Document]) -> list:
        """Identify subtle but impactful provisions."""
        findings = []
        llm_struc = llm.with_structured_output(TrojanHorseRecords)
        for chunk in chunks:
            response = llm_struc.invoke([
                SLEEPER_PROVISION_PROMPT,
                {"role": "user", "content": f"{chunk.page_content}{feedback_context}\nImportant: Only include details that are explicitly mentioned in the text with specific evidence."}
            ])
            findings.append(response)
        return findings

    def analyze_beneficiaries(chunks: list[Document]) -> dict:
        """Identify specific beneficiaries and their benefits."""
        findings = []
        llm_struc = llm.with_structured_output(BeneficiaryRecords)
        for chunk in chunks:
            response = llm_struc.invoke([
                BENEFICIARY_ANALYSIS_PROMPT,
                {"role": "user", "content": f"{chunk.page_content}{feedback_context}\nImportant: Only include details that are explicitly mentioned in the text with specific evidence."}
            ])
            findings.append(response)
        return findings

    # Split bill text into chunks
    bill_text = state["bill_text"]
    text_chunks = split_bill_text(bill_text)

    # Get the bill's original purpose from all summaries
    summaries = state.get("summaries", {}).get("levels", {})
    original_purpose = "\n\n".join([summary for summary in summaries.values() if summary])
    
    # Fallback to title if no summaries available
    if not original_purpose:
        original_purpose = state["bill_metadata"].get("title", "")
    
    investigation_results = {
        "pork_barrel_spending": check_pork_barrel(text_chunks),
        "trojan_horses": identify_trojan_horses(text_chunks, original_purpose),
        "sleeper_provisions": identify_sleeper_provisions(text_chunks),
        "beneficiaries": analyze_beneficiaries(text_chunks)
    }
    
    return {
        **state,
        **investigation_results,
        "investigation_feedback": ""  # Clear any previous feedback
    }

def user_alignment_agent(state: State):
    """Analyze bill's impact on the user based on their profile."""
    
    user_profile = state["profile"]
    bill_text = state["bill_text"]
    
    # Split text into chunks for processing
    text_chunks = split_bill_text(bill_text)
    
    # Prepare base bill analysis without full text
    base_bill_analysis = {
        "summaries": state["summaries"],
        "media_analysis": state.get("media_analysis", []),
        "investigation": {
            "pork_barrel_spending": state["pork_barrel_spending"],
            "trojan_horses": state["trojan_horses"],
            "beneficiaries": state["beneficiaries"],
        }
    }
    
    # If there's feedback from correction node, include it in the prompt
    correction_feedback = state.get("correction_feedback", "")
    feedback_context = f"\nPrevious feedback: {correction_feedback}" if correction_feedback else ""
    
    llm_struc = llm.with_structured_output(AlignmentRecords)
    
    # Process each chunk for benefits and drawbacks
    all_benefits = []
    all_drawbacks = []
    for chunk in text_chunks:
        # Create chunk-specific analysis
        chunk_analysis = {
            **base_bill_analysis,
            "text": chunk.page_content
        }
        
        # Analyze benefits for this chunk
        benefits_response = llm_struc.invoke([
            USER_ALIGNMENT_PROMPTS["benefits_analysis"],
            {"role": "user", "content": f"User profile: {user_profile}\nBill analysis: {chunk_analysis}{feedback_context}\nImportant: Only include benefits that are explicitly mentioned or can be directly inferred from this section of the bill text."}
        ])
        if benefits_response:
            all_benefits.append(benefits_response)
            
        # Analyze drawbacks for this chunk
        drawbacks_response = llm_struc.invoke([
            USER_ALIGNMENT_PROMPTS["drawbacks_analysis"],
            {"role": "user", "content": f"User profile: {user_profile}\nBill analysis: {chunk_analysis}{feedback_context}\nImportant: Only include drawbacks that are explicitly mentioned or can be directly inferred from this section of the bill text."}
        ])
        if drawbacks_response:
            all_drawbacks.append(drawbacks_response)
    
    # Analyze costs for the entire bill
    llm_struc_cost = llm.with_structured_output(BillCost)
    full_analysis = {
        **base_bill_analysis,
        "text": bill_text
    }
    cost_analysis_response = llm_struc_cost.invoke([
        USER_ALIGNMENT_PROMPTS["cost_analysis"],
        {"role": "user", "content": f"Bill analysis: {full_analysis}{feedback_context}\nImportant: Only include cost analysis that is explicitly mentioned or can be directly inferred from the bill text."}
    ])

    return {
        **state,
        "user_benefits": all_benefits,
        "user_drawbacks": all_drawbacks,
        "cost_analysis": cost_analysis_response,
        "correction_feedback": ""  # Clear any previous feedback
    }

def correction_alignment_agent(state: State):
    """Validates alignment results against the bill text to detect hallucinations.
    Only triggers revisions for significant issues and clear misinformation."""
    
    current_attempts = state.get("correction_attempts", 0) + 1
    
    bill_text = state["bill_text"]
    user_benefits = state["user_benefits"]
    user_drawbacks = state["user_drawbacks"]
    cost_analysis = state["cost_analysis"]
    
    if current_attempts > MAX_CORRECTION_ATTEMPTS:
        return {
            **state,
            "correction_feedback": "Maximum correction attempts reached. Some claims may still need verification.",
            "should_revise": False,
            "correction_attempts": current_attempts
        }

    def validate_against_text(claims, text_chunks):
        """Helper to validate claims against the source text chunks.
        Focus on identifying clear factual errors and significant misinformation."""
        all_findings = []
        
        llm_response = llm.invoke([{
            "role": "system",
            "content": "Summarize the key factual claims and specific assertions."
        }, {
            "role": "user",
            "content": f"Claims: {claims}"
        }])
        claims_summary = llm_response.content
        
        for chunk in text_chunks:
            llm_response = llm.invoke([{
                "role": "system",
                "content": """You are a fact-checking agent focused on identifying serious factual errors and clear misinformation.
                Only flag issues that:
                1. Directly contradict the source text
                2. Make specific claims with no supporting evidence
                3. Significantly misrepresent numbers, dates, or key facts
                
                Ignore issues that are:
                1. Matters of interpretation or subjective analysis 
                2. Minor wording differences
                3. Reasonable extrapolations from the text
                4. Contextual information that could be from other reliable sources"""
            }, {
                "role": "user",
                "content": f"Claims Summary: {claims_summary}\n\nDetailed Claims: {claims}\n\nSource Text Chunk: {chunk.page_content}\n\nAnalyze this text chunk and list:\n1. MAJOR factual errors or clear misinformation (with specific evidence)\n2. Significant claims that completely lack support in the text\n\nOnly include serious issues that clearly require revision."
            }])
            if llm_response.content.strip():
                all_findings.append(llm_response.content)
        
        if all_findings:
            synthesis_prompt = f"""Review all findings across text chunks and identify only the most serious issues:

Findings from all chunks:
{'\n'.join(all_findings)}

List ONLY clear factual errors and significant misinformation that definitively require revision.
Ignore minor discrepancies, subjective interpretations, or reasonable extrapolations."""
            
            final_response = llm.invoke([{
                "role": "system",
                "content": "Focus only on major issues that clearly require revision. Ignore minor or subjective discrepancies."
            }, {
                "role": "user",
                "content": synthesis_prompt
            }])
            return final_response.content
        return ""
    
    # Split text into chunks for processing
    text_chunks = split_bill_text(bill_text)
    
    # Validate each type of analysis
    benefits_validation = validate_against_text(user_benefits, text_chunks)
    drawbacks_validation = validate_against_text(user_drawbacks, text_chunks)
    cost_validation = validate_against_text(cost_analysis, text_chunks)
    
    # Combine all validation results
    all_validations = [
        ("benefits", benefits_validation),
        ("drawbacks", drawbacks_validation),
        ("costs", cost_validation)
    ]
    
    # Only consider significant issues
    significant_issues = any(
        validation for _, validation in all_validations 
        if validation.strip() and ("clear" in validation.lower() or "significant" in validation.lower())
    )
    
    if significant_issues:
        feedback = f"Major Issues Requiring Revision (Attempt {current_attempts} of {MAX_CORRECTION_ATTEMPTS}):\n"
        for analysis_type, validation in all_validations:
            if validation.strip():
                feedback += f"\n{analysis_type.title()} Critical Issues:\n{validation}\n"
        
        return {
            **state,
            "correction_feedback": feedback,
            "should_revise": True,
            "correction_attempts": current_attempts
        }
    
    return {
        **state,
        "correction_feedback": "",
        "should_revise": False,
        "correction_attempts": current_attempts
    }

def correction_investigative_agent(state: State):
    """Validates investigative findings against the bill text to detect hallucinations.
    Only triggers revisions for significant issues and clear misinformation."""
    
    current_attempts = state.get("investigation_correction_attempts", 0) + 1
    
    bill_text = state["bill_text"]
    pork_barrel_spending = state["pork_barrel_spending"]
    trojan_horses = state["trojan_horses"]
    sleeper_provisions = state["sleeper_provisions"]
    beneficiaries = state["beneficiaries"]
    original_purpose = state.get("summaries", {}).get("levels", {}).get("You are a legislative analyst. Summarize this bill in one sentence.", "")
    
    if current_attempts > MAX_CORRECTION_ATTEMPTS:
        return {
            **state,
            "investigation_feedback": "Maximum correction attempts reached. Some findings may need additional verification.",
            "should_revise_investigation": False,
            "investigation_correction_attempts": current_attempts
        }

    def validate_findings(findings, finding_type: str, text_chunks: list[Document], context: str = ""):
        """Helper to validate investigative findings against the source text chunks.
        Focus on identifying clear factual errors and significant misinformation."""
        all_validations = []
        
        llm_response = llm.invoke([{
            "role": "system",
            "content": f"Summarize the key factual claims and specific assertions from these {finding_type} findings."
        }, {
            "role": "user",
            "content": f"Findings: {findings}"
        }])
        findings_summary = llm_response.content
        
        validation_criteria = {
            "pork_barrel_spending": "Focus on verifying specific spending amounts and clear pork_barrel_spending designations. Ignore interpretative analysis.",
            "trojan_horses": f"Focus on provisions that explicitly and significantly deviate from the stated purpose: {context}",
            "sleeper_provisions": "Focus on provisions with clear textual evidence of hidden significant impact.",
            "beneficiaries": "Focus on explicitly named beneficiaries and clearly defined benefits."
        }.get(finding_type, "")
        
        for chunk in text_chunks:
            llm_response = llm.invoke([{
                "role": "system",
                "content": f"""You are a rigorous fact-checking agent specializing in legislative analysis.
                Focus ONLY on major factual errors and clear misinformation.
                
                {validation_criteria}
                
                Only flag issues that:
                1. Directly contradict the source text
                2. Make specific claims with no supporting evidence
                3. Significantly misrepresent key provisions
                
                Ignore issues that are:
                1. Matters of interpretation or analysis
                2. Minor details or wording differences
                3. Reasonable extrapolations
                4. Contextual information from other sources"""
            }, {
                "role": "user",
                "content": f"""Findings Summary: {findings_summary}

Detailed Findings: {findings}

Bill Text Section: {chunk.page_content}

List ONLY:
1. Major factual errors (with specific evidence)
2. Clear misrepresentations of the text
3. Significant claims that have no support anywhere in the text

Focus only on issues serious enough to require revision."""
            }])
            if llm_response.content.strip():
                all_validations.append(llm_response.content)
        
        # Synthesize findings across all chunks
        if all_validations:
            synthesis_prompt = f"""Review all validations and identify only the most serious issues:

Validations from all chunks:
{'\n'.join(all_validations)}

List ONLY:
1. Critical factual errors that must be corrected
2. Significant misrepresentations of the bill
3. Major claims that have no support anywhere in the text

Ignore minor issues, subjective interpretations, or reasonable extrapolations."""
            
            final_response = llm.invoke([{
                "role": "system",
                "content": f"Focus only on major issues that clearly require revision. Ignore minor or subjective discrepancies."
            }, {
                "role": "user",
                "content": synthesis_prompt
            }])
            return final_response.content
        return ""
    
    text_chunks = split_bill_text(bill_text)
    
    validations = [
        ("pork_barrel_spending", validate_findings(pork_barrel_spending, "pork_barrel_spending", text_chunks)),
        ("trojan_horses", validate_findings(trojan_horses, "trojan_horses", text_chunks, original_purpose)),
        ("sleeper_provisions", validate_findings(sleeper_provisions, "sleeper_provisions", text_chunks)),
        ("beneficiaries", validate_findings(beneficiaries, "beneficiaries", text_chunks))
    ]
    
    # Only consider significant issues
    significant_issues = any(
        validation for _, validation in validations 
        if validation.strip() and ("clear" in validation.lower() or "significant" in validation.lower() or "critical" in validation.lower())
    )
    
    if significant_issues:
        # Create detailed feedback
        feedback = f"Investigation Correction Feedback (Attempt {current_attempts} of {MAX_CORRECTION_ATTEMPTS}):\n"
        for finding_type, validation in validations:
            if validation.strip():
                feedback += f"\n{finding_type.title()} Critical Issues:\n{validation}\n"
        
        return {
            **state,
            "investigation_feedback": feedback,
            "should_revise_investigation": True,
            "investigation_correction_attempts": current_attempts
        }
    
    return {
        **state,
        "investigation_feedback": "",
        "should_revise_investigation": False,
        "investigation_correction_attempts": current_attempts
    }


# Define conditional routing based on correction results
def should_revise_investigation(state):
    """Route to either investigation agent for revision or continue based on correction results."""
    if not ENABLE_INVESTIGATION_CORRECTION:
        return "alignment"
    return "investigation" if state.get("should_revise_investigation", False) and state.get("investigation_correction_attempts", 0) < MAX_CORRECTION_ATTEMPTS else "alignment"

def should_revise(state):
    """Route to either alignment agent for revision or end based on correction results."""
    if not ENABLE_ALIGNMENT_CORRECTION:
        return END
    return "alignment" if state.get("should_revise", False) and state.get("correction_attempts", 0) < MAX_CORRECTION_ATTEMPTS else END

# Set up the workflow graph
graph = (
    graph_builder
    .add_node("init", init_state_agent)
    .add_node("summarizer", summarizer_agent)
    .add_node("history", bill_history_checker_agent)
    .add_node("media", media_search_agent)  # Keep node but don't connect it
    .add_node("investigation", investigative_agent_subworkflow)
    .add_node("correct_investigation", correction_investigative_agent)
    .add_node("alignment", user_alignment_agent)
    .add_node("correct_alignment", correction_alignment_agent)
    
    # Define the workflow - media agent connections removed
    .add_edge("init", "summarizer")
    .add_edge("summarizer", "history")
    .add_edge("history", "investigation")  # Direct connection bypassing media
    .add_edge("investigation", "correct_investigation")
    .add_conditional_edges(
        "correct_investigation",
        should_revise_investigation
    )
    .add_edge("alignment", "correct_alignment")
    .add_conditional_edges(
        "correct_alignment",
        should_revise
    )
    
    .set_entry_point("init")
    .compile()
)



# Example usage
if __name__ == "__main__":
    # Example user profile
    initial_state = {
        "messages": [],
        "profile": """
        Name: Jane Doe
        Location: Phoenix, Arizona
        Occupation: Small business owner (Local coffee shop)
        Family: Married with 2 children
        Interests: 
        - Small business growth
        - Education funding
        - Healthcare costs
        - Environmental sustainability
        """,
        # Bill identifiers
        "congress_num": "119",
        "bill_type": "hr",
        "bill_number": "3852",
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
    result = graph.invoke(initial_state)

    
    print("\n=== Bill Analysis Results ===\n")
    
    print("One-Sentence Summary:")
    print(result["summaries"]["levels"]["You are a legislative analyst. Summarize this bill in one sentence."])
    print("\nDetailed Summary:")
    print(result["summaries"]["levels"]["Summarize this bill in one detailed paragraph."])
    
    print("\nKey Benefits for User:")
    print(result["user_benefits"])
    
    print("\nPotential Drawbacks:")
    print(result["user_drawbacks"])
    
    print("\nCost Analysis:")
    print(result["cost_analysis"])
    
    print("\nInvestigative Findings:")
    print("pork_barrel_spending and Directed Spending:")
    print(result["pork_barrel_spending"] if result["pork_barrel_spending"] else "No pork_barrel_spending found.")
    print("\nTrojan Horse Provisions (Unrelated to Bill's Purpose):")
    print(result["trojan_horses"] if result["trojan_horses"] else "No trojan horse provisions found.")
    print("\nSleeper Provisions (Subtle but Significant):")
    print(result["sleeper_provisions"] if result["sleeper_provisions"] else "No sleeper provisions found.")
    
    print("\nBeneficiaries Analysis:")
    print(result["beneficiaries"] if result["beneficiaries"] else "No specific beneficiaries identified.")
    
    print("\nMedia Coverage Summary:")
    for analysis in result["media_analysis"]:
        print(f"\n{analysis['source'].upper()}:")
        print(analysis['analysis'])





