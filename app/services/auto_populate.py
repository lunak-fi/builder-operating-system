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
    operator_ids: List[UUID],
    db: Session
) -> Dict[str, Any]:
    """
    Populate database with extracted data from LLM.
    Creates new Deal, Principals, and Underwriting records.

    Args:
        extracted_data: Structured data from LLM extraction
        document_id: ID of source document
        operator_ids: List of confirmed operator IDs (required, at least one)
        db: Database session

    Returns:
        Dictionary with IDs of created records:
        {
            "operator_ids": [UUID, ...],
            "deal_id": UUID,
            "principal_ids": [UUID, ...],
            "underwriting_id": UUID
        }
    """
    try:
        # Validate at least one operator
        if not operator_ids:
            raise AutoPopulationError("At least one operator is required")

        result = {
            "operator_ids": operator_ids,
            "deal_id": None,
            "principal_ids": [],
            "underwriting_id": None
        }

        # 1. Use the confirmed operator_ids (already validated by caller)
        logger.info(f"Creating deal with {len(operator_ids)} confirmed operator(s)")

        # 2. Create new deal with extracted data (use first operator for FK)
        deal_data = extracted_data.get("deal", {})
        deal = _create_deal(deal_data, operator_ids[0], db)
        result["deal_id"] = deal.id
        logger.info(f"Deal created: {deal.deal_name} ({deal.id})")

        # 3. Create junction table entries for all operators
        from app.models.deal_operator import DealOperator

        for idx, operator_id in enumerate(operator_ids):
            deal_operator = DealOperator(
                deal_id=deal.id,
                operator_id=operator_id,
                is_primary=(idx == 0)  # First is primary
            )
            db.add(deal_operator)
        logger.info(f"Linked {len(operator_ids)} operator(s) to deal")

        # 4. Create principals for ALL operators (not just first)
        principals_data = extracted_data.get("principals", [])
        all_principals = []
        for operator_id in operator_ids:
            if principals_data:
                principals = _create_principals(principals_data, operator_id, db)
                all_principals.extend(principals)
        result["principal_ids"] = [p.id for p in all_principals]
        if all_principals:
            logger.info(f"Created {len(all_principals)} principal(s)")

        # 5. Create underwriting for the new deal
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

    # Geocode and standardize MSA
    try:
        from app.services.geocoding import MSAGeocoder
        from datetime import datetime

        geocoder = MSAGeocoder()

        # Extract address components
        address = deal_data.get("address_line1", "")
        city = ""  # Could extract from address if needed
        state = deal_data.get("state", "")
        zipcode = deal_data.get("postal_code", "")

        # Attempt geocoding if we have address data
        if address or (city and state):
            geo_result = geocoder.standardize_market(address, city, state, zipcode)

            if geo_result["geocoded"]:
                # Use standardized MSA from Census data
                deal_fields["msa"] = geo_result["msa"]
                deal_fields["latitude"] = geo_result["latitude"]
                deal_fields["longitude"] = geo_result["longitude"]
                deal_fields["geocoded_at"] = datetime.utcnow()
                deal_fields["msa_source"] = "census_geocoder"
                logger.info(f"Geocoded address to MSA: {geo_result['msa']}")
            else:
                # Fallback: Use LLM-extracted MSA
                deal_fields["msa_source"] = "llm_extraction"
                logger.warning("Geocoding failed, using LLM-extracted MSA")

    except Exception as e:
        # Geocoding error - use LLM extraction as fallback
        logger.error(f"Geocoding error: {e}")
        deal_fields["msa_source"] = "llm_extraction"

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
