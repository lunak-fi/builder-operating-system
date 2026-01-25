# Dashboard Quick Wins - Phase 1

## Goal
Transform the dashboard from a static summary view to an interactive decision-making platform.

**Target:** Maximum visual impact with minimal backend changes.

---

## Current State (Baseline)

**What Users See:**
- 6 static metric cards in a 2×3 grid
- 2 charts (market distribution + deal flow) - not interactive
- Recent activity table - no quick actions
- No activity indicators or context

**User Feedback:** "Feels a bit static"

---

## Implementation Tasks

### 1. Interactive Chart Filtering ⭐ Start Here
**Impact:** HIGH | **Effort:** LOW | **Status:** 🔜 Not started

**What:**
- Click market bars → filter recent activity table to that market
- Click deal flow bars → filter to that stage
- Show active filter indicator
- Add "Clear filters" button

**Implementation:**
```tsx
// In Dashboard.tsx
const [activeMarketFilter, setActiveMarketFilter] = useState<string | null>(null);
const [activeStageFilter, setActiveStageFilter] = useState<string | null>(null);

const filteredDeals = recentDeals.filter(deal => {
  if (activeMarketFilter && deal.state !== activeMarketFilter) return false;
  if (activeStageFilter && deal.status !== activeStageFilter) return false;
  return true;
});

// Pass to MarketChart
<MarketChart
  data={marketData}
  activeFilter={activeMarketFilter}
  onFilterClick={(market) => setActiveMarketFilter(market)}
/>
```

**Files:**
- [ ] `src/components/Dashboard.tsx` - Add filter state
- [ ] `src/components/MarketChart.tsx` - Add click handlers
- [ ] `src/components/DealFlowChart.tsx` - Add click handlers
- [ ] `src/components/RecentActivityTable.tsx` - Show filter indicator

**Success Criteria:**
- ✅ Clicking market bar filters table to that market
- ✅ Clicking stage bar filters table to that stage
- ✅ Active filter highlighted in chart
- ✅ Clear filters button works
- ✅ No backend changes required

---

### 2. Activity Indicators
**Impact:** HIGH | **Effort:** LOW | **Status:** 🔜 Not started

**What:**
- Green pulse dot for deals with activity in last hour
- "NEW" badge for deals created today
- Yellow highlight for recently updated deals

**Implementation:**
```tsx
// In RecentActivityTable.tsx
const isNew = (createdAt: string) => {
  const created = new Date(createdAt);
  const today = new Date();
  return created.toDateString() === today.toDateString();
};

const isActive = (updatedAt: string) => {
  const updated = new Date(updatedAt);
  const hourAgo = new Date(Date.now() - 60 * 60 * 1000);
  return updated > hourAgo;
};

// In table row
<div className="flex items-center gap-2">
  {isActive(deal.updated_at) && (
    <div className="relative">
      <div className="w-2 h-2 bg-green-500 rounded-full" />
      <div className="absolute inset-0 bg-green-500 rounded-full animate-ping opacity-75" />
    </div>
  )}
  {deal.name}
  {isNew(deal.created_at) && (
    <span className="text-[10px] px-1.5 py-0.5 bg-yellow-400 text-black rounded font-semibold">
      NEW
    </span>
  )}
</div>
```

**Files:**
- [ ] `src/components/RecentActivityTable.tsx` - Add indicators

**Success Criteria:**
- ✅ Green pulse dot appears on deals updated in last hour
- ✅ NEW badge appears on deals created today
- ✅ Animations work smoothly

---

### 3. Quick Action Menus
**Impact:** HIGH | **Effort:** MEDIUM | **Status:** 🔜 Not started

**What:**
- Three-dot menu on each table row
- Quick actions: Move Next, Pass, View Deal
- No navigation required for stage changes

**Implementation:**
```tsx
// In RecentActivityTable.tsx
import { MoreHorizontal } from 'lucide-react';

<DropdownMenu>
  <DropdownMenuTrigger>
    <button className="p-1 hover:bg-gray-100 rounded">
      <MoreHorizontal size={16} />
    </button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    <DropdownMenuItem onClick={() => handleMoveNext(deal.id)}>
      Move to Next Stage
    </DropdownMenuItem>
    <DropdownMenuItem onClick={() => handlePass(deal.id)}>
      Pass on Deal
    </DropdownMenuItem>
    <DropdownMenuItem onClick={() => onViewDeal(deal.id)}>
      View Details
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

**Files:**
- [ ] `src/components/RecentActivityTable.tsx` - Add dropdown menus
- [ ] Check if dropdown components exist, install if needed

**Backend:**
- No changes needed (APIs already exist)

**Success Criteria:**
- ✅ Three-dot menu appears on hover/click
- ✅ Move Next action updates deal stage
- ✅ Pass action marks deal as passed
- ✅ Table refreshes after actions
- ✅ Optimistic UI updates (instant feedback)

---

### 4. Contextual Insights Panel
**Impact:** HIGH | **Effort:** MEDIUM | **Status:** 🔜 Not started

**What:**
- Dismissible insight card showing actionable intelligence
- Examples:
  - "⚠️ 3 deals have been in Due Diligence > 30 days"
  - "🔥 Austin market is heating up: +40% this month"
  - "✅ You closed 2 deals this week"

**Implementation:**
```tsx
// In Dashboard.tsx
const getInsights = () => {
  const insights = [];

  // Check for stalled deals
  const stalledDeals = recentDeals.filter(deal => {
    if (deal.status !== 'due_diligence') return false;
    const daysSince = (Date.now() - new Date(deal.updated_at).getTime()) / (1000 * 60 * 60 * 24);
    return daysSince > 30;
  });

  if (stalledDeals.length > 0) {
    insights.push({
      type: 'warning',
      title: `${stalledDeals.length} deals need attention`,
      message: `${stalledDeals.map(d => d.name).join(', ')} have been in due diligence for over 30 days.`
    });
  }

  // Add more insight logic...

  return insights;
};

<div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded-r-lg">
  <div className="flex items-start gap-3">
    <AlertCircle className="text-blue-600" />
    <div>
      <h4 className="text-sm font-semibold text-blue-900">
        {insight.title}
      </h4>
      <p className="text-sm text-blue-700 mt-1">
        {insight.message}
      </p>
    </div>
  </div>
</div>
```

**Files:**
- [ ] `src/components/Dashboard.tsx` - Add insights logic

**Backend:**
- No changes needed (uses existing deal data)

**Success Criteria:**
- ✅ Insights panel appears when relevant
- ✅ Stalled deals insight works (>30 days in stage)
- ✅ Panel is dismissible
- ✅ Multiple insights can be shown
- ✅ Insights are data-driven, not generic

---

## Dependencies

**Frontend Packages:**
- Existing UI components (buttons, dropdowns, icons)
- No new packages required for Phase 1

**Backend:**
- No changes required (all APIs exist)

---

## Testing Checklist

### Interactive Filtering
- [ ] Click market "Texas" → table shows only Texas deals
- [ ] Click stage "Due Diligence" → table shows only DD deals
- [ ] Click same filter again → toggles off
- [ ] Click different filter → replaces previous
- [ ] Clear filters button → shows all deals
- [ ] Visual highlight on active filter

### Activity Indicators
- [ ] Upload new deal → NEW badge appears
- [ ] Update existing deal → green pulse appears
- [ ] Wait 1 hour → pulse disappears
- [ ] Wait 1 day → NEW badge disappears

### Quick Actions
- [ ] Three-dot menu appears on table row
- [ ] Click "Move Next" → stage updates
- [ ] Click "Pass" → deal marked as passed
- [ ] Click "View Details" → navigates to deal
- [ ] Table refreshes after action
- [ ] Loading states work

### Insights
- [ ] Stalled deals insight appears when deals >30 days old
- [ ] Insight is data-specific (shows deal names)
- [ ] Insight can be dismissed
- [ ] No insights when none applicable

---

## Success Metrics

**Quantitative:**
- Dashboard engagement time increases
- Clicks per session on interactive elements
- Reduced navigation to accomplish common tasks

**Qualitative:**
- Dashboard feels "alive" and responsive
- Users can answer "What needs my attention?" quickly
- Common actions (move stage, pass) require fewer clicks

---

## Implementation Order

1. **Start:** Interactive Chart Filtering (easy win, high impact)
2. **Next:** Activity Indicators (visual polish, easy)
3. **Then:** Quick Action Menus (functionality boost)
4. **Finally:** Contextual Insights (intelligence layer)

**Estimated effort:** 1-2 days for all 4 features

---

## Current Status

### Phase 1: Quick Wins - COMPLETED ✅
- [x] Feature 1: Interactive Chart Filtering
- [x] Feature 2: Activity Indicators (NEW badges, pulse dots)
- [x] Feature 3: Quick Action Menus (three-dot menu on table rows)
- [x] Feature 4: Contextual Insights Panel (stalled deals, recent commits, hot markets)

### Additional Improvements - ALL COMPLETED ✅
- [x] Asymmetric Hero Metric Layout (2 large hero metrics + 4 secondary)
- [x] Our Capital Deployed vs Total Deal Equity separation
- [x] Backend: Added `our_investment` field to track actual investments
- [x] Inline Deal Previews on Hover (HoverCard with underwriting metrics)
- [x] Command Palette (Cmd+K with fuzzy search, quick actions, reset insights)
- [x] Enhanced Market Visualizations (show total equity instead of deal count)
- [x] Deal Velocity Metrics (stage transitions tracking, conversion rates)

### Backend Enhancements Completed ✅
- [x] Added `DealStageTransition` model to track historical stage changes
- [x] Updated all deal status change endpoints to record transitions
- [x] Created `/api/deals/velocity-metrics` endpoint
- [x] Added migration for `deal_stage_transitions` table
- [x] Fixed route ordering (velocity-metrics before /{deal_id})

**Started:** Jan 23, 2026
**Phase 1 Completed:** Jan 24, 2026
**All Features Completed:** Jan 25, 2026

---

## Files to Modify

### Primary Files
- `src/components/Dashboard.tsx` - Filter state, insights logic
- `src/components/MarketChart.tsx` - Click handlers
- `src/components/DealFlowChart.tsx` - Click handlers
- `src/components/RecentActivityTable.tsx` - Indicators, action menus

### No Changes Needed
- Backend APIs (all exist)
- Database schema
- Data fetching hooks (useDashboardData already has data we need)

---

## Future Enhancements (Phase 2+)

Not included in this task:
- Sparkline trends (requires historical metrics API)
- Command palette (Cmd+K)
- WebSocket real-time updates
- Deal velocity metrics
- Asymmetric hero metric layout

These are deferred to Phase 2.
