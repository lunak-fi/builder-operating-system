# Three-Tier "Living Deal" Layout - Implementation

## Overview
Transform the DealDetail page into a Twitter/X-inspired "living deal" interface where information flows chronologically on the left (Activity Feed) and synthesizes intelligently on the right (Master Memo), with key fundamentals always visible at the top.

**Design Inspiration:** Professional version of X's live feed paradigm for investment professionals.

---

## Three-Tier Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ TIER 1: DEAL IDENTITY BAR (~48px, sticky)                      │
│ Acme Logistics · Apex Partners · US SE · Value-Add   [Stage ▼] │
├─────────────────────────────────────────────────────────────────┤
│ TIER 2: KEY METRICS STRIP (~80px, sticky)                      │
│ $42M ARR ◉ | 45% Growth ◉ | -$8M EBITDA ◉ | $200M Ask ◉        │
│ Updated from: Q3 Financials.xlsx (2 min ago)                   │
├────────────────────────────────┬────────────────────────────────┤
│ TIER 3A: ACTIVITY FEED (45%)   │ TIER 3B: MASTER MEMO (55%)     │
│ - Upload zone                  │ - Deal snapshot                │
│ - DealTimeline (chronological) │ - Investment thesis            │
│ - Document cards               │ - Key risks                    │
│ - Version grouping             │ - Open questions               │
│                                │ - Timeline/milestones          │
└────────────────────────────────┴────────────────────────────────┘
```

---

## Phase 1: UI-First Restructure (v1)

**Goal:** Build the visual three-tier structure with static/placeholder data. **No backend changes required.**

### Implementation Tasks

#### New Components Created

- [x] **1.1 DealIdentityBar.tsx** (`/src/components/deal-detail/DealIdentityBar.tsx`)
  - Compact horizontal bar (48px height, sticky top-0)
  - Display: Deal Name · Sponsor · Market · Strategy + Stage dropdown
  - Action buttons: Move Next, Pass, Edit, Delete

- [x] **1.2 KeyMetricsStrip.tsx** (`/src/components/deal-detail/KeyMetricsStrip.tsx`)
  - Horizontal metrics bar (80px height, sticky top-[48px])
  - Display: 4-5 key metrics with visual separators
  - Source line: "Updated from: [doc name] ([time ago])"
  - Mobile: Horizontal scroll with snap points

- [x] **1.3 MasterMemo.tsx** (`/src/components/deal-detail/MasterMemo.tsx`)
  - Right panel (55% width) with scrollable content
  - Sections: Deal Snapshot, Investment Thesis, Key Metrics, Sponsor Profile, Key Risks, Open Questions, Timeline
  - **v1: Uses placeholder/hardcoded content**
  - Mobile: Full width, stacked below activity feed

- [x] **1.4 ActivityFeedPanel.tsx** (`/src/components/deal-detail/ActivityFeedPanel.tsx`)
  - Left panel (45% width) wrapper around existing DealTimeline
  - Upload zone at top, chronological feed below
  - Reuses existing DealTimeline component

#### Helper Functions

- [x] **1.5 dealMetrics.ts** (`/src/lib/dealMetrics.ts`)
  - `extractKeyMetrics()` - Maps from deal.rawUnderwriting to display format
  - `getLatestDocument()` - Returns latest document for source tracking
  - `formatTimeAgo()` - Time formatting helper
  - Supports DEFAULT_METRICS configuration

#### Restructure DealDetail.tsx

- [x] **1.6 Remove tab-based layout**
  - Removed tab state and navigation UI
  - Removed tab content sections

- [x] **1.7 Add three-tier layout**
  - Tier 1: DealIdentityBar (sticky)
  - Tier 2: KeyMetricsStrip (sticky)
  - Tier 3: Two-panel split (Activity Feed + Master Memo)

- [x] **1.8 Mobile responsive design**
  - Desktop (≥1024px): Side-by-side 45/55 split
  - Tablet (768-1023px): Side-by-side 50/50 split
  - Mobile (<768px): Stacked vertical

---

## Phase 2: AI-Powered Memo Generation (v2)

**Goal:** Add AI generation for Investment Thesis, Key Risks, and Open Questions using Claude API.

### Backend Implementation

#### Memo Generator Service

- [x] **2.1 Create memo_generator.py** (`/app/services/memo_generator.py`)
  - `generate_memo_for_deal(deal_id, db)` - Main generation function
  - Fetches deal context: Deal + Operator + DealUnderwriting + Documents
  - Calls Claude API with structured prompt
  - Returns Memo object stored in database

- [x] **2.2 Build AI prompt**
  - `_build_deal_context()` - Extracts deal data and identifies missing fields
  - `_build_memo_prompt()` - Constructs prompt for Claude API
  - Prompt generates 3 sections:
    - **Investment Thesis**: 2-4 compelling bullet points on value creation
    - **Key Risks**: 4-6 specific risks tied to deal metrics
    - **Open Questions**: 5-8 actionable due diligence questions
  - Uses Claude Sonnet 4.5 model with temperature=0.3

- [x] **2.3 Error handling**
  - `MemoGenerationError` exception class
  - Graceful fallback if generation fails

#### Memo API Endpoints

- [x] **2.4 Create memos.py API** (`/app/api/memos.py`)
  - `GET /api/memos/deal/{deal_id}` - Fetch memo for a deal
  - `POST /api/memos/generate/{deal_id}` - Manually trigger generation
  - `DELETE /api/memos/{memo_id}` - Delete memo

- [x] **2.5 Register routes** (`/app/main.py`)
  - Added memo router import
  - Registered `/api/memos` routes

#### Auto-Generation Trigger

- [x] **2.6 Update documents.py** (`/app/api/documents.py`)
  - Modified `confirm_extraction()` endpoint
  - Auto-generates memo after deal creation
  - Non-blocking: logs warning if generation fails, doesn't fail request

### Frontend Implementation

#### Type Definitions

- [x] **2.7 Add Memo interface** (`/src/lib/types.ts`)
  ```typescript
  export interface Memo {
    id: string;
    deal_id: string;
    title: string | null;
    memo_type: string;
    content_markdown: string;
    generated_by: string | null;
    created_at: string;
  }
  ```

#### API Client

- [x] **2.8 Add memosAPI** (`/src/lib/api.ts`)
  - `getByDeal(dealId)` - Fetch memo
  - `generate(dealId)` - Regenerate memo
  - `delete(memoId)` - Delete memo
  - Exported in default API object

#### Data Hook Updates

- [x] **2.9 Update useDealDetail** (`/src/lib/useDealDetail.ts`)
  - Added `parseMemoMarkdown()` helper to extract 3 sections
  - Added `memoContent` to DealDetailData interface
  - Fetches memo in parallel with other data
  - Parses markdown into: investmentThesis, keyRisks, openQuestions

#### UI Component Updates

- [x] **2.10 Update MasterMemo component** (`/src/components/deal-detail/MasterMemo.tsx`)
  - Added react-markdown import and rendering
  - Added "Regenerate" button with loading state
  - **Investment Thesis**: Shows AI content or falls back to business plan
  - **Key Risks**: Shows AI content or placeholder with regenerate prompt
  - **Open Questions**: Shows AI content or placeholder
  - All sections use ReactMarkdown for rendering

- [x] **2.11 Install dependencies**
  - Installed `react-markdown` package
  - Fixed ReactMarkdown className prop issue (wrapped in div)

---

## Files Modified Summary

### Phase 1 (Frontend Only)

| File | Changes |
|------|---------|
| `/src/components/DealDetail.tsx` | Removed tabs, added three-tier layout |
| `/src/components/deal-detail/DealIdentityBar.tsx` | **NEW** - Top identity bar |
| `/src/components/deal-detail/KeyMetricsStrip.tsx` | **NEW** - Metrics display |
| `/src/components/deal-detail/MasterMemo.tsx` | **NEW** - Right panel memo |
| `/src/components/deal-detail/ActivityFeedPanel.tsx` | **NEW** - Left panel wrapper |
| `/src/lib/dealMetrics.ts` | **NEW** - Metrics helpers |

### Phase 2 (Backend + Frontend)

| File | Changes |
|------|---------|
| `/app/services/memo_generator.py` | **NEW** - AI memo generation service |
| `/app/api/memos.py` | **NEW** - Memo API endpoints |
| `/app/main.py` | Added memo router |
| `/app/api/documents.py` | Added auto-generation trigger |
| `/src/lib/types.ts` | Added Memo interface |
| `/src/lib/api.ts` | Added memosAPI client |
| `/src/lib/useDealDetail.ts` | Added memo fetching and parsing |
| `/src/components/deal-detail/MasterMemo.tsx` | Added AI content display |
| `package.json` | Added react-markdown dependency |

---

## Testing Checklist

### Phase 1 Testing (Completed ✅)

- [x] **Load existing deal**
  - Three tiers render correctly
  - Identity bar shows deal info
  - Metrics strip displays 4-5 metrics
  - Activity feed shows documents
  - Master memo shows placeholder content

- [x] **Action buttons work**
  - Move Next, Pass, Edit, Delete functional
  - No regressions from tab removal

- [x] **Mobile responsive**
  - Identity bar abbreviated
  - Metrics scroll horizontally
  - Feed and memo stack vertically

### Phase 2 Testing (Completed ✅)

- [x] **Auto-generation on deal creation**
  - Upload new deal document
  - Confirm extraction and create deal
  - Verify memo auto-generated in database
  - Check backend logs for success message

- [x] **Manual regeneration**
  - Navigate to existing deal detail page
  - Click "Regenerate" button
  - Verify loading spinner appears
  - Verify page reloads with new AI content

- [x] **AI content quality**
  - Investment Thesis: Generated from business plan
  - Key Risks: 4-6 specific risks tied to deal metrics (Example: "Short-term rental execution risk as 25% of revenue depends on hospitality operations...")
  - Open Questions: 5-8 actionable questions (Example: "Investigate Watchung Capital's track record specifically in Des Moines multifamily...")
  - Content is specific and data-driven, not generic

- [x] **Frontend display**
  - Markdown renders correctly
  - Bold formatting works
  - Bullet points display properly
  - Fallback content works when no memo

**Testing Notes:**
- ✅ Manual regeneration works perfectly
- ✅ Auto-generation confirmed working (all AI generated content)
- ⚠️ **Improvement opportunity:** Add stage-awareness (committed deals should have different risks/questions focused on portfolio monitoring vs. pre-investment due diligence)

---

## Current Status

### Phase 1: Three-Tier UI
✅ **COMPLETE** - Committed and pushed to GitHub

**Commit:** 8545daf - "Implement Phase 1: Three-tier living deal layout"
- 6 files changed (681 insertions, 352 deletions)
- All components created and integrated
- Mobile responsive design implemented
- No regressions in existing functionality

### Phase 2: AI Memo Generation
✅ **COMPLETE** - Tested and working

**Implementation complete:**
- Backend memo generation service with Claude API integration
- Frontend memo display with "Regenerate" button
- Auto-generation trigger on deal creation
- react-markdown integration with proper formatting
- Manual regeneration functionality

**Testing results:**
- ✅ Auto-generation works on new deal uploads
- ✅ Manual regeneration works via "Regenerate" button
- ✅ AI generates specific, data-driven content (not generic)
- ✅ Markdown renders correctly with bullet points and bold text
- ⚠️ Future improvement: Add stage-awareness for different deal statuses

---

## Cost & Performance

**Claude API Costs:**
- ~3,500 tokens per memo = $0.01-0.02 per generation
- 100 deals/month = $1-2/month (negligible)

**Performance:**
- Memo generation: 5-10 seconds
- Auto-generation runs in background (doesn't block deal creation)
- Frontend loads memo in parallel with other data

---

## Conversation Transcripts (Phase 1)
✅ **COMPLETE** - Implemented and working

**Implementation complete:**
- Backend transcript extractor service with Claude API integration
- Automatic AI extraction of key decisions, action items, and risks
- Transcript-specific metadata (topic, conversation_date) storage
- Frontend TranscriptCard component with teal styling and insight badges
- Frontend TranscriptViewer slide-over panel
- Regenerate insights functionality
- Processing status indicators

**What works:**
- Upload .txt or .md files as transcripts to existing deals
- Automatic AI extraction runs in background after parsing
- Transcripts display in Activity Feed with distinctive styling
- Click transcript to open slide-over viewer with AI insights
- Insights show: key decisions, action items (with assignees), risks, sentiment
- Regenerate insights manually via button
- Download original transcript file
- Escape key closes viewer
- Mobile responsive design

**Testing results:**
- ✅ Backend AI extraction working with Claude API
- ✅ Frontend components rendering correctly
- ✅ Metadata storage in JSONB field
- ✅ Regenerate insights endpoint functional

---

## Future Enhancements

**Phase 2 - Enhanced Transcript Integration:**

1. **Master Memo Integration**
   - ✅ **COMPLETE** - Implemented and tested (2026-01-22)
   - ✅ "Key Conversations" section: Summarizes conversations with dates, topics, and sentiment
   - ✅ "Open Items" section: Aggregated action items from all transcripts with assignees and priorities
   - ✅ Color-coded priority indicators (🔴 High, 🟡 Medium, 🟢 Low)
   - ✅ Conditional rendering (sections only appear when transcripts exist)
   - ✅ Works for both early-stage and committed deal formats
   - ⚠️ Future enhancement: Source attribution links to jump to specific transcripts
   - ⚠️ Future enhancement: In-transcript highlighting when clicking insights
   - **Backend commit:** ab56236
   - **Frontend commit:** 57e2625
   - **Tested on:** Frog Alley deal with conversation transcript

2. **Enhanced Transcript Features**
   - **Priority:** Medium
   - [ ] Filter bar for Activity Feed (type, date, has insights)
   - [ ] Upload dialog with transcript-specific fields (topic, participants, date/time)
   - [ ] Participant management and tagging
   - [ ] Transcript metadata editing UI

**Phase 3 - Advanced Features:**

3. **Multiple Sponsors Per Deal**
   - ✅ **COMPLETE** - Implemented and tested
   - **Problem:** Some deals have 2+ sponsors (e.g., The Ark has Aptitude Development + The Alley Family Office; 2910 North Arthur Ashe has AIP + PointsFive)
   - **Implementation complete:**
     - ✅ Created `deal_operators` junction table (many-to-many relationship)
     - ✅ Updated LLM extraction to capture multiple sponsors from documents
     - ✅ Modified auto-populate logic to create/link multiple operators
     - ✅ Updated frontend to display multiple sponsors (DealIdentityBar, sponsor cards)
     - ✅ **NEW:** Added API endpoints to manually add/remove/update sponsors on deals
   - **API Endpoints (2026-01-22):**
     - `POST /api/deals/{deal_id}/operators` - Add sponsor to deal
     - `DELETE /api/deals/{deal_id}/operators/{operator_id}` - Remove sponsor from deal
     - `PUT /api/deals/{deal_id}/operators/{operator_id}` - Update primary sponsor status
   - **Features:**
     - Automatic primary sponsor management (only one primary at a time)
     - Duplicate prevention (can't add same sponsor twice)
     - Business validation (must keep at least one sponsor per deal)
   - **Commit:** af505f5 - "Complete Multiple Sponsors feature - add sponsor management API endpoints"

4. **Advanced Transcript Features**
   - **Problem:** Need to upload and track conversation transcripts (sponsor calls, IC meetings, site visits) for each deal
   - [ ] Cross-transcript search functionality
   - [ ] Action item assignment and tracking (assignee, due date, status)
   - [ ] Export and reporting for transcripts and action items
   - [ ] Bulk operations for action items

5. **Stage-Aware Memo Generation**
   - **Problem:** Memos don't adapt content based on deal stage (new vs. committed deals need different risks/questions)
   - **Enhancement:** Modify AI prompt based on deal status
     - **New deals** (Received/Screening): Focus on investment decision risks, sponsor verification, due diligence questions
     - **Committed deals** (Invested/Portfolio): Focus on portfolio monitoring, operational performance, exit strategy
   - **Implementation:** Update `_build_memo_prompt()` in memo_generator.py to include deal status context
   - **Priority:** Medium - Improves memo relevance and usefulness

6. **Configurable Metrics Dashboard**
   - User selects which metrics to display
   - Pin/unpin metrics
   - Metric history timeline view

7. **Collaborative Memo Editing**
   - Rich text editor for memo sections
   - Track changes / version history
   - Comments on specific sections

8. **Smart Metric Updates**
   - Detect metric changes when document uploaded
   - Show diff view before accepting
   - Auto-update memo content with highlights

9. **Memo Version History**
   - Store multiple memo versions
   - Compare versions side-by-side
   - Restore previous versions

10. **Multi-Document Context**
    - Analyze all documents, not just latest
    - Extract insights from document changes over time
    - Streaming generation (show sections as they generate)

---

## Architecture Notes

### Data Flow: Auto-Generation
1. User uploads document → `POST /api/documents/upload`
2. Document parsed → Extraction confirmed → Deal created
3. `documents.py` calls `generate_memo_for_deal(deal_id, db)`
4. Memo generator fetches context, calls Claude API
5. Memo stored in database with markdown content
6. Frontend fetches memo when loading deal detail page

### Data Flow: Manual Regeneration
1. User clicks "Regenerate" button
2. Frontend calls `POST /api/memos/generate/{deal_id}`
3. Backend deletes old memo, generates new one
4. Page reloads to show fresh content

### Markdown Parsing
- Backend stores raw markdown with section headers
- Frontend uses regex to extract three sections:
  - `## Investment Thesis\n...`
  - `## Key Risks\n...`
  - `## Open Questions\n...`
- react-markdown renders each section independently

---

## Key Principles

1. **Simplicity First:** Minimal changes to data layer, reuse existing components
2. **UI-First Approach:** Visual transformation before backend integration
3. **No Regressions:** Preserve all existing functionality
4. **Mobile Responsive:** Design works on all screen sizes
5. **Phased Rollout:** v1 = UI, v2 = Backend, v3 = AI enhancements
6. **Always Test Before Commit:** Never commit untested code

---

## Documentation

**Project rules:** `/Users/kennethluna/ws/CLAUDE.md`
- Rule #7: ALWAYS test changes before committing. After testing is successful, commit and push automatically without asking for permission.

**Implementation plan:** Located in previous session transcript
- Full detailed plan with all specifications
- Component designs and API contracts
- Testing strategy and success criteria
