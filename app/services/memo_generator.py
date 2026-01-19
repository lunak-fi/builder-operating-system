import logging
from typing import Dict, Any
from uuid import UUID
from anthropic import Anthropic
from sqlalchemy.orm import Session

from app.models import Deal, Operator, DealUnderwriting, DealDocument, Memo
from app.services.llm_extractor import LLMSettings

logger = logging.getLogger(__name__)


class MemoGenerationError(Exception):
    """Raised when memo generation fails"""
    pass


def generate_memo_for_deal(deal_id: UUID, db: Session) -> Memo:
    """
    Generate AI-powered memo with 3 sections:
    - Investment Thesis (refined from business_plan_summary)
    - Key Risks (based on financials, strategy, missing data)
    - Open Questions (smart due diligence questions)

    Args:
        deal_id: UUID of the deal to generate memo for
        db: Database session

    Returns:
        Memo object stored in database

    Raises:
        MemoGenerationError: If generation fails
    """
    try:
        # Fetch deal with related data
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise MemoGenerationError(f"Deal {deal_id} not found")

        # Fetch related data
        operator = db.query(Operator).filter(Operator.id == deal.operator_id).first()
        underwriting = db.query(DealUnderwriting).filter(DealUnderwriting.deal_id == deal_id).first()
        documents = db.query(DealDocument).filter(DealDocument.deal_id == deal_id).order_by(
            DealDocument.created_at.desc()
        ).all()

        # Build context for AI generation
        context = _build_deal_context(deal, operator, underwriting, documents)

        # Get latest document text for additional context
        document_text = ""
        if documents and documents[0].parsed_text:
            # Use first 10k characters of latest document
            document_text = documents[0].parsed_text[:10000]

        # Generate memo content using Claude API
        logger.info(f"Generating memo for deal {deal_id} (status: {deal.status})")
        memo_markdown = _generate_memo_content(context, document_text, deal.status)

        # Delete existing memo if any
        db.query(Memo).filter(Memo.deal_id == deal_id).delete()
        db.commit()

        # Create and store memo
        memo = Memo(
            deal_id=deal_id,
            title=f"Investment Memo - {deal.deal_name}",
            memo_type="investment_memo",
            content_markdown=memo_markdown,
            generated_by="claude-sonnet-4-20250514"
        )
        db.add(memo)
        db.commit()
        db.refresh(memo)

        logger.info(f"Successfully generated memo for deal {deal_id}")
        return memo

    except Exception as e:
        logger.error(f"Memo generation failed for deal {deal_id}: {str(e)}")
        if isinstance(e, MemoGenerationError):
            raise
        raise MemoGenerationError(f"Unexpected error during memo generation: {str(e)}")


def _build_deal_context(
    deal: Deal,
    operator: Operator | None,
    underwriting: DealUnderwriting | None,
    documents: list[DealDocument]
) -> Dict[str, Any]:
    """Build context dictionary from deal data"""

    # Identify missing critical fields
    missing_fields = []
    if underwriting:
        if not underwriting.hard_cost:
            missing_fields.append("hard_cost")
        if not underwriting.exit_cap_rate:
            missing_fields.append("exit_cap_rate")
        if not underwriting.yield_on_cost:
            missing_fields.append("yield_on_cost")
        if not underwriting.dscr_at_stabilization:
            missing_fields.append("dscr_at_stabilization")

    context = {
        # Deal basics
        "deal_name": deal.deal_name,
        "strategy": deal.strategy_type or "Unknown",
        "asset_type": deal.asset_type or "Unknown",
        "market": f"{deal.msa or deal.submarket or 'Unknown'}, {deal.state or ''}".strip(', '),
        "sponsor_name": operator.name if operator else "Unknown Sponsor",

        # Property details
        "num_units": deal.num_units,
        "building_sf": deal.building_sf,
        "year_built": deal.year_built,
        "address": deal.address_line1,

        # Business plan
        "business_plan": deal.business_plan_summary or "Not provided",
        "hold_period_years": deal.hold_period_years,

        # Financials
        "total_project_cost": underwriting.total_project_cost if underwriting else None,
        "land_cost": underwriting.land_cost if underwriting else None,
        "hard_cost": underwriting.hard_cost if underwriting else None,
        "soft_cost": underwriting.soft_cost if underwriting else None,
        "equity_required": underwriting.equity_required if underwriting else None,
        "loan_amount": underwriting.loan_amount if underwriting else None,
        "ltv": underwriting.ltv if underwriting else None,
        "ltc": underwriting.ltc if underwriting else None,
        "levered_irr": underwriting.levered_irr if underwriting else None,
        "equity_multiple": underwriting.equity_multiple if underwriting else None,
        "exit_cap_rate": underwriting.exit_cap_rate if underwriting else None,
        "dscr_at_stabilization": underwriting.dscr_at_stabilization if underwriting else None,

        # Missing fields
        "missing_fields": missing_fields,

        # Document count
        "document_count": len(documents)
    }

    return context


def _generate_memo_content(context: Dict[str, Any], document_text: str, deal_status: str) -> str:
    """Call Claude API to generate memo content"""

    # Build the prompt
    prompt = _build_memo_prompt(context, document_text, deal_status)

    # Initialize Claude client
    settings = LLMSettings()
    client = Anthropic(
        api_key=settings.anthropic_api_key,
        max_retries=2
    )

    logger.info("Sending memo generation request to Claude API")

    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.3,  # Slightly creative for risk/question generation
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    # Extract response
    response_text = message.content[0].text
    logger.info(f"Received memo from Claude API ({len(response_text)} chars)")

    return response_text


def _build_memo_prompt(context: Dict[str, Any], document_text: str, deal_status: str) -> str:
    """Build the prompt for Claude to generate the memo"""

    # Format currency values
    def fmt_currency(val):
        if val is None:
            return "Not provided"
        if val >= 1_000_000:
            return f"${val/1_000_000:.1f}M"
        if val >= 1_000:
            return f"${val/1_000:.0f}K"
        return f"${val:,.0f}"

    # Format percentage values
    def fmt_pct(val):
        if val is None:
            return "Not provided"
        return f"{val * 100:.1f}%"

    # Format multiplier values
    def fmt_mult(val):
        if val is None:
            return "Not provided"
        return f"{val:.2f}x"

    # Check if this is a committed deal (portfolio monitoring mode)
    is_committed = deal_status == "committed"

    if is_committed:
        # Prompt for COMMITTED deals - portfolio monitoring focus
        prompt = f"""You are an investment analyst generating a portfolio monitoring memo for a COMMITTED commercial real estate deal. This deal is already in the portfolio, so focus on tracking execution and performance rather than evaluating whether to invest.

DEAL INFORMATION:
---
Deal Name: {context['deal_name']}
Strategy: {context['strategy']}
Asset Type: {context['asset_type']}
Market: {context['market']}
Sponsor: {context['sponsor_name']}

Property Details:
- Units: {context['num_units'] or 'Not provided'}
- Square Feet: {context['building_sf'] or 'Not provided'}
- Year Built: {context['year_built'] or 'Not provided'}
- Location: {context['address'] or 'Not provided'}

Business Plan Summary:
{context['business_plan']}

Underwriting Metrics (As Committed):
- Total Project Cost: {fmt_currency(context['total_project_cost'])}
- Land/Acquisition Cost: {fmt_currency(context['land_cost'])}
- Hard Costs: {fmt_currency(context['hard_cost'])}
- Soft Costs: {fmt_currency(context['soft_cost'])}
- Equity Required: {fmt_currency(context['equity_required'])}
- Loan Amount: {fmt_currency(context['loan_amount'])}
- LTV: {fmt_pct(context['ltv'])}
- LTC: {fmt_pct(context['ltc'])}
- Levered IRR (Projected): {fmt_pct(context['levered_irr'])}
- Equity Multiple (Projected): {fmt_mult(context['equity_multiple'])}
- Exit Cap Rate (Assumed): {fmt_pct(context['exit_cap_rate'])}
- DSCR at Stabilization (Projected): {context['dscr_at_stabilization'] or 'Not provided'}
- Hold Period: {context['hold_period_years'] or 'Not provided'} years

LATEST UPDATE DOCUMENT:
{document_text[:10000] if document_text else 'No recent update available'}

---

INSTRUCTIONS:

Generate a portfolio monitoring memo with EXACTLY these three sections:

## Execution Status

Write 3-5 bullet points that summarize WHERE WE ARE in the business plan execution. Focus on:
- Current phase of the project (e.g., construction 60% complete, lease-up phase, stabilized, etc.)
- Key milestones achieved or missed since commitment
- Timeline updates or changes from original plan
- Any budget updates (over/under on costs)
- Reference specific numbers from the latest update when possible

Use markdown bullet points with bold key phrases.

## Current Risks & Concerns

Identify 4-6 ACTIVE risks that matter NOW for this portfolio asset. Consider:
- Execution risks (construction delays, cost overruns, permitting issues)
- Market changes since commitment (demand shifts, competitive supply, rent trends)
- Leasing/occupancy challenges (if applicable)
- Financial performance vs. projections (if operating)
- Sponsor performance issues
- Macroeconomic headwinds affecting this deal

Use markdown bullet points with bold risk categories. Be specific about what's changed or what to monitor.

## Action Items & Follow-Ups

Generate 5-8 SPECIFIC action items and questions to track. Focus on:
- Next milestones to monitor (completion dates, lease-up targets, etc.)
- Updates needed from sponsor (quarterly reports, budget reconciliation, etc.)
- Site visits or calls needed
- Missing data that would help monitoring
- Decisions needed from the investment committee
- Market research to validate performance assumptions

Use markdown bullet points starting with strong verbs (Monitor, Request, Schedule, Review, Track, etc.)

CRITICAL REQUIREMENTS:
1. Return ONLY the markdown content for these three sections - no introduction, no conclusion
2. Start with ## Execution Status as the first line
3. Be SPECIFIC and reference the actual deal data - avoid generic statements
4. Use bullet points (- or *) for all items
5. Use **bold** to highlight key phrases in each bullet
6. Do NOT invent data - only use information provided above
7. Total output should be 400-600 words
8. Remember: this is a COMMITTED deal, so focus on monitoring execution, not evaluating the investment decision

Generate the memo now:"""
    else:
        # Prompt for EARLY-STAGE deals - investment evaluation focus
        prompt = f"""You are an investment analyst generating an investment memo for a commercial real estate deal. Analyze the following deal information and generate a comprehensive memo with three specific sections.

DEAL INFORMATION:
---
Deal Name: {context['deal_name']}
Strategy: {context['strategy']}
Asset Type: {context['asset_type']}
Market: {context['market']}
Sponsor: {context['sponsor_name']}

Property Details:
- Units: {context['num_units'] or 'Not provided'}
- Square Feet: {context['building_sf'] or 'Not provided'}
- Year Built: {context['year_built'] or 'Not provided'}
- Location: {context['address'] or 'Not provided'}

Business Plan Summary:
{context['business_plan']}

Financial Metrics:
- Total Project Cost: {fmt_currency(context['total_project_cost'])}
- Land/Acquisition Cost: {fmt_currency(context['land_cost'])}
- Hard Costs: {fmt_currency(context['hard_cost'])}
- Soft Costs: {fmt_currency(context['soft_cost'])}
- Equity Required: {fmt_currency(context['equity_required'])}
- Loan Amount: {fmt_currency(context['loan_amount'])}
- LTV: {fmt_pct(context['ltv'])}
- LTC: {fmt_pct(context['ltc'])}
- Levered IRR: {fmt_pct(context['levered_irr'])}
- Equity Multiple: {fmt_mult(context['equity_multiple'])}
- Exit Cap Rate: {fmt_pct(context['exit_cap_rate'])}
- DSCR at Stabilization: {context['dscr_at_stabilization'] or 'Not provided'}
- Hold Period: {context['hold_period_years'] or 'Not provided'} years

Missing Data Points: {', '.join(context['missing_fields']) if context['missing_fields'] else 'None'}

DOCUMENT EXCERPT (First 10k chars):
{document_text[:10000] if document_text else 'No document text available'}

---

INSTRUCTIONS:

Generate a professional investment memo with EXACTLY these three sections:

## Investment Thesis

Write 2-4 compelling bullet points that explain the VALUE CREATION strategy. Focus on:
- Specific opportunities for value add (not generic statements)
- Market dynamics that support the thesis
- Sponsor's edge or competitive advantage
- Why THIS deal at THIS time makes sense
- Reference specific numbers from the financials when possible

Use markdown bullet points with bold key phrases.

## Key Risks

Identify 4-6 SPECIFIC risks tied to this deal. Consider:
- Financial risks (leverage, returns sensitivity, exit cap rate assumptions)
- Market risks (supply/demand, rent growth assumptions)
- Execution risks (construction, lease-up, repositioning timeline)
- Sponsor risks (track record, experience in this market/strategy)
- Missing data points that create uncertainty
- Risks specific to the strategy type ({context['strategy']})

Use markdown bullet points with bold risk categories. Be specific and quantitative where possible.

## Open Questions

Generate 5-8 ACTIONABLE due diligence questions that an investor should ask. Focus on:
- Questions about missing data fields: {', '.join(context['missing_fields']) if context['missing_fields'] else 'N/A'}
- Clarifications needed on the business plan
- Market research to validate assumptions
- Sponsor background checks
- Legal/regulatory considerations
- Questions specific to {context['asset_type']} deals in {context['market']}

Use markdown bullet points starting with strong verbs (Verify, Confirm, Review, Investigate, etc.)

CRITICAL REQUIREMENTS:
1. Return ONLY the markdown content for these three sections - no introduction, no conclusion
2. Start with ## Investment Thesis as the first line
3. Be SPECIFIC and reference the actual deal data - avoid generic statements
4. Use bullet points (- or *) for all items
5. Use **bold** to highlight key phrases in each bullet
6. Do NOT invent or hallucinate data - only use information provided above
7. If data is missing, acknowledge it in the Open Questions section
8. Total output should be 400-600 words

Generate the memo now:"""

    return prompt
