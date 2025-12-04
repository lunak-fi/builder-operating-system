# Database Schema - Complete Reference

## Overview
Commercial Real Estate deal management system with 6 core tables tracking operators, principals, deals, documents, underwriting data, and investment memos.

---

## Tables

### 1. operators
**Description**: Commercial real estate operators/companies

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| name | TEXT | NOT NULL | Company name |
| legal_name | TEXT | NULL | Legal entity name |
| website_url | TEXT | NULL | Company website |
| hq_city | TEXT | NULL | Headquarters city |
| hq_state | TEXT | NULL | Headquarters state |
| hq_country | TEXT | NOT NULL, DEFAULT 'USA' | Headquarters country |
| primary_geography_focus | TEXT | NULL | Primary geographic focus area |
| primary_asset_type_focus | TEXT | NULL | Primary asset type focus |
| description | TEXT | NULL | Company description |
| notes | TEXT | NULL | Additional notes |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Last update timestamp |

**Relationships**:
- One-to-Many with `principals` (CASCADE delete)
- One-to-Many with `deals` (CASCADE delete)

---

### 2. principals
**Description**: Key people associated with operators

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| operator_id | UUID | NOT NULL, FK → operators.id (CASCADE) | Associated operator |
| full_name | TEXT | NOT NULL | Person's full name |
| headline | TEXT | NULL | Professional headline |
| linkedin_url | TEXT | NULL | LinkedIn profile URL |
| email | TEXT | NULL | Email address |
| phone | TEXT | NULL | Phone number |
| bio | TEXT | NULL | Biography |
| background_summary | TEXT | NULL | Professional background summary |
| years_experience | INTEGER | NULL | Years of experience |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Last update timestamp |

**Relationships**:
- Many-to-One with `operators`

---

### 3. deals
**Description**: Real estate deals/investments

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| operator_id | UUID | NOT NULL, FK → operators.id (CASCADE) | Deal operator |
| internal_code | TEXT | NOT NULL | Internal tracking code |
| deal_name | TEXT | NOT NULL | Deal name |
| country | TEXT | NOT NULL, DEFAULT 'USA' | Property country |
| state | TEXT | NULL | Property state |
| msa | TEXT | NULL | Metropolitan Statistical Area |
| submarket | TEXT | NULL | Submarket within MSA |
| address_line1 | TEXT | NULL | Street address |
| postal_code | TEXT | NULL | ZIP/postal code |
| asset_type | TEXT | NULL | Asset type (multifamily, office, etc.) |
| strategy_type | TEXT | NULL | Investment strategy |
| num_units | INTEGER | NULL | Number of units |
| building_sf | NUMERIC | NULL | Building square footage |
| year_built | INTEGER | NULL | Year property was built |
| business_plan_summary | TEXT | NULL | Business plan summary |
| hold_period_years | NUMERIC | NULL | Expected hold period in years |
| status | TEXT | NOT NULL, DEFAULT 'inbox' | Deal status |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Last update timestamp |

**Relationships**:
- Many-to-One with `operators`
- One-to-Many with `deal_documents` (CASCADE delete)
- One-to-One with `deal_underwriting` (CASCADE delete)
- One-to-Many with `memos` (CASCADE delete)

---

### 4. deal_documents
**Description**: Documents associated with deals (PDFs, pitchbooks, etc.)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| deal_id | UUID | NOT NULL, FK → deals.id (CASCADE) | Associated deal |
| document_type | TEXT | NOT NULL | Document type (pitch_deck, etc.) |
| file_name | TEXT | NOT NULL | Original filename |
| file_url | TEXT | NOT NULL | File storage path/URL |
| source_description | TEXT | NULL | Source description |
| parsed_text | TEXT | NULL | Extracted text from document |
| parsing_status | TEXT | NOT NULL, DEFAULT 'pending' | Status: pending/processing/completed/failed |
| parsing_error | TEXT | NULL | Error message if parsing failed |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Last update timestamp |

**Relationships**:
- Many-to-One with `deals`

---

### 5. deal_underwriting
**Description**: Financial underwriting analysis (one per deal)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| deal_id | UUID | NOT NULL, UNIQUE, FK → deals.id (CASCADE) | Associated deal (1:1) |
| source_document_id | UUID | NULL, FK → deal_documents.id | Source document reference |
| version_label | TEXT | NULL | Version identifier |
| **Costs** ||||
| total_project_cost | NUMERIC | NULL | Total project cost |
| land_cost | NUMERIC | NULL | Land acquisition cost |
| hard_cost | NUMERIC | NULL | Hard construction costs |
| soft_cost | NUMERIC | NULL | Soft costs (fees, etc.) |
| **Financing** ||||
| loan_amount | NUMERIC | NULL | Loan amount |
| equity_required | NUMERIC | NULL | Required equity investment |
| interest_rate | NUMERIC | NULL | Loan interest rate |
| ltv | NUMERIC | NULL | Loan-to-Value ratio |
| ltc | NUMERIC | NULL | Loan-to-Cost ratio |
| **Returns** ||||
| levered_irr | NUMERIC | NULL | Levered IRR (%) |
| unlevered_irr | NUMERIC | NULL | Unlevered IRR (%) |
| equity_multiple | NUMERIC | NULL | Equity multiple |
| avg_cash_on_cash | NUMERIC | NULL | Average cash-on-cash return |
| **Metrics** ||||
| dscr_at_stabilization | NUMERIC | NULL | Debt Service Coverage Ratio |
| exit_cap_rate | NUMERIC | NULL | Exit cap rate |
| yield_on_cost | NUMERIC | NULL | Yield on cost |
| project_duration_years | NUMERIC | NULL | Project duration |
| **Flexible Storage** ||||
| details_json | JSONB | NULL | Additional data as JSON |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Last update timestamp |

**Relationships**:
- One-to-One with `deals` (UNIQUE constraint on deal_id)
- Optional reference to `deal_documents`

---

### 6. memos
**Description**: Investment memos and notes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated UUID |
| deal_id | UUID | NOT NULL, FK → deals.id (CASCADE) | Associated deal |
| title | TEXT | NULL | Memo title |
| memo_type | TEXT | NOT NULL, DEFAULT 'investment_memo' | Memo type |
| content_markdown | TEXT | NOT NULL | Memo content in markdown |
| generated_by | TEXT | NULL | Generation source (human/AI) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |

**Relationships**:
- Many-to-One with `deals`

---

## Entity Relationship Diagram

```
┌─────────────────┐
│   operators     │
│─────────────────│
│ id (PK)         │
│ name            │
│ legal_name      │
│ website_url     │
│ hq_city         │
│ hq_state        │
│ hq_country      │
│ ...             │
└────────┬────────┘
         │
         │ 1:N
         │
    ┌────┴─────────────────────────────┐
    │                                  │
    │                                  │
┌───▼──────────┐              ┌───────▼────────┐
│  principals  │              │     deals      │
│──────────────│              │────────────────│
│ id (PK)      │              │ id (PK)        │
│ operator_id  │              │ operator_id    │
│ full_name    │              │ internal_code  │
│ headline     │              │ deal_name      │
│ linkedin_url │              │ country        │
│ email        │              │ state          │
│ ...          │              │ msa            │
└──────────────┘              │ asset_type     │
                              │ strategy_type  │
                              │ status         │
                              │ ...            │
                              └────┬───────────┘
                                   │
                                   │ 1:N
                    ┌──────────────┼──────────────┬─────────────┐
                    │              │              │             │
                    │              │              │             │ 1:1
                    │              │              │             │
            ┌───────▼────────┐  ┌──▼─────────┐ ┌─▼────────────────┐
            │ deal_documents │  │   memos    │ │ deal_underwriting│
            │────────────────│  │────────────│ │──────────────────│
            │ id (PK)        │  │ id (PK)    │ │ id (PK)          │
            │ deal_id        │  │ deal_id    │ │ deal_id (UNIQUE) │
            │ document_type  │  │ title      │ │ source_doc_id    │
            │ file_name      │  │ memo_type  │ │ version_label    │
            │ file_url       │  │ content_md │ │ total_proj_cost  │
            │ parsed_text    │  │ generated  │ │ land_cost        │
            │ parsing_status │  │ ...        │ │ hard_cost        │
            │ ...            │  └────────────┘ │ soft_cost        │
            └────────────────┘                 │ loan_amount      │
                                               │ equity_required  │
                                               │ levered_irr      │
                                               │ unlevered_irr    │
                                               │ equity_multiple  │
                                               │ details_json     │
                                               │ ...              │
                                               └──────────────────┘
```

---

## Key Features

### UUID Primary Keys
- All tables use UUID with server-side generation (`uuid.uuid4`)
- Prevents ID collision and enables distributed systems

### Timestamps
- `created_at`: Server-side default `now()`
- `updated_at`: Server-side default `now()` with automatic update on modification

### Cascade Deletes
- All foreign keys use `ON DELETE CASCADE`
- Deleting an operator removes all principals and deals
- Deleting a deal removes all documents, underwriting, and memos

### JSONB Support
- `deal_underwriting.details_json` uses PostgreSQL JSONB
- Flexible storage for additional metrics not in schema

### Unique Constraints
- `deal_underwriting.deal_id` is UNIQUE (enforces 1:1 relationship)

---

## Migration Chain

1. **79df4a9ae6de** - Initial migration: operators and principals tables
2. **1bd3146a267e** - Add deals and deal_documents tables
3. **18fdc704c9b4** - Add deal_underwriting and memos tables

---

## API Endpoints (Implemented)

### Operators
- `GET /api/operators` - List all operators
- `POST /api/operators` - Create operator
- `GET /api/operators/{id}` - Get operator by ID
- `PUT /api/operators/{id}` - Update operator
- `DELETE /api/operators/{id}` - Delete operator

### Principals
- `GET /api/principals` - List all principals
- `POST /api/principals` - Create principal
- `GET /api/principals/{id}` - Get principal by ID
- `PUT /api/principals/{id}` - Update principal
- `DELETE /api/principals/{id}` - Delete principal

### Deals
- `GET /api/deals` - List all deals
- `POST /api/deals` - Create deal
- `GET /api/deals/{id}` - Get deal by ID
- `PUT /api/deals/{id}` - Update deal
- `DELETE /api/deals/{id}` - Delete deal

### Documents
- `POST /api/documents/upload` - Upload PDF & auto-create deal (recommended)
- `POST /api/documents/deals/{deal_id}/upload` - Upload PDF for existing deal
- `GET /api/documents/deals/{deal_id}/documents` - List deal documents
- `GET /api/documents/{document_id}` - Get document by ID
- `GET /api/documents/{document_id}/status` - Get parsing status
- `POST /api/documents/{document_id}/extract` - Extract structured data via LLM
- `DELETE /api/documents/{document_id}` - Delete document

### Underwriting
- `GET /api/underwriting/deals/{deal_id}` - Get deal underwriting
- `POST /api/underwriting/deals/{deal_id}` - Create/update underwriting
- `DELETE /api/underwriting/{underwriting_id}` - Delete underwriting

### Memos
- **Not yet implemented** - Model exists but no API endpoints

---

## Workflow

1. **Upload Document**: `POST /api/documents/upload` uploads PDF, auto-creates deal
2. **Background Extraction**: PDF text extracted in background task
3. **LLM Processing**: `POST /api/documents/{id}/extract` sends text to Claude AI
4. **Auto-Population**: Extracted data populates operator, deal, principals, underwriting tables
5. **Review & Edit**: Use CRUD endpoints to refine extracted data
