from typing import Optional, Dict, Tuple
import requests
from shapely.geometry import Point
import geopandas as gpd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MSAGeocoder:
    def __init__(self):
        shapefile_path = Path(__file__).parent.parent / "data" / "msa_boundaries" / "tl_2023_us_cbsa.shp"
        if not shapefile_path.exists():
            raise FileNotFoundError(f"MSA shapefile not found at {shapefile_path}")
        self.msa_gdf = gpd.read_file(shapefile_path)
        # Reproject to WGS84 to match geocoding results
        self.msa_gdf = self.msa_gdf.to_crs("EPSG:4326")

    def geocode_address(self, address: str, city: str, state: str, zipcode: str) -> Optional[Tuple[float, float]]:
        """Use Census Geocoder API to convert address to lat/lon"""
        address_parts = [p for p in [address, city, state, zipcode] if p]
        if not address_parts:
            return None

        full_address = ", ".join(address_parts)

        try:
            url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
            params = {
                "address": full_address,
                "benchmark": "Public_AR_Current",
                "format": "json"
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            matches = data.get("result", {}).get("addressMatches", [])
            if matches:
                coords = matches[0]["coordinates"]
                return (coords["y"], coords["x"])  # (latitude, longitude)

            return None

        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None

    def get_msa_from_coords(self, lat: float, lon: float) -> Optional[str]:
        """Perform spatial join to find MSA containing coordinates"""
        try:
            point = Point(lon, lat)
            point_gdf = gpd.GeoDataFrame([{"geometry": point}], crs="EPSG:4326")

            joined = gpd.sjoin(point_gdf, self.msa_gdf, how="left", predicate="within")

            if not joined.empty and "NAME" in joined.columns:
                msa_name = joined.iloc[0]["NAME"]
                return msa_name

            return None

        except Exception as e:
            logger.error(f"MSA lookup error: {e}")
            return None

    def standardize_market(self, address: str, city: str, state: str, zipcode: str) -> Dict:
        """Convert address to standardized MSA"""
        coords = self.geocode_address(address, city, state, zipcode)

        if coords:
            msa = self.get_msa_from_coords(*coords)
            return {
                "msa": msa,
                "latitude": coords[0],
                "longitude": coords[1],
                "geocoded": True
            }

        return {"msa": None, "geocoded": False}
