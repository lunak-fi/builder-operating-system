import os
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer

CLERK_JWKS_URL = os.getenv(
    "CLERK_JWKS_URL",
    "https://moved-mackerel-98.clerk.accounts.dev/.well-known/jwks.json"
)

clerk_config = ClerkConfig(jwks_url=CLERK_JWKS_URL)
require_auth = ClerkHTTPBearer(config=clerk_config)
