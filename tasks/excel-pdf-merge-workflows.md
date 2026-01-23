# Excel + PDF Merge Workflows

## Overview

The system supports merging PDF (deal narrative) with Excel (financial metrics) using **explicit linking only** - no automatic detection to avoid errors.

---

## Workflow 1: Upload PDF + Excel Together (Same Session)

**Use case:** You have both PDF and Excel at the same time

### Steps:

1. **Upload PDF**
   ```bash
   POST /api/documents/upload
   FormData: { file: deal.pdf }

   Response: { id: "pdf-doc-id", ... }
   ```

2. **Upload Excel**
   ```bash
   POST /api/documents/upload
   FormData: { file: model.xlsx }

   Response: { id: "excel-doc-id", ... }
   ```

3. **Extract with explicit linking**
   ```bash
   POST /api/documents/{pdf-doc-id}/extract
   Body: {
     "related_document_ids": ["excel-doc-id"]
   }

   Response: {
     "extracted_data": {
       "deal": { ... },           # From PDF
       "operators": [ ... ],       # From PDF
       "underwriting": { ... },    # From Excel (overrides PDF)
       "_extraction_metadata": {
         "method": "merged",
         "pdf_source": {...},
         "excel_source": {...}
       }
     },
     "operator_matches": [ ... ],
     "extraction_method": "merged"
   }
   ```

4. **Confirm and create deal**
   ```bash
   POST /api/documents/{pdf-doc-id}/confirm
   Body: {
     "operator_ids": ["selected-operator-id"],
     "extracted_data": { ... }
   }

   Response: {
     "success": true,
     "deal_id": "new-deal-id",
     ...
   }
   ```

---

## Workflow 2: Excel Arrives Later

**Use case:** Deal created from PDF only, Excel model received days/weeks later

### Steps:

1. **Initial: PDF only**
   ```bash
   # Upload PDF
   POST /api/documents/upload

   # Extract (no Excel available)
   POST /api/documents/{pdf-doc-id}/extract

   # Create deal
   POST /api/documents/{pdf-doc-id}/confirm

   Response: { deal_id: "deal-123", ... }
   ```

   Deal is created with PDF data only (no Excel metrics yet).

2. **Later: Excel arrives**
   ```bash
   # Upload Excel to existing deal
   POST /api/documents/deals/{deal-123}/upload
   FormData: { file: model.xlsx }

   Response: { id: "excel-doc-id", deal_id: "deal-123", ... }
   ```

   Excel is automatically linked to deal via `deal_id`.

3. **Re-extract with Excel**
   ```bash
   POST /api/documents/deals/{deal-123}/re-extract

   Response: {
     "extracted_data": {
       "deal": { ... },           # From original PDF
       "operators": [ ... ],       # From original PDF
       "underwriting": { ... },    # From NEW Excel (updated metrics!)
       "_extraction_metadata": {
         "method": "merged",
         ...
       }
     },
     "extraction_method": "merged",
     "message": "Re-extraction complete. Review data..."
   }
   ```

4. **Apply updates (manual for now)**

   User reviews the new financial metrics and updates the deal manually.

   *Future: Could add `POST /api/deals/{deal-id}/apply-re-extraction` to auto-update.*

---

## Data Merge Priority

When both PDF and Excel are present:

| Data Type | Source Priority | Example |
|-----------|----------------|---------|
| Deal Name | PDF | "100 North 3rd Street" |
| Address | PDF | "100 N 3rd St, Brooklyn, NY" |
| Sponsor | PDF | "Aperture Capital" |
| Business Plan | PDF | "Value-add repositioning..." |
| Asset Type | PDF | "Multifamily" |
| **IRR** | **Excel** | 16.53% (not PDF's 15%) |
| **Equity Multiple** | **Excel** | 2.00x |
| **Project Cost** | **Excel** | $1,685,348 |
| **All other financials** | **Excel** | Loan, equity, costs, etc. |

**Key principle:** PDF = narrative, Excel = numbers

---

## No Auto-Detection

**Important:** The system does NOT automatically link documents.

### ❌ What does NOT happen:

- Upload PDF #1 at 10:00am
- Upload Excel #1 at 10:05am
- Extract PDF #1 → **Excel is NOT automatically included**

### ✅ What you must do:

**Option A:** Explicitly link when extracting:
```bash
POST /api/documents/{pdf-id}/extract
Body: { "related_document_ids": ["excel-id"] }
```

**Option B:** Upload Excel to deal, then re-extract:
```bash
POST /api/documents/deals/{deal-id}/upload  # Upload Excel
POST /api/documents/deals/{deal-id}/re-extract  # Merge data
```

---

## Example: Real World Usage

### Scenario: New deal arrives with both PDF and Excel

```bash
# 1. Upload PDF
curl -X POST /api/documents/upload \
  -F "file=@100_N_3rd_Street.pdf"
# Response: { "id": "doc-abc", ... }

# 2. Upload Excel
curl -X POST /api/documents/upload \
  -F "file=@100_N_3rd_Model.xlsx"
# Response: { "id": "doc-xyz", ... }

# 3. Extract with explicit link
curl -X POST /api/documents/doc-abc/extract \
  -H "Content-Type: application/json" \
  -d '{"related_document_ids": ["doc-xyz"]}'
# Response: Merged data (PDF narrative + Excel financials)

# 4. Confirm and create deal
curl -X POST /api/documents/doc-abc/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "operator_ids": ["op-123"],
    "extracted_data": { ... }
  }'
# Response: { "deal_id": "deal-456", ... }
```

### Scenario: Excel arrives 2 weeks later

```bash
# Deal already exists (deal-456)

# 1. Upload Excel to existing deal
curl -X POST /api/documents/deals/deal-456/upload \
  -F "file=@Updated_Model_v2.xlsx"
# Response: { "id": "doc-new", "deal_id": "deal-456", ... }

# 2. Re-extract to merge new Excel data
curl -X POST /api/documents/deals/deal-456/re-extract
# Response: Updated extraction with new Excel metrics

# 3. Review and manually update deal records
# (or use future auto-apply endpoint)
```

---

## Error Handling

### No Excel provided when expected

```bash
POST /api/documents/{pdf-id}/extract
Body: { "related_document_ids": ["invalid-id"] }

Response: 400 Bad Request
{
  "detail": "Related document invalid-id not found or not an Excel file"
}
```

### Re-extract but no Excel on deal

```bash
POST /api/documents/deals/{deal-id}/re-extract

Response: 200 OK (but no merge)
{
  "extracted_data": { ... },  # PDF only
  "extraction_method": "text",  # Not "merged"
  "message": "No Excel found, extracted from PDF only"
}
```

---

## Future Enhancements

**Phase 3 possibilities:**

1. **Auto-apply re-extraction**
   - `POST /api/deals/{deal-id}/apply-re-extraction`
   - Automatically update deal records with new Excel data

2. **Frontend UI**
   - Drag-and-drop PDF + Excel together
   - Visual indication when documents are linked
   - Show "Excel available" badge on deals
   - "Upload Excel" button on deal detail page

3. **Batch operations**
   - Upload multiple PDFs + Excels
   - Link them via filename matching UI
   - Extract all at once

---

## Key Takeaways

✅ **Always explicit:** User must specify which Excel goes with which PDF
✅ **Two workflows:** Same-session (link on extract) or later (upload to deal, re-extract)
✅ **Excel wins:** All financial metrics from Excel override PDF
✅ **Re-extraction:** Non-destructive preview, user can review before applying
