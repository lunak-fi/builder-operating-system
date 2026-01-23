# Excel Financial Analyst - Integration Plan

## Problem Statement

Current PDF extraction has fundamental limitations:
- ❌ No standardization in deck layouts
- ❌ Confusion between main deals and case studies (e.g., extracting "718 Lorimer Street" case study instead of "100 N 3rd Street" main deal)
- ❌ Vision extraction is expensive (~$0.05-0.10/doc) and still error-prone
- ❌ Text extraction produces garbled output for designed PDFs

**Root Insight:** The **source of truth** for financial metrics already exists in structured Excel models (*.xlsx) that accompany most investment decks.

---

## Solution: Excel-First Financial Extraction

Create a specialized **Financial Analyst Service** that:
1. ✅ Analyzes structured Excel financial models directly
2. ✅ Extracts IRR, MOIC, equity, hold period, cap rates from cells/formulas
3. ✅ Prioritizes Excel data over PDF extraction when both are present
4. ✅ Handles variations in model structure (different sheet names, layouts)
5. ✅ Falls back to PDF extraction only when no Excel is available

---

## Integration Architecture

### Current Workflow (PDF Only)

```
User uploads PDF → Background Parsing → Text/Vision Extraction
                                              ↓
                                    Preview Extracted Data
                                              ↓
                                    User Confirms Sponsor
                                              ↓
                                         Create Deal
```

### New Workflow (PDF + Excel)

```
User uploads PDF → Background Parsing
User uploads Excel → Background Parsing
                           ↓
                  User clicks "Continue"
                           ↓
               Check: Is Excel uploaded?
                           ↓
        ┌──────────────────┴──────────────────┐
        │                                     │
     YES│                                     │NO
        ↓                                     ↓
Excel Financial Analyst            PDF Extraction
(Structured extraction)           (Text or Vision)
        │                                     │
        └──────────────────┬──────────────────┘
                           ↓
                   Merge Data:
                   - PDF: Deal description, sponsor, property info
                   - Excel: ALL financial metrics (prioritized)
                           ↓
                   Preview Combined Data
                           ↓
                   User Confirms Sponsor
                           ↓
                       Create Deal
```

---

## User Decisions Made

### 1. Upload Flow
**Decision:** Sequential upload with linking (minimal UI changes)

**Implementation:**
- Keep existing single-file upload UI
- After first document uploaded, show "Upload Additional Document" option
- When second document detected, show: "Analyze with previous document?"
- User confirms → both documents sent to extraction together
- Frontend tracks documents uploaded in same session
- Passes multiple `document_ids` to extraction endpoint

### 2. Common Sheet Names
**Decision:** Focus on these patterns (from user's real models)

- **"Returns"** / **"Investment Returns"** - IRR, equity multiple, return projections
- **"Sources & Uses"** / **"S&U"** - Project costs, equity, debt breakdown
- **"Cash Flow"** / **"Proforma"** - Monthly/annual cash flow projections
- **"Overview"** - High-level summary metrics

**Implementation:** Use fuzzy matching (e.g., "Inv Returns" matches "Investment Returns")

### 3. Re-extraction Strategy
**Decision:** Yes, allow re-extraction after deal creation

**Use cases:**
- User uploads better/updated Excel model later
- Initial extraction was incorrect
- Want to switch from PDF-first to Excel-first

**Implementation:**
- Add `POST /api/deals/{deal_id}/re-extract` endpoint
- Show comparison: "Old values vs. New extracted values"
- User can accept all or selectively apply changes
- Track extraction history in deal metadata

---

## Integration Points

### 1. Finding Related Documents

**Challenge:** How to know which Excel file goes with which PDF?

**Solution: Session Grouping + Same Deal**

**Option A: Upload session grouping** (for new uploads)
- Frontend tracks documents uploaded in same session
- Passes array of `document_ids` to extraction endpoint
- Backend extracts from all and merges

**Option B: Same deal_id** (for later additions)
- User creates deal with PDF
- Later uploads Excel to existing deal
- Extraction can re-run using both documents

**Implementation:**
```python
# Modified extraction endpoint
POST /api/documents/{document_id}/extract
{
    "related_document_ids": ["uuid2"]  # Optional: Excel or other docs
}

# Find related docs helper
def find_related_excel_documents(document_id: str, db: Session) -> List[DealDocument]:
    """Find Excel documents related to the given document."""
    document = db.query(DealDocument).filter(DealDocument.id == document_id).first()

    if not document:
        return []

    # Strategy 1: Same upload session (documents without deal_id uploaded recently)
    if document.deal_id is None:
        recent_docs = db.query(DealDocument).filter(
            DealDocument.deal_id == None,
            DealDocument.document_type == "financial_model",
            DealDocument.created_at >= document.created_at - timedelta(minutes=10)
        ).all()
        return recent_docs

    # Strategy 2: Same deal
    if document.deal_id:
        deal_docs = db.query(DealDocument).filter(
            DealDocument.deal_id == document.deal_id,
            DealDocument.document_type == "financial_model"
        ).all()
        return deal_docs

    return []
```

---

### 2. Extraction Decision Logic

**Where:** `POST /api/documents/{document_id}/extract` endpoint

**New logic:**
```python
# Step 1: Check for related Excel documents
excel_docs = find_related_excel_documents(document_id, db)

# Step 2: Determine extraction strategy
if excel_docs:
    # Excel-first strategy
    financial_data = extract_from_excel(excel_docs[0])

    if document.document_type == "offer_memo":
        # PDF provides deal narrative, Excel provides financials
        narrative_data = extract_deal_narrative_from_pdf(document)
        extracted_data = merge_extraction_data(narrative_data, financial_data)
    else:
        # Excel-only extraction
        extracted_data = financial_data

elif document.document_type == "offer_memo":
    # PDF-only extraction (existing logic)
    if has_images or text_too_short:
        extracted_data = extract_deal_data_from_vision(document)
    else:
        extracted_data = extract_deal_data_from_text(document)

elif document.document_type == "financial_model":
    # Excel-only extraction
    extracted_data = extract_from_excel(document)
```

---

### 3. Data Merging Strategy

**Principle:** Excel is source of truth for financial metrics

**Merge logic:**

| Data Type | Source Priority | Fallback |
|---|---|---|
| **Deal Name** | PDF | Excel sheet name |
| **Address** | PDF | None (rarely in Excel) |
| **Property Description** | PDF | None |
| **Sponsor Name** | PDF | Excel metadata |
| **Business Plan** | PDF | None |
| **Asset Type** | PDF | None |
| **Strategy Type** | PDF | None |
| **Hold Period** | Excel | PDF |
| **IRR (Levered/Unlevered)** | Excel | PDF |
| **Equity Multiple** | Excel | PDF |
| **Total Project Cost** | Excel | PDF |
| **Equity Required** | Excel | PDF |
| **Debt Amount** | Excel | PDF |
| **Exit Cap Rate** | Excel | PDF |
| **DSCR** | Excel | PDF |
| **All other financial metrics** | Excel | PDF |

**Implementation:**
```python
def merge_extraction_data(pdf_data: Dict, excel_data: Dict) -> Dict:
    """
    Merge PDF narrative with Excel financials.
    Excel takes precedence for all financial metrics.
    """
    merged = pdf_data.copy()

    # Override all underwriting fields with Excel data
    if "underwriting" in excel_data:
        merged["underwriting"] = excel_data["underwriting"]

    # Keep deal narrative from PDF
    # Keep operators from PDF (sponsor identification)
    # Keep principals from PDF (team bios)

    # Add metadata about data sources
    merged["_extraction_metadata"] = {
        "pdf_source": pdf_data.get("_extraction_metadata", {}),
        "excel_source": excel_data.get("_extraction_metadata", {}),
        "merged": True
    }

    return merged
```

---

## Excel Financial Analyst Service Design

### Service Responsibilities

1. **Identify model structure:**
   - Find sheet names (user's common patterns):
     * "Returns" / "Investment Returns"
     * "Sources & Uses" / "S&U"
     * "Cash Flow" / "Proforma"
     * "Overview"
   - Locate financial metrics by searching for keywords in cells
   - Handle common variations: "IRR", "Int Rate of Return", "Internal Rate of Return"
   - Use fuzzy matching for sheet names (e.g., "Inv Returns" matches "Investment Returns")

2. **Extract metrics:**
   - Search for cells containing: "IRR", "MOIC", "Equity Multiple", "DSCR", "Cap Rate"
   - Extract adjacent cell values (usually to the right or below)
   - Parse percentages → decimals (19.6% → 0.196)
   - Parse currency → numbers ($1,685,348 → 1685348)

3. **Validate extraction:**
   - Check if numbers are in reasonable ranges
   - Flag if IRR > 100% (likely formatting error)
   - Flag if equity multiple < 0.5 or > 10
   - Warn if critical metrics are missing

4. **Return structured data:**
   - Same JSON format as PDF extraction
   - Include confidence scores for each metric
   - Include cell references (for debugging)

### Example Usage

```python
from app.services.excel_analyst import analyze_financial_model

result = analyze_financial_model(
    excel_path="/path/to/model.xlsx",
    focus_metrics=["irr", "moic", "equity", "hold_period"]
)

# Returns:
{
    "underwriting": {
        "levered_irr": 0.196,
        "equity_multiple": 1.73,
        "equity_required": 1685348,
        "hold_period_months": 60,
        "total_project_cost": 1685348,
        "_confidence": {
            "levered_irr": 0.95,
            "equity_multiple": 0.95,
            "equity_required": 0.90
        },
        "_cell_references": {
            "levered_irr": "Returns!D12",
            "equity_multiple": "Returns!D13"
        }
    }
}
```

---

## Implementation Phases

### Phase 1: Basic Excel Extraction (MVP)
**Goal:** Extract financial metrics from Excel models

**Status:** 🔜 Next up

**Tasks:**
- [ ] Create `app/services/excel_analyst.py` service module
- [ ] Implement basic sheet identification (find Returns, S&U, Cash Flow, Overview sheets)
- [ ] Implement metric extraction (IRR, MOIC, equity, hold period)
- [ ] Add unit tests with sample Excel files
- [ ] Update extraction endpoint to support financial_model type
- [ ] Test with real user Excel models

**Files:**
- New: `app/services/excel_analyst.py`
- Modified: `app/api/documents.py` (add Excel extraction path)

**Success Criteria:**
- ✅ Can extract IRR from "Returns" sheet
- ✅ Can extract equity multiple from various cell locations
- ✅ Handles percentage → decimal conversion
- ✅ Returns same JSON structure as PDF extraction

---

### Phase 2: Multi-Document Extraction
**Goal:** Extract from PDF + Excel together

**Status:** ⏸️ Waiting on Phase 1

**Tasks:**
- [ ] Add `related_document_ids` parameter to extraction endpoint
- [ ] Implement `find_related_excel_documents()` helper
- [ ] Implement `merge_extraction_data()` function
- [ ] Update frontend to track upload session
- [ ] Update frontend to pass multiple document IDs
- [ ] Test PDF + Excel extraction workflow
- [ ] Test Excel-only extraction workflow

**Files:**
- Modified: `app/api/documents.py` (merge logic)
- Modified: `app/services/llm_extractor.py` (add merge function)
- Modified: Frontend upload components (session tracking)

**Success Criteria:**
- ✅ Uploading PDF + Excel in same session merges data
- ✅ Financial metrics from Excel override PDF
- ✅ Deal narrative from PDF preserved
- ✅ Extraction metadata tracks sources

---

### Phase 3: Advanced Excel Analysis
**Goal:** Handle variations in model structure

**Status:** ⏸️ Future enhancement

**Tasks:**
- [ ] Implement fuzzy sheet name matching
- [ ] Add support for common model variations
- [ ] Improve metric confidence scoring
- [ ] Add validation warnings (IRR > 100%, etc.)
- [ ] Handle multi-scenario models (Base/Upside/Downside)
- [ ] Extract additional metrics (yield on cost, cash-on-cash, etc.)

**Files:**
- Enhanced: `app/services/excel_analyst.py`

---

### Phase 4: Re-extraction & Refinement
**Goal:** Allow re-extraction with different strategies

**Status:** ⏸️ Future enhancement

**Tasks:**
- [ ] Add `POST /api/deals/{deal_id}/re-extract` endpoint
- [ ] Support switching between Excel-first and PDF-first strategies
- [ ] Allow uploading new Excel model to existing deal → triggers re-extraction
- [ ] Show comparison: "Old values vs. New extracted values"
- [ ] User can accept all changes or selectively apply
- [ ] Track extraction history in deal metadata
- [ ] Add "Extraction History" section in deal detail

**Files:**
- New: Re-extraction endpoints
- Modified: Frontend deal editing components
- New: Extraction history tracking

---

## API Changes Required

### New Endpoints

```python
# Extract from multiple documents (PDF + Excel)
POST /api/documents/extract-batch
Request:
{
    "document_ids": ["uuid1", "uuid2"],
    "primary_document_id": "uuid1"  # Which doc is the main PDF
}

Response:
{
    "success": true,
    "extracted_data": {...},
    "operator_matches": [...],
    "extraction_sources": {
        "pdf": "uuid1",
        "excel": "uuid2"
    }
}

# Re-extract using existing deal documents
POST /api/deals/{deal_id}/re-extract
Request:
{
    "use_excel": true,  # Prioritize Excel if available
    "document_ids": ["uuid1", "uuid2"]  # Optional: specific docs
}

Response:
{
    "success": true,
    "old_data": {...},
    "new_data": {...},
    "changes": [...]  # List of changed fields
}
```

### Modified Endpoints

```python
# Existing extraction endpoint - add optional related_document_ids
POST /api/documents/{document_id}/extract
Request (optional):
{
    "related_document_ids": ["uuid2"]  # Optional: Excel or other docs
}

Response (enhanced):
{
    "success": true,
    "document_id": "uuid1",
    "extracted_data": {...},
    "operator_matches": [...],
    "extraction_method": "excel",  # NEW: tracks source
    "extraction_sources": {  # NEW: detailed source tracking
        "narrative": "pdf",
        "financials": "excel"
    }
}
```

---

## Success Criteria

### Phase 1 (Basic Excel Extraction)

✅ **Excel extraction accurately extracts:**
- Levered IRR (19.6% → 0.196)
- Equity Multiple (1.73x → 1.73)
- Total Project Cost, Equity Required
- Hold Period
- All other financial metrics present in model

✅ **No confusion between main deal and case studies:**
- Excel model is for the primary deal only
- No risk of extracting historical performance

✅ **Extraction is fast and reliable:**
- Excel extraction: < 5 seconds
- No API calls required (direct cell reading)

### Phase 2 (Multi-Document Extraction)

✅ **Data prioritization works correctly:**
- Financial metrics from Excel override PDF
- Deal narrative from PDF preserved
- Sponsor info from PDF preserved

✅ **Combined extraction speed:**
- PDF + Excel extraction: < 15 seconds total

### Overall

✅ **Graceful fallbacks:**
- PDF-only upload still works (existing behavior)
- Excel-only upload extracts what it can
- Missing metrics flagged clearly

---

## Technical Dependencies

### Existing (Already Installed)
- `openpyxl` - Excel file reading (already in requirements.txt)
- `pandas` - Data manipulation (optional, for complex analysis)

### New (If Needed)
- None required for MVP - openpyxl is sufficient

---

## Files Modified Summary

### Phase 1 (Backend Only)

| File | Status | Changes |
|------|--------|---------|
| `app/services/excel_analyst.py` | NEW | Core Excel extraction service |
| `app/api/documents.py` | Modified | Add Excel extraction path |
| `tests/test_excel_analyst.py` | NEW | Unit tests |

### Phase 2 (Backend + Frontend)

| File | Status | Changes |
|------|--------|---------|
| `app/api/documents.py` | Modified | Add merge logic, related docs |
| `app/services/llm_extractor.py` | Modified | Add `merge_extraction_data()` |
| Frontend upload components | Modified | Session tracking, multi-doc support |

---

## Risk Mitigation

### Risk 1: Excel Models Vary Too Much
**Mitigation:**
- Start with user's known model patterns
- Add fuzzy matching for sheet names
- Log extraction failures for analysis
- Iterate based on real-world failures

### Risk 2: Cell Values Are Formulas
**Mitigation:**
- openpyxl reads calculated values by default
- Use `data_only=True` flag when loading workbook
- Falls back to formula if value not cached

### Risk 3: Multi-Scenario Models (Base/Upside/Downside)
**Mitigation:**
- Phase 1: Extract only Base case
- Phase 3: Add scenario detection and selection
- User can specify preferred scenario in UI

### Risk 4: Extraction Confidence Too Low
**Mitigation:**
- Return confidence scores for each metric
- Flag low-confidence extractions in UI
- Allow manual override
- Track which models work well vs. poorly

---

## Cost & Performance

### Extraction Cost
- **Excel extraction:** $0 (no API calls, direct cell reading)
- **PDF extraction:** $0.01-0.09 (LLM-based)
- **Combined (PDF + Excel):** $0.01-0.09 (same as PDF alone)

**Savings:** Excel extraction is free and faster than vision-based PDF extraction

### Performance
- **Excel file reading:** < 1 second (openpyxl)
- **Metric extraction:** < 1 second (cell searching)
- **Total Excel extraction:** < 5 seconds
- **Combined PDF + Excel:** < 15 seconds total

---

## Next Steps

1. ✅ **Integration design complete**
2. ✅ **User decisions made**
3. **Ready for implementation:** Begin Phase 1 (Basic Excel Extraction MVP)
4. **After Phase 1:** Test with real user Excel models, iterate
5. **Then Phase 2:** Multi-document extraction and merging

---

## Critical Files Reference

**New Files:**
- `app/services/excel_analyst.py` - Excel extraction service
- `tests/test_excel_analyst.py` - Unit tests

**Modified Files:**
- `app/api/documents.py` - Extraction endpoint with Excel support
- `app/services/llm_extractor.py` - Add `merge_extraction_data()`

**Existing Files (Reference):**
- `app/services/document_parser.py` - Currently basic Excel parsing
- `app/services/auto_populate.py` - Deal creation logic
- `app/models.py` - DealDocument, Deal, DealUnderwriting models
