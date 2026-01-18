import logging
from typing import Dict, Any, List
from decimal import Decimal
from sqlalchemy.orm import Session
from uuid import UUID

from app.models import Operator, Deal, Principal, DealUnderwriting

logger = logging.getLogger(__name__)

# Constant for placeholder operator when name is missing
UNKNOWN_OPERATOR_NAME = "Unknown Operator"


class AutoPopulationError(Exception):
    """Raised when auto-population fails"""
    pass


def populate_database_from_extraction(
    extracted_data: Dict[str, Any],
    document_id: UUID,
    operator_id: UUID,
    db: Session
) -> Dict[str, Any]:
    """
    Populate database with extracted data from LLM.
    Creates new Deal, Principals, and Underwriting records.

    Args:
        extracted_data: Structured data from LLM extraction
        document_id: ID of source document
        operator_id: ID of confirmed operator (required)
        db: Database session

    Returns:
        Dictionary with IDs of created records:
        {
            "operator_id": UUID,
            "deal_id": UUID,
            "principal_ids": [UUID, ...],
            "underwriting_id": UUID
        }
    """
    try:
        result = {
            "operator_id": operator_id,
            "deal_id": None,
            "principal_ids": [],
            "underwriting_id": None
        }

        # 1. Use the confirmed operator_id (already validated by caller)
        logger.info(f"Creating deal with confirmed operator {operator_id}")

        # 2. Create new deal with extracted data
        deal_data = extracted_data.get("deal", {})
        deal = _create_deal(deal_data, operator_id, db)
        result["deal_id"] = deal.id
        logger.info(f"Deal created: {deal.deal_name} ({deal.id})")

        # 3. Create principals (only if we have an operator to link them to)
        principals_data = extracted_data.get("principals", [])
        if principals_data and operator_id:
            principals = _create_principals(principals_data, operator_id, db)
            result["principal_ids"] = [p.id for p in principals]
            logger.info(f"Created {len(principals)} principal(s)")

        # 4. Create underwriting for the new deal
        underwriting_data = extracted_data.get("underwriting", {})
        if underwriting_data:
            underwriting = _create_underwriting(underwriting_data, deal.id, db)
            result["underwriting_id"] = underwriting.id
            logger.info(f"Underwriting created for deal {deal.id}")

        db.commit()
        logger.info("Database population completed successfully")
        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Auto-population failed: {str(e)}")
        raise AutoPopulationError(f"Failed to populate database: {str(e)}")


def _create_or_update_operator(operator_data: Dict[str, Any], db: Session) -> Operator:
    """
    Create operator or find existing by name.
    """
    operator_name = operator_data.get("name")

    # Check if operator already exists by name
    existing = db.query(Operator).filter(Operator.name == operator_name).first()

    if existing:
        # Update existing operator with new data
        for field, value in operator_data.items():
            if value is not None and hasattr(existing, field):
                setattr(existing, field, value)
        return existing
    else:
        # Create new operator
        operator = Operator(**{k: v for k, v in operator_data.items() if v is not None})
        db.add(operator)
        db.flush()  # Get the ID without committing
        return operator


def _create_deal(deal_data: Dict[str, Any], operator_id: UUID, db: Session) -> Deal:
    """
    Create a new deal with extracted data.
    """
    import uuid

    # Build deal fields from extracted data
    deal_fields = {
        "operator_id": operator_id,
        "deal_name": deal_data.get("deal_name", "Unnamed Deal"),
        "internal_code": deal_data.get("internal_code") or f"AUTO-{uuid.uuid4().hex[:8].upper()}",
        "status": "received"  # New deals start in "received" status
    }

    # Optional fields
    optional_fields = [
        "country", "state", "msa", "submarket", "address_line1", "postal_code",
        "asset_type", "strategy_type", "num_units", "year_built",
        "business_plan_summary", "hold_period_years"
    ]

    for field in optional_fields:
        value = deal_data.get(field)
        if value is not None:
            deal_fields[field] = value

    # Handle building_sf (needs Decimal conversion)
    building_sf = deal_data.get("building_sf")
    if building_sf is not None:
        deal_fields["building_sf"] = Decimal(str(building_sf))

    # Create the deal
    deal = Deal(**deal_fields)
    db.add(deal)
    db.flush()
    return deal


def _create_principals(principals_data: List[Dict[str, Any]], operator_id: UUID, db: Session) -> List[Principal]:
    """
    Create principal records linked to operator.

    Checks for duplicates by name+operator to avoid creating duplicates.
    """
    created_principals = []

    for principal_data in principals_data:
        full_name = principal_data.get("full_name")
        if not full_name:
            continue

        # Check if principal already exists for this operator
        existing = db.query(Principal).filter(
            Principal.operator_id == operator_id,
            Principal.full_name == full_name
        ).first()

        if existing:
            # Update existing principal
            for field, value in principal_data.items():
                if value is not None and hasattr(existing, field) and field != "full_name":
                    setattr(existing, field, value)
            created_principals.append(existing)
        else:
            # Create new principal
            principal = Principal(
                operator_id=operator_id,
                **{k: v for k, v in principal_data.items() if v is not None}
            )
            db.add(principal)
            db.flush()
            created_principals.append(principal)

    return created_principals


def _create_underwriting(underwriting_data: Dict[str, Any], deal_id: UUID, db: Session) -> DealUnderwriting:
    """
    Create underwriting record for a new deal.
    """
    # Prepare data for model
    model_data = {"deal_id": deal_id}

    # Map fields from extraction JSON to model fields
    field_mapping = {
        "total_project_cost": "total_project_cost",
        "land_cost": "land_cost",
        "hard_cost": "hard_cost",
        "soft_cost": "soft_cost",
        "loan_amount": "loan_amount",
        "equity_required": "equity_required",
        "interest_rate": "interest_rate",
        "ltv": "ltv",
        "ltc": "ltc",
        "dscr_at_stabilization": "dscr_at_stabilization",
        "levered_irr": "levered_irr",
        "unlevered_irr": "unlevered_irr",
        "equity_multiple": "equity_multiple",
        "average_cash_on_cash": "avg_cash_on_cash",
        "exit_cap_rate": "exit_cap_rate",
        "yield_on_cost": "yield_on_cost",
        "hold_period_months": "project_duration_years",
    }

    for json_field, model_field in field_mapping.items():
        value = underwriting_data.get(json_field)
        if value is not None:
            # Convert months to years for project_duration_years
            if json_field == "hold_period_months":
                value = Decimal(str(value)) / 12
            else:
                value = Decimal(str(value))
            model_data[model_field] = value

    # Handle details_json
    details_json = underwriting_data.get("details_json", {})
    if details_json:
        model_data["details_json"] = details_json

    # Create new underwriting
    underwriting = DealUnderwriting(**model_data)
    db.add(underwriting)
    db.flush()
    return underwriting
