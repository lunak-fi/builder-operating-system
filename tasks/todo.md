# Builder Operating System - Project Status & Roadmap

**Last updated:** 2026-02-18

---

## Platform Overview

- **Backend**: FastAPI + PostgreSQL (hosted on Railway)
- **Frontend**: Next.js 16 + React 19 (hosted on Vercel)
- **AI**: Claude (Anthropic) for document extraction, memo generation, transcript analysis
- **Auth**: Clerk (OAuth + JWT)
- **Email**: SendGrid Inbound Parse for email forwarding

### Database Schema (10 tables)
Operators, Principals, Deals, DealOperators (junction), DealDocuments (with versioning), DealUnderwriting, Memos, DealStageTransitions, DealNotes, PendingEmails + PendingEmailAttachments

---

## Completed Features

### Core Platform
| Feature | Description |
|---------|-------------|
| **Deal Pipeline** | 8-stage workflow (inbox -> committed/passed) with filtering, sorting, search |
| **Document Processing** | PDF/Excel upload, AI extraction, version control |
| **AI Data Extraction** | Claude extracts deal info, financials, sponsor data from documents |
| **Financial Model Analysis** | Excel parsing with fuzzy sheet matching, metric extraction |
| **Sponsor Management** | CRUD + search + deal associations |
| **Dashboard Analytics** | KPIs, charts, velocity metrics, contextual insights |
| **Geocoding/MSA Mapping** | Census API + shapefile-based market standardization |

### Three-Tier Living Deal UI
| Feature | Description |
|---------|-------------|
| **DealIdentityBar** | Sticky top bar with deal name, sponsor, market, strategy, stage dropdown |
| **KeyMetricsStrip** | Horizontal metrics bar with 4-5 key metrics, source tracking |
| **ActivityFeedPanel** | Left panel (45%) with upload zone and chronological document feed |
| **MasterMemo** | Right panel (55%) with AI-generated investment analysis |
| **Mobile Responsive** | Desktop split, tablet 50/50, mobile stacked vertical |

### AI Memo Generation
| Feature | Description |
|---------|-------------|
| **Auto-generation** | Memo generated automatically when deal is created |
| **Manual regeneration** | "Regenerate" button for on-demand refresh |
| **Stage-aware prompts** | Different analysis for early-stage vs committed deals |
| **Sections** | Investment Thesis, Key Risks, Open Questions (early) / Execution Status, Risks, Action Items (committed) |

### Transcript Processing
| Feature | Description |
|---------|-------------|
| **Upload & parsing** | Upload .txt/.md transcripts to deals |
| **AI insight extraction** | Key decisions, action items (with assignees), risks, sentiment |
| **Participant extraction** | AI identifies participants from transcript content |
| **TranscriptCard** | Distinctive teal styling with insight badges in activity feed |
| **TranscriptViewer** | Slide-over panel with full text and AI insights |
| **Master Memo integration** | "Key Conversations" and "Open Items" sections from transcripts |

### Authentication (Clerk)
| Feature | Description |
|---------|-------------|
| **Frontend auth** | Clerk provider, protected routes, sign-in/sign-up pages |
| **Backend auth** | JWT validation middleware on all API endpoints |
| **Webhook bypass** | Inbound email webhooks excluded from auth (external service calls) |

### Email Forwarding (SendGrid)
| Feature | Description |
|---------|-------------|
| **Inbound parsing** | SendGrid webhook receives forwarded emails |
| **Pending email inbox** | Emails land in inbox for review before deal creation |
| **PDF/Excel attachment parsing** | Attachments parsed before AI extraction (two-phase workflow) |
| **AI extraction from attachments** | Parsed attachment text included in AI deal extraction |
| **Link to existing deal** | Option to link email to existing deal instead of creating new |
| **Deal search** | Search endpoint for deal autocomplete when linking |
| **Confirm/reject workflow** | Review extracted data, select operators, create or link deal |

### Multi-Asset Type Support
| Feature | Description |
|---------|-------------|
| **asset_type_details JSONB** | Flexible per-type fields on deals |
| **Asset type templates** | Multifamily, Mixed-Use, Retail, Industrial, Office |
| **Extraction prompts** | AI recognizes asset-type-specific metrics |
| **Conditional UI** | Relevant fields displayed per asset type |

### Multi-Operator Deals
| Feature | Description |
|---------|-------------|
| **Junction table** | Many-to-many deal-operator relationship |
| **Primary sponsor** | One primary designation per deal |
| **API endpoints** | Add/remove/update sponsors on deals |
| **LLM extraction** | AI captures multiple sponsors from documents |

### Deal Notes
| Feature | Description |
|---------|-------------|
| **Notes table** | deal_notes with author, note_type, content |
| **CRUD endpoints** | Create, read, update, delete notes |
| **UI component** | Notes section in deal detail |

### Document Management
| Feature | Description |
|---------|-------------|
| **Document deletion** | Delete button with confirmation dialog on all doc types |
| **Document date picker** | Optional date field in upload dialogs |
| **Chronological ordering** | Documents ordered by event date, not upload time |

---

## Remaining Roadmap

### Near-Term

| Feature | Priority | Description |
|---------|----------|-------------|
| **Activity Feed filters** | Medium | Filter bar for type, date, has insights |
| **Transcript metadata editing** | Medium | Edit topic, date, participants after upload |
| **Deals page design polish** | Medium | Visual refinements to deals list page |

### Medium-Term

| Feature | Priority | Description |
|---------|----------|-------------|
| **Cross-transcript search** | Medium | Search across all transcripts for a deal |
| **Action item tracking** | Medium | Assignee, due date, status on action items |
| **Configurable metrics dashboard** | Low | User selects which metrics to display |
| **Source data integration** | Low | Google Drive / Dropbox watched folder sync |

### Long-Term

| Feature | Priority | Description |
|---------|----------|-------------|
| **Collaborative memo editing** | Low | Rich text editor, version history, comments |
| **Multi-document AI context** | Low | Analyze changes across document versions |
| **SMS/text thread capture** | Low | Twilio integration for forwarded texts |
| **Export & reporting** | Low | PDF export of memos, deal summaries |
| **Mobile app** | Low | After core features stable |

---

## Architecture Notes

### Email Inbound Flow
```
User forwards email -> SendGrid webhook -> /webhooks/inbound-email
  -> Parse sender, subject, body, attachments
  -> Save PendingEmail + PendingEmailAttachments
  -> Has parseable attachments?
     YES -> Parse each (PDF/Excel) -> Last one triggers AI extraction
     NO  -> Trigger AI extraction immediately
  -> AI extracts deal data from email body + attachment text
  -> User reviews in inbox -> Confirm (create/link deal) or Reject
```

### Document Upload Flow
```
User uploads file -> POST /api/documents/upload
  -> Parse document (PDF/Excel/text)
  -> AI extracts deal data
  -> User confirms extraction -> Deal created
  -> Memo auto-generated in background
```

### Key File Paths
- Backend entry: `app/main.py`
- API routes: `app/api/` (deals, documents, memos, operators, pending_emails, webhooks)
- AI services: `app/services/` (llm_extractor, memo_generator, transcript_extractor, document_parser, pdf_extractor, excel_analyst)
- Models: `app/models/`
- Migrations: `migrations/versions/`
- Frontend pages: `src/app/` (dashboard, deals, operators, inbox, sign-in, sign-up)
- Frontend components: `src/components/` (deal-detail/, ui/)

### Local Development
- See `tasks/local-dev-setup.md` for full setup instructions
- Backend: `uvicorn app.main:app --reload --port 8000`
- Frontend: `cd builder-operating-system-ui && npm run dev`
- Database: PostgreSQL 15 via Postgres.app (stop Homebrew's postgresql@14 first)
