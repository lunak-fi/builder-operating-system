from app.db.session import SessionLocal
from app.models import Deal
from app.services.geocoding import MSAGeocoder
from datetime import datetime

def backfill_geocoding():
    """Geocode all existing deals with address data"""
    db = SessionLocal()
    geocoder = MSAGeocoder()

    deals = db.query(Deal).filter(
        Deal.address_line1.isnot(None),
        Deal.latitude.is_(None)
    ).all()

    print(f"Found {len(deals)} deals to geocode")

    success_count = 0
    fail_count = 0

    for deal in deals:
        try:
            result = geocoder.standardize_market(
                deal.address_line1 or "",
                "",
                deal.state or "",
                deal.postal_code or ""
            )

            if result["geocoded"]:
                deal.msa = result["msa"]
                deal.latitude = result["latitude"]
                deal.longitude = result["longitude"]
                deal.geocoded_at = datetime.utcnow()
                deal.msa_source = "backfill_geocode"
                success_count += 1
                print(f"✅ {deal.deal_name}: {result['msa']}")
            else:
                fail_count += 1
                print(f"❌ {deal.deal_name}: Geocoding failed")

        except Exception as e:
            fail_count += 1
            print(f"❌ {deal.deal_name}: Error - {e}")

    db.commit()
    db.close()

    print(f"\n📊 Results: {success_count} success, {fail_count} failed")

if __name__ == "__main__":
    backfill_geocoding()
