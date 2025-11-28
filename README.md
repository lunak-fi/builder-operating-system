# Builder Operating System

FastAPI backend for managing operators and principals in the commercial real estate industry.

## Project Structure

```
/app
  /api          # API endpoints (to be implemented)
  /models       # SQLAlchemy models
  /schemas      # Pydantic schemas
  /db           # Database session, base, config
  main.py       # FastAPI application
/migrations     # Alembic migrations
alembic.ini     # Alembic configuration
requirements.txt
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Database

Copy the example environment file:

```bash
cp .env.example .env
```

Update the `DATABASE_URL` in `.env` if needed.

### 3. Create Database

```bash
createdb builder_os
```

Or using psql:

```sql
CREATE DATABASE builder_os;
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## Database Models

### Operators
- Commercial real estate operators/companies
- Fields: name, legal_name, website, headquarters info, focus areas, etc.
- Relationships: One-to-many with principals and deals

### Principals
- Key people associated with operators
- Fields: full_name, headline, contact info, experience, etc.
- Foreign key relationship to operators (CASCADE delete)

### Deals
- Real estate deals/investments managed by operators
- Fields: internal_code, deal_name, location (country, state, msa, submarket), asset details (type, strategy, units, sq ft), business plan, status, etc.
- Foreign key relationship to operators (CASCADE delete)
- Relationships: One-to-many with deal_documents and memos, one-to-one with deal_underwriting

### Deal Documents
- Documents associated with deals (pitchbooks, reports, etc.)
- Fields: document_type, file_name, file_url, parsed_text, parsing_status, etc.
- Foreign key relationship to deals (CASCADE delete)

### Deal Underwriting
- Financial underwriting analysis for deals (one per deal)
- Fields: costs (total_project_cost, land_cost, hard_cost, soft_cost), financing (loan_amount, equity_required, interest_rate, ltv, ltc), returns (levered_irr, unlevered_irr, equity_multiple, cash_on_cash), metrics (dscr, exit_cap_rate, yield_on_cost), details_json (JSONB for additional data)
- Foreign key relationship to deals (CASCADE delete) with UNIQUE constraint
- Optional reference to source_document

### Memos
- Investment memos and notes associated with deals
- Fields: title, memo_type, content_markdown, generated_by
- Foreign key relationship to deals (CASCADE delete)

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Next Steps

- Implement CRUD endpoints in `/app/api`
- Add authentication/authorization
- Add additional models as needed
- Implement business logic
