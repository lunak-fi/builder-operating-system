# Database Schema

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

## Table Relationships

### One-to-Many Relationships
- `operators` → `principals` (CASCADE delete)
- `operators` → `deals` (CASCADE delete)
- `deals` → `deal_documents` (CASCADE delete)
- `deals` → `memos` (CASCADE delete)

### One-to-One Relationships
- `deals` → `deal_underwriting` (CASCADE delete, UNIQUE constraint on deal_id)

### Optional Relationships
- `deal_underwriting` → `deal_documents` (source_document_id, nullable)

## Migration Chain

1. **79df4a9ae6de** - Initial migration: operators and principals tables
2. **1bd3146a267e** - Add deals and deal_documents tables
3. **18fdc704c9b4** - Add deal_underwriting and memos tables

## Key Features

- **UUID Primary Keys**: All tables use UUID with server-side generation
- **Timestamps**: created_at and updated_at on most tables
- **Cascade Deletes**: All foreign keys use ON DELETE CASCADE
- **JSONB Support**: deal_underwriting.details_json for flexible data storage
- **Unique Constraints**: deal_underwriting enforces one underwriting per deal
