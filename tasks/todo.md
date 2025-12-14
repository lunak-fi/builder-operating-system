# Fund/Strategy Deck Classification Plan

## Overview
Add support for two document types:
1. **Deal Decks** - Property-specific investments (current flow)
2. **Fund/Strategy Decks** - Investment thesis without a specific property (new)

Currently, Ascend Investment Management and Middle Door Homes are fund/strategy decks incorrectly processed as deals.

---

## Implementation Tasks

### Phase 1: Database Schema

- [x] **1.1 Create Fund model** (`app/models/fund.py`)
  - id (UUID), operator_id (FK), name, strategy
  - target_irr, target_equity_multiple, target_geography, target_asset_types
  - fund_size, gp_commitment, management_fee, carried_interest
  - status (Active, Closed, Fundraising)
  - created_at, updated_at

- [x] **1.2 Create FundDocument model** or extend deal_documents
  - Add optional `fund_id` FK to deal_documents (nullable, like deal_id)

- [x] **1.3 Add fund_id to deals table**
  - Optional FK to link deals sourced from a fund

- [x] **1.4 Create Alembic migration**
  - New funds table
  - Alter deal_documents (add fund_id)
  - Alter deals (add fund_id)

---

### Phase 2: Document Classification

- [x] **2.1 Create classification service** (`app/services/document_classifier.py`)
  - Function: `classify_document(parsed_text: str) -> Literal["deal", "fund"]`
  - Use Claude to detect document type based on content
  - Key indicators for fund decks:
    - No specific property address
    - Investment strategy/thesis language
    - Target criteria (not actual deal metrics)
    - Fund structure terms (GP/LP, management fee, carry)

- [x] **2.2 Update upload flow** (`app/api/documents.py`)
  - After PDF extraction, run classification
  - Store classification result in document record
  - Route to appropriate extraction schema

---

### Phase 3: Fund Extraction Schema

- [x] **3.1 Create fund extraction prompt** (`app/services/llm_extractor.py`)
  - New function: `extract_fund_data_from_text(pdf_text: str)`

---

### Phase 4: Auto-Populate for Funds

- [x] **4.1 Create fund population logic** (`app/services/auto_populate.py`)
  - New function: `populate_fund_from_extraction()`
  - Creates/updates Operator
  - Creates Fund record
  - Creates Principals
  - Links document to fund (not deal)

- [x] **4.2 Update extraction endpoint** (`app/api/documents.py`)
  - Check document classification
  - Route to deal or fund population logic

---

### Phase 5: API Endpoints

- [x] **5.1 Create Fund schemas** (`app/schemas/fund.py`)
  - FundCreate, FundUpdate, FundResponse

- [x] **5.2 Create Fund API** (`app/api/funds.py`)
  - GET /api/funds - List all funds
  - GET /api/funds/{id} - Get fund details
  - GET /api/funds/{id}/deals - Get deals sourced from fund
  - PUT /api/funds/{id} - Update fund
  - DELETE /api/funds/{id} - Delete fund

- [x] **5.3 Register router** (`app/main.py`)

---

### Phase 6: Data Migration

- [x] **6.1 Re-process existing fund decks**
  - Ascend Investment Management - Completed
  - Middle Door Homes - Document not yet uploaded

---

## File Changes Summary

| File | Change |
|------|--------|
| `app/models/fund.py` | New file - Fund model |
| `app/models/__init__.py` | Export Fund |
| `app/models/operator.py` | Added funds relationship |
| `app/models/deal.py` | Added fund_id FK and fund relationship |
| `app/models/deal_document.py` | Added fund_id FK and document_classification |
| `app/schemas/fund.py` | New file - Pydantic schemas |
| `app/schemas/__init__.py` | Export fund schemas |
| `app/api/funds.py` | New file - Fund endpoints |
| `app/api/documents.py` | Add classification routing |
| `app/services/document_classifier.py` | New file - Classification logic |
| `app/services/llm_extractor.py` | Add fund extraction function |
| `app/services/auto_populate.py` | Add fund population function |
| `app/main.py` | Register funds router |
| `migrations/versions/372bb9d35aa5_add_funds_table_and_fund_id_to_deals_.py` | New migration |

---

## Review

### Implementation Complete

All phases of the fund/strategy deck classification feature have been implemented:

1. **Database Schema**: Created `funds` table with full schema including target metrics, fund structure, and relationships. Added `fund_id` FK to both `deals` and `deal_documents` tables.

2. **Document Classification**: Built AI-powered classifier that detects whether a document is a deal deck (property-specific) or fund/strategy deck (investment thesis).

3. **Fund Extraction**: Created dedicated extraction prompt for fund decks that captures:
   - Target IRR, equity multiple
   - Fund size, GP commitment
   - Management fee, carried interest, preferred return
   - Target geography and asset types
   - Investment thesis and track record

4. **API Endpoints**: Full CRUD for funds at `/api/funds/*`

5. **Data Migration**: Successfully re-processed Ascend Investment Management:
   - Correctly classified as "fund"
   - Extracted: 24.5% target IRR, 2.25x multiple, $20M fund size, SFR strategy
   - Created proper fund record instead of deal

### Test Result
```
Ascend Real Estate Fund I LLC | SFR | 24.5% IRR | 2.25x | $20M
```

### Next Steps
- Upload and process Middle Door Homes document when available
- ~~Add frontend UI for viewing funds (new Funds page)~~ ✅ DONE

---

## Frontend Fund Integration

### Implementation Complete

Added frontend support for viewing funds:

1. **API Layer** (`src/lib/api.ts`)
   - Added `fundsAPI` with getAll, get, getDeals, update, delete methods

2. **Types** (`src/lib/types.ts`)
   - Added `FundWithDetails` interface

3. **Navigation** (`src/components/ClientLayout.tsx`)
   - Added "Funds" nav item between Sponsors and Portfolio
   - Uses Landmark icon

4. **Funds List Page** (`/funds`)
   - Created `src/app/funds/page.tsx`
   - Created `src/components/Funds.tsx`
   - Displays: Fund Name, Sponsor, Strategy, Target IRR, Fund Size, Status
   - Includes search and status filter

5. **Fund Detail Page** (`/funds/[id]`)
   - Created `src/app/funds/[id]/page.tsx`
   - Created `src/components/FundDetail.tsx`
   - Displays:
     - Key Metrics: Target IRR, Target Multiple, Fund Size, Preferred Return
     - Fund Structure: GP Commitment, Management Fee, Carried Interest
     - Investment Focus: Strategy, Target Geography, Target Asset Types
     - Deals from this fund (table)
   - Links to sponsor detail page

### Files Created
| File | Description |
|------|-------------|
| `src/app/funds/page.tsx` | Funds list route |
| `src/app/funds/[id]/page.tsx` | Fund detail route |
| `src/components/Funds.tsx` | Funds list component |
| `src/components/FundDetail.tsx` | Fund detail component |

### Files Modified
| File | Change |
|------|--------|
| `src/lib/api.ts` | Added fundsAPI |
| `src/lib/types.ts` | Added FundWithDetails interface |
| `src/components/ClientLayout.tsx` | Added Funds nav item |
