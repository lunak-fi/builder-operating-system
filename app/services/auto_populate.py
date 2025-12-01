import logging
from typing import Dict, Any, List
from decimal import Decimal
from sqlalchemy.orm import Session
from uuid import UUID

from app.models import Operator, Deal, Principal, DealUnderwriting

logger = logging.getLogger(__name__)


class AutoPopulationError(Exception):
    """Raised when auto-population fails"""
    pass


def populate_database_from_extraction(
    extracted_data: Dict[str, Any],
    document_id: UUID,
    deal_id: UUID,
    db: Session
) -> Dict[str, Any]:
    """
    Populate database with extracted data from LLM.

    Args:
        extracted_data: Structured data from LLM extraction
        document_id: ID of source document
        deal_id: ID of the deal this document belongs to
        db: Database session

    Returns:
        Dictionary with IDs of created/updated records:
        {
            "operator_id": UUID,
            "deal_id": UUID,
            "principal_ids": [UUID, ...],
            "underwriting_id": UUID
        }
    """
    try:
        result = {
            "operator_id": None,
            "deal_id": deal_id,
            "principal_ids": [],
            "underwriting_id": None
        }

        # 1. Create or update operator
        operator_data = extracted_data.get("operator", {})
        if operator_data and operator_data.get("name"):
            operator = _create_or_update_operator(operator_data, db)
            result["operator_id"] = operator.id
            logger.info(f"Operator processed: {operator.name} ({operator.id})")

            # 2. Update deal with extracted data and link to operator
            deal_data = extracted_data.get("deal", {})
            if deal_data:
                deal = _update_deal(deal_id, deal_data, operator.id, db)
                logger.info(f"Deal updated: {deal.deal_name} ({deal.id})")

            # 3. Create principals linked to operator
            principals_data = extracted_data.get("principals", [])
            if principals_data:
                principals = _create_principals(principals_data, operator.id, db)
                result["principal_ids"] = [p.id for p in principals]
                logger.info(f"Created {len(principals)} principal(s)")

            # 4. Create or update underwriting
            underwriting_data = extracted_data.get("underwriting", {})
            if underwriting_data:
                underwriting = _create_or_update_underwriting(underwriting_data, deal_id, db)
                result["underwriting_id"] = underwriting.id
                logger.info(f"Underwriting created/updated for deal {deal_id}")

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


def _update_deal(deal_id: UUID, deal_data: Dict[str, Any], operator_id: UUID, db: Session) -> Deal:
    """
    Update existing deal with extracted data.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise AutoPopulationError(f"Deal {deal_id} not found")

    # Update operator_id
    deal.operator_id = operator_id

    # Update other fields from extracted data
    field_mapping = {
        "deal_name": "deal_name",
        "internal_code": "internal_code",
        "country": "country",
        "state": "state",
        "msa": "msa",
        "submarket": "submarket",
        "address_line1": "address_line1",
        "postal_code": "postal_code",
        "asset_type": "asset_type",
        "strategy_type": "strategy_type",
        "num_units": "num_units",
        "building_sf": "building_sf",
        "year_built": "year_built",
        "business_plan_summary": "business_plan_summary",
        "hold_period_years": "hold_period_years"
    }

    for json_field, model_field in field_mapping.items():
        value = deal_data.get(json_field)
        if value is not None:
            # Convert building_sf to Decimal if needed
            if model_field == "building_sf" and not isinstance(value, Decimal):
                value = Decimal(str(value))
            setattr(deal, model_field, value)

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


def _create_or_update_underwriting(underwriting_data: Dict[str, Any], deal_id: UUID, db: Session) -> DealUnderwriting:
    """
    Create or update deal underwriting record.

    Only one underwriting record per deal (unique constraint).
    """
    # Check if underwriting already exists for this deal
    existing = db.query(DealUnderwriting).filter(DealUnderwriting.deal_id == deal_id).first()

    # Prepare data for model
    model_data = {}

    # Map fields from extraction JSON to model fields
    field_mapping = {
        "total_project_cost": "total_project_cost",
        "loan_amount": "loan_amount",
        "equity_required": "equity_required",
        "levered_irr": "levered_irr",
        "unlevered_irr": "unlevered_irr",
        "equity_multiple": "equity_multiple",
        "average_cash_on_cash": "avg_cash_on_cash",  # Note: model uses avg_cash_on_cash
        "hold_period_months": "project_duration_years",  # Convert months to years
    }

    for json_field, model_field in field_mapping.items():
        value = underwriting_data.get(json_field)
        if value is not None:
            # Convert months to years for project_duration_years
            if json_field == "hold_period_months":
                value = Decimal(str(value)) / 12  # Convert months to years
            else:
                # Convert to Decimal for numeric fields
                value = Decimal(str(value))
            model_data[model_field] = value

    # Handle details_json - store additional metrics here
    details_json = underwriting_data.get("details_json", {})

    # Also store purchase_price and renovation_budget in details_json since they're not in the model
    if underwriting_data.get("purchase_price"):
        details_json["purchase_price"] = underwriting_data["purchase_price"]
    if underwriting_data.get("renovation_budget"):
        details_json["renovation_budget"] = underwriting_data["renovation_budget"]

    if details_json:
        model_data["details_json"] = details_json

    if existing:
        # Update existing
        for field, value in model_data.items():
            setattr(existing, field, value)
        return existing
    else:
        # Create new
        underwriting = DealUnderwriting(
            deal_id=deal_id,
            **model_data
        )
        db.add(underwriting)
        db.flush()
        return underwriting
