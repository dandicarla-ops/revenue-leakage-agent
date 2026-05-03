"""
Claude Analyzer - Intelligent analysis of billing discrepancies.
Uses Claude API to determine root cause, severity, and recommended actions.
Usage: from src.tools.claude_analyzer import analyze_discrepancy
"""

import os
import json
from dotenv import load_dotenv
import anthropic

# Load environment variables
load_dotenv()

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Merchant industry context (helps Claude with seasonality detection)
MERCHANT_INDUSTRY_CONTEXT = {
    "M001": {"name": "TechFlow Inc.", "industry": "SaaS", "mmc": 50000, "currency": "USD"},
    "M002": {"name": "RetailKing Ltd.", "industry": "E-commerce", "mmc": 30000, "currency": "USD"},
    "M003": {"name": "AlpineResort Booking", "industry": "Travel/Hospitality", "mmc": 20000, "currency": "USD"},
    "M004": {"name": "CloudServices Corp.", "industry": "Cloud Infrastructure", "mmc": 75000, "currency": "USD"},
    "M005": {"name": "VolumeTrading Pro", "industry": "Financial/Crypto", "mmc": 100000, "currency": "USD"},
}

# Month names for readability
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

class DiscrepancyAnalysis:
    """Represents Claude's analysis of a billing discrepancy."""

    def __init__(self, merchant_id, merchant_name, month, shortfall,
                 root_cause, pattern, severity, recommended_action,
                 confidence, reasoning, asc606_flag=False):
        self.merchant_id = merchant_id
        self.merchant_name = merchant_name
        self.month = month
        self.shortfall = shortfall
        self.root_cause = root_cause
        self.pattern = pattern
        self.severity = severity
        self.recommended_action = recommended_action
        self.confidence = confidence
        self.reasoning = reasoning
        self.asc606_flag = asc606_flag

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "month": self.month,
            "shortfall": self.shortfall,
            "root_cause": self.root_cause,
            "pattern": self.pattern,
            "severity": self.severity,
            "recommended_action": self.recommended_action,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "asc606_flag": self.asc606_flag
        }

    def __str__(self):
        month_name = MONTH_NAMES.get(int(self.month), str(self.month))
        return (
            f"\n{'=' * 60}\n"
            f"  ANALYSIS: {self.merchant_name} ({self.merchant_id})\n"
            f"{'=' * 60}\n"
            f"  Month:              {month_name}\n"
            f"  Shortfall:          ${self.shortfall:,.2f}\n"
            f"  Root Cause:         {self.root_cause}\n"
            f"  Pattern:            {self.pattern}\n"
            f"  Severity:           {self.severity}\n"
            f"  Recommended Action: {self.recommended_action}\n"
            f"  Confidence:         {self.confidence}\n"
            f"  ASC 606 Flag:       {'⚠️  Possible timing issue' if self.asc606_flag else '✅ Not flagged'}\n"
            f"  Reasoning:          {self.reasoning}\n"
        )


def build_analysis_prompt(discrepancies, merchant_context):
    """
    Build a structured prompt for Claude to analyze discrepancies.

    Args:
        discrepancies (list): List of Discrepancy objects
        merchant_context (dict): Merchant industry context

    Returns:
        str: Formatted prompt for Claude
    """

    industry = merchant_context.get("industry", "Unknown")
    mmc = merchant_context.get("mmc", 0)
    currency = merchant_context.get("currency", "USD")
    merchant_name = merchant_context.get("name", "Unknown")

# Format discrepancy details (skip rows with NaN month)
    discrepancy_details = []
    for d in discrepancies:
        try:
            if d.month != d.month:  # NaN check (NaN != NaN is always True)
                continue
            month_name = MONTH_NAMES.get(int(d.month), str(d.month))
            discrepancy_details.append(
                f"  - {month_name}: Expected {currency} {d.expected:,.0f}, "
                f"Actual {currency} {d.actual:,.0f}, "
                f"Shortfall {currency} {d.shortfall:,.0f} ({d.percentage_shortfall:.1f}%)"
            )
        except (ValueError, TypeError):
            continue

    discrepancy_text = "\n".join(discrepancy_details)

    prompt = f"""You are a Senior Finance Analyst specializing in revenue leakage detection for payment processors and fintech companies.

Analyze the following billing discrepancies and provide a structured assessment.

MERCHANT PROFILE:
- Merchant Name: {merchant_name}
- Industry: {industry}
- Monthly Minimum Commitment (MMC): {currency} {mmc:,.0f}
- Currency: {currency}

MATERIAL DISCREPANCIES (>10% shortfall):
{discrepancy_text}

ANALYSIS INSTRUCTIONS:
For each discrepancy, determine:

1. ROOT CAUSE - Choose the most likely cause:
   - "Ramp-up": New merchant still growing into their MMC
   - "Seasonal variance": Expected lower billing due to industry seasonality
   - "Genuine leakage": Systematic underbilling error requiring immediate action
   - "Data error": Likely billing system or data quality issue
   - "Contract amendment": Possible mid-year contract changes

2. PATTERN - Identify the trend:
   - "Single month anomaly": One-off spike or dip
   - "Recurring monthly": Consistent underbilling across months
   - "Seasonal cycle": Higher/lower billing tied to specific seasons
   - "Trending downward": Getting progressively worse
   - "Trending upward": Improving over time (e.g. ramp-up)

3. SEVERITY - Assess urgency:
   - "Critical": Recurring leakage, large absolute shortfall (>$50k)
   - "High": Material gap not explained by seasonality or ramp-up
   - "Medium": Seasonal variance or data quality issue
   - "Low": Expected ramp-up or minor seasonal pattern

4. RECOMMENDED ACTION - What finance team should do:
   - "Investigate billing system": If data error or genuine leakage suspected
   - "Document seasonal pattern": If seasonality explains the variance
   - "Follow up with merchant/sales/legal": If contract terms need clarification
   - "No action needed": If ramp-up or expected variance

5. CONFIDENCE - How certain are you?
   - "High": Clear pattern, strong evidence
   - "Medium": Likely cause identified, some ambiguity
   - "Low": Ambiguous, needs more data

6. ASC 606 FLAG - Should this be reviewed for revenue timing issues?
   - true: If prepayment, advance payments, or deferred revenue may explain the gap
   - false: If no timing issues suspected

IMPORTANT CONTEXT:
- Travel/Hospitality merchants (like ski resorts, hotels) typically see lower summer billing and higher winter billing
- SaaS merchants typically ramp up over 3-6 months before reaching full MMC
- Crypto/Financial merchants are volatile month-to-month due to market conditions
- E-commerce merchants often see Q4 spikes (Black Friday, Christmas)
- Consistent shortfalls across multiple months are more concerning than single-month dips

Respond ONLY with a valid JSON array. No preamble, no markdown, no explanation outside the JSON.
One object per discrepancy in this exact format:

[
  {{
    "month": <month number as integer>,
    "root_cause": "<root cause>",
    "pattern": "<pattern>",
    "severity": "<severity>",
    "recommended_action": "<recommended action>",
    "confidence": "<confidence level>",
    "asc606_flag": <true or false>,
    "reasoning": "<2-3 sentence explanation of your analysis>"
  }}
]"""

    return prompt


def analyze_discrepancies(discrepancies, merchant_id):
    """
    Send discrepancies to Claude for intelligent analysis.

    Args:
        discrepancies (list): List of material Discrepancy objects
        merchant_id (str): Merchant ID for context lookup

    Returns:
        list: List of DiscrepancyAnalysis objects
    """

    if not discrepancies:
        print("  ⚠️  No discrepancies to analyze")
        return []

    # Get merchant context
    merchant_context = MERCHANT_INDUSTRY_CONTEXT.get(merchant_id, {
        "name": discrepancies[0].merchant_name,
        "industry": "Unknown",
        "mmc": discrepancies[0].expected,
        "currency": "USD"
    })

    print(f"  🤖 Sending {len(discrepancies)} discrepancies to Claude for analysis...")

    # Build prompt
    prompt = build_analysis_prompt(discrepancies, merchant_context)

    try:
        # Call Claude API
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        response_text = response.content[0].text.strip()

        # Clean up any markdown formatting if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        analyses_raw = json.loads(response_text)

        # Map raw analysis back to discrepancy objects
        analyses = []
        for raw in analyses_raw:
            # Find matching discrepancy by month
            matching_disc = next(
                (d for d in discrepancies if int(d.month) == int(raw["month"])),
                None
            )

            if matching_disc and matching_disc.month == matching_disc.month:  # NaN check
                analysis = DiscrepancyAnalysis(
                    merchant_id=merchant_id,
                    merchant_name=matching_disc.merchant_name,
                    month=raw["month"],
                    shortfall=matching_disc.shortfall,
                    root_cause=raw["root_cause"],
                    pattern=raw["pattern"],
                    severity=raw["severity"],
                    recommended_action=raw["recommended_action"],
                    confidence=raw["confidence"],
                    reasoning=raw["reasoning"],
                    asc606_flag=raw.get("asc606_flag", False)
                )
                analyses.append(analysis)

        print(f"  ✅ Claude analyzed {len(analyses)} discrepancies")
        return analyses

    except json.JSONDecodeError as e:
        print(f"  ❌ Failed to parse Claude response as JSON: {e}")
        print(f"  Raw response: {response_text[:200]}...")
        return []
    except Exception as e:
        print(f"  ❌ Claude API error: {e}")
        return []


def save_analyses(analyses, output_folder="output"):
    """
    Save analyses to JSON file.

    Args:
        analyses (list): List of DiscrepancyAnalysis objects
        output_folder (str): Folder to save output
    """
    os.makedirs(output_folder, exist_ok=True)

    output_file = os.path.join(output_folder, "discrepancy_analyses.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([a.to_dict() for a in analyses], f, indent=2, ensure_ascii=False)

    print(f"\n  ✅ Saved analyses to: {output_file}")


if __name__ == "__main__":
    # Test the analyzer using reconciliation engine output
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from src.tools.reconciliation_engine import (
        load_billing_data,
        reconcile_merchant,
        filter_material_discrepancies
    )

    print("=" * 60)
    print("CLAUDE DISCREPANCY ANALYZER TEST")
    print("=" * 60 + "\n")

    try:
        # Step 1: Load billing data
        print("Step 1: Loading billing data...")
        billing_df = load_billing_data("data/sample_billing.csv")

        # Step 2: Reconcile merchant
        print("\nStep 2: Reconciling merchant...")
        merchant_id = "M001"
        merchant_name = "TechFlow Inc."
        min_commitment = 50000

        discrepancies = reconcile_merchant(
            merchant_id, merchant_name, min_commitment, billing_df
        )

        # Step 3: Filter material discrepancies
        material = filter_material_discrepancies(discrepancies, threshold_percentage=10.0)
        print(f"  Found {len(material)} material discrepancies")

        # Step 4: Analyze with Claude
        print("\nStep 3: Analyzing with Claude...")
        analyses = analyze_discrepancies(material, merchant_id)

        # Step 5: Print results
        print("\nStep 4: Analysis Results:")
        for analysis in analyses:
            print(analysis)

        # Step 6: Save to JSON
        save_analyses(analyses)

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
