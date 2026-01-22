import requests
import zipfile
from pathlib import Path

def download_msa_shapefiles():
    """Download Census MSA boundary shapefiles"""
    url = "https://www2.census.gov/geo/tiger/TIGER2023/CBSA/tl_2023_us_cbsa.zip"
    output_dir = Path(__file__).parent.parent / "app" / "data" / "msa_boundaries"
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / "msa_shapefiles.zip"

    print(f"Downloading MSA shapefiles from Census Bureau...")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Extracting shapefiles...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(output_dir)

    zip_path.unlink()
    print(f"✅ MSA shapefiles downloaded to {output_dir}")

if __name__ == "__main__":
    download_msa_shapefiles()
