from typing import Literal, List
from langchain_core.pydantic_v1 import BaseModel, Field

SEVERITY_GUIDELINES = """
SEVERITY SCALE — rate each provision by its overall level of risk, controversy, and misalignment with the bill’s stated purpose, **plus** how well it aligns with or harms the user’s stated background, values, and priorities.  
Consider: transparency, fairness, scope, precedent, fiscal exposure, and direct or indirect impact on the user, their family, and community.

LOW — Routine, clearly germane, aligned or neutral to user values  
• Squarely fits the bill’s objectives and enjoys broad support.  
• Benefits the public at large or a broad class; poses little or no downside for the user and generally aligns with their values.  
• Fiscal exposure is negligible or modest (< $10 million over the scoring window).  
• Implemented via transparent, competitive, or formula-based mechanisms.  
• Unlikely to trigger litigation, audits, or significant opposition; minimal long-term risk.

MEDIUM — Debatable, mixed or uncertain alignment with user values  
• Noticeable policy, market, or fiscal effect ($10 million – $100 million) **or** shifts authority to a single agency, sector, or region.  
• Creates a carve-out or exemption that may disadvantage competitors, taxpayers, or the user’s community.  
• Alignment with the user’s values is mixed: offers some benefits but also potential conflicts or opportunity costs.  
• Oversight or transparency is partial (directed grant, sole-source award, unclear metrics).  
• May attract watchdog/media scrutiny; impact is significant but confined to a sector, region, or time-bound pilot.

HIGH — Highly problematic, conflicts with core user values  
• Sweeping authority, nationwide precedent, or open-ended fiscal commitment (> $100 million or indefinite mandatory spending) with limited oversight.  
• Clearly misaligned with the bill’s purpose or inserted without full debate (“rider”).  
• Favors a single entity or very small group at broad public cost, removes safeguards, or limits future accountability.  
• Directly undermines the user’s stated values or imposes substantial costs, reduced services, or diminished rights on the user, their family, or community.  
• Likely to provoke major political, legal, or public backlash and create long-term structural or reputational risks.

If a provision does not clearly meet Medium or High criteria, classify it as LOW.
"""


class ChangeRecord(BaseModel):
    """A model for representing change records with title, explanation, concern, and severity."""
    title: str = Field(description="Summarized title of change")
    explanation: str = Field(description="Detailed explanation of the change")
    concern: str = Field(description="Why the change is concerning")
    severity: Literal["low", "medium", "high"] = Field(description=SEVERITY_GUIDELINES)

class PorkRecord(BaseModel):
    """A model for representing pork records."""
    title: str = Field(description="Summarized title of pork barrel spending")
    explanation: str = Field(description="Explanation of pork barrel spending")
    concern: str = Field(description="Why pork barrel is concerning")
    severity: Literal["low", "medium", "high"] = Field(description=SEVERITY_GUIDELINES)
    why: str = Field(description="Explain WHY this is pork barrel spending. do not call things pork barrel spending if they are not actually pork barrel spending")


class TrojanHorseRecord(BaseModel):
    """A model for representing trojan horse records."""
    title: str = Field(description="Summarized title of trojan horse or sleeper provision")
    explanation: str = Field(description="Explanation of trojan horse or sleeper provision")
    concern: str = Field(description="Why trojan horse or sleeper provision is concerning")
    severity: Literal["low", "medium", "high"] = Field(description=SEVERITY_GUIDELINES)
    why: str = Field(description="Explain WHY this is a trojan horse  or sleeper provision. do not call things trojan horses or sleeper provisions if they are not actually trojan horses or sleeper provisions")

class BeneficiaryRecord(BaseModel):
    """A model for representing beneficiary records."""
    name: str = Field(description="Beneficiary name")
    benefit: str = Field(description="How bill benefits beneficiary")
    severity: Literal["low", "medium", "high"] = Field(description=SEVERITY_GUIDELINES)

class AlignmentRecord(BaseModel):
    """A model for representing alignment analysis records."""
    benefit_or_harm: Literal["benefit", "harm"] = Field(description="Whether this is a benefit or harm")
    effect_type: Literal["me", "family", "community"] = Field(description="Type of effect")
    summary: str = Field(description="Summary of why")
    explanation: str = Field(description="Detailed explanation of why")
    severity: Literal["low", "medium", "high"] = Field(description=SEVERITY_GUIDELINES)

class Alternative(BaseModel):
    """A model for representing cost alternatives."""
    alternative: str = Field(description="Description of the alternative")
    explanation: str = Field(description="Explanation of the alternative")

class BillCost(BaseModel):
    """A model for representing bill cost analysis."""
    cost_explanation: str = Field(description="Explanation of the cost")
    alternatives: List[Alternative] = Field(description="List of alternative approaches")

# Container classes for list outputs
class ChangeRecords(BaseModel):
    """Container for a list of change records."""
    records: List[ChangeRecord] = Field(description="List of change records")

class PorkRecords(BaseModel):
    """Container for a list of earmark records."""
    records: List[PorkRecord] = Field(description="List of pork records")

class TrojanHorseRecords(BaseModel):
    """Container for a list of trojan horse records."""
    records: List[TrojanHorseRecord] = Field(description="List of trojan horse or sleeper provision records")

class BeneficiaryRecords(BaseModel):
    """Container for a list of beneficiary records."""
    records: List[BeneficiaryRecord] = Field(description="List of beneficiary records")

class AlignmentRecords(BaseModel):
    """Container for a list of alignment records."""
    records: List[AlignmentRecord] = Field(description="List of alignment records")