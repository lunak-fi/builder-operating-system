#!/usr/bin/env tsx

import * as fs from 'fs/promises';
import * as path from 'path';

// ============================================================================
// Type Definitions
// ============================================================================

interface Phase {
  name: string;
  description: string;
  status: 'complete' | 'active' | 'planned' | 'backlog';
  tasksTotal: number;
  tasksComplete: number;
  rawSection: string;
}

type KanbanColumn = 'Backlog' | 'Planned' | 'Active' | 'Done';

// ============================================================================
// Core Parsing Functions
// ============================================================================

/**
 * Extract all high-level phases from todo.md
 */
function parsePhases(todoContent: string): Phase[] {
  const phases: Phase[] = [];

  // Match section headers like "## Phase 1: ...", "## Conversation Transcripts", "## Future Enhancements"
  const sectionRegex = /^## (.+?)$/gm;
  const matches = [...todoContent.matchAll(sectionRegex)];

  for (let i = 0; i < matches.length; i++) {
    const match = matches[i];
    const sectionName = match[1].trim();
    const startIdx = match.index!;
    const endIdx = i < matches.length - 1 ? matches[i + 1].index! : todoContent.length;
    const rawSection = todoContent.slice(startIdx, endIdx);

    // Skip utility sections
    if (shouldSkipSection(sectionName)) {
      continue;
    }

    // Special handling for "Future Enhancements" - parse numbered sub-items
    if (sectionName === 'Future Enhancements') {
      const subPhases = parseFutureEnhancements(rawSection);
      phases.push(...subPhases);
      continue;
    }

    // Extract description (first paragraph after header)
    const description = extractDescription(rawSection);

    // Count tasks
    const taskCheckboxes = rawSection.match(/- \[(x| )\]/g) || [];
    const tasksTotal = taskCheckboxes.length;
    const tasksComplete = taskCheckboxes.filter(cb => cb.includes('[x]')).length;

    // Determine status
    const status = categorizePhase(rawSection, sectionName, tasksTotal, tasksComplete);

    phases.push({
      name: cleanPhaseName(sectionName),
      description,
      status,
      tasksTotal,
      tasksComplete,
      rawSection
    });
  }

  return phases;
}

/**
 * Parse numbered sub-items from "Future Enhancements" section
 */
function parseFutureEnhancements(rawSection: string): Phase[] {
  const phases: Phase[] = [];

  // Match numbered items like "1. **Title**" or "5. **Title**"
  const itemRegex = /^\d+\.\s+\*\*(.+?)\*\*/gm;
  const matches = [...rawSection.matchAll(itemRegex)];

  for (let i = 0; i < matches.length; i++) {
    const match = matches[i];
    const itemName = match[1].trim();
    const startIdx = match.index!;
    const endIdx = i < matches.length - 1 ? matches[i + 1].index! : rawSection.length;
    const itemSection = rawSection.slice(startIdx, endIdx);

    // Extract description
    const description = extractDescription(itemSection);

    // Count tasks
    const taskCheckboxes = itemSection.match(/- \[(x| )\]/g) || [];
    const tasksTotal = taskCheckboxes.length;
    const tasksComplete = taskCheckboxes.filter(cb => cb.includes('[x]')).length;

    // Determine status
    const status = categorizePhase(itemSection, itemName, tasksTotal, tasksComplete);

    phases.push({
      name: itemName,
      description,
      status,
      tasksTotal,
      tasksComplete,
      rawSection: itemSection
    });
  }

  return phases;
}

/**
 * Skip non-phase sections
 */
function shouldSkipSection(sectionName: string): boolean {
  const skipSections = [
    'Overview',
    'Three-Tier Layout Structure',
    'Files Modified Summary',
    'Testing Checklist',
    'Current Status',
    'Cost & Performance',
    'Architecture Notes',
    'Key Principles',
    'Documentation'
  ];

  return skipSections.some(skip => sectionName.includes(skip));
}

/**
 * Extract brief description from section
 */
function extractDescription(rawSection: string): string {
  const MAX_LENGTH = 120;

  // Look for **Goal:** pattern - stop at next section marker
  const goalMatch = rawSection.match(/\*\*Goal:\*\*\s*(.+?)(?=\n\n|\n\s*[-*]|\*\*[A-Z]|$)/s);
  if (goalMatch) {
    return truncateDescription(goalMatch[1].trim().replace(/\n/g, ' '), MAX_LENGTH);
  }

  // Look for **Problem:** pattern - stop at next section marker
  const problemMatch = rawSection.match(/\*\*Problem:\*\*\s*(.+?)(?=\n\s*[-*]|\*\*[A-Z]|\n\n|$)/s);
  if (problemMatch) {
    return truncateDescription(problemMatch[1].trim().replace(/\n/g, ' '), MAX_LENGTH);
  }

  // Look for **Note:** pattern
  const noteMatch = rawSection.match(/\*\*Note:\*\*\s*(.+?)(?=\n\s*[-*]|\*\*[A-Z]|\n\n|$)/s);
  if (noteMatch) {
    return truncateDescription(noteMatch[1].trim().replace(/\n/g, ' '), MAX_LENGTH);
  }

  // Look for **Implementation complete:** pattern - take first bullet point
  const implMatch = rawSection.match(/\*\*Implementation complete:\*\*\s*\n\s*-\s*(.+?)(?=\n|$)/);
  if (implMatch) {
    return truncateDescription(implMatch[1].trim(), MAX_LENGTH);
  }

  // Look for **What works:** pattern
  const worksMatch = rawSection.match(/\*\*What works:\*\*\s*\n\s*-\s*(.+?)(?=\n|$)/);
  if (worksMatch) {
    return truncateDescription(worksMatch[1].trim(), MAX_LENGTH);
  }

  // Extract first 2-3 bullet points and concatenate
  const bulletMatches = rawSection.match(/^\s*-\s*(.+?)$/gm);
  if (bulletMatches && bulletMatches.length > 0) {
    const bullets = bulletMatches
      .slice(0, 3)
      .map(b => {
        // Remove leading dash, checkbox, and emoji markers
        let cleaned = b.replace(/^\s*-\s*/, '')
                       .replace(/\s*\[.\]\s*/, '')
                       .replace(/^✅\s*/, '')
                       .replace(/^⚠️\s*/, '')
                       .replace(/^\*\*COMPLETE\*\*\s*-?\s*/, '')
                       .trim();
        return cleaned;
      })
      .filter(b => b.length > 10 && !b.startsWith('**Backend') && !b.startsWith('**Frontend') && !b.startsWith('**Tested'));

    if (bullets.length > 0) {
      const combined = bullets.join('; ');
      return truncateDescription(combined, MAX_LENGTH);
    }
  }

  // Fall back to first meaningful paragraph
  const lines = rawSection.split('\n').slice(1); // Skip header line
  for (const line of lines) {
    const trimmed = line.trim();
    // Skip empty lines, headers, and markers
    if (trimmed &&
        !trimmed.startsWith('**') &&
        !trimmed.startsWith('-') &&
        !trimmed.startsWith('#') &&
        !trimmed.startsWith('✅') &&
        trimmed.length > 20) {
      return truncateDescription(trimmed, MAX_LENGTH);
    }
  }

  return 'Planned feature';
}

/**
 * Truncate description to max length with ellipsis
 */
function truncateDescription(text: string, maxLength: number): string {
  // Clean up extra whitespace
  text = text.replace(/\s+/g, ' ').trim();

  if (text.length <= maxLength) {
    return text;
  }

  // Try to break at sentence end
  const truncated = text.substring(0, maxLength);
  const lastPeriod = truncated.lastIndexOf('.');
  const lastComma = truncated.lastIndexOf(',');

  if (lastPeriod > maxLength * 0.6) {
    return text.substring(0, lastPeriod + 1);
  } else if (lastComma > maxLength * 0.7) {
    return text.substring(0, lastComma) + '...';
  } else {
    // Break at last space
    const lastSpace = truncated.lastIndexOf(' ');
    if (lastSpace > maxLength * 0.6) {
      return text.substring(0, lastSpace) + '...';
    }
    return truncated + '...';
  }
}

/**
 * Clean phase name for display
 */
function cleanPhaseName(name: string): string {
  // Remove version suffixes like "(v1)", "(v2)"
  let cleaned = name.replace(/\s*\([v\d]+\)\s*$/, '');

  // Remove "Phase N:" prefix for cleaner display
  cleaned = cleaned.replace(/^Phase \d+:\s*/, '');

  return cleaned.trim();
}

/**
 * Categorize phase into Kanban column
 */
function categorizePhase(
  rawSection: string,
  sectionName: string,
  tasksTotal: number,
  tasksComplete: number
): 'complete' | 'active' | 'planned' | 'backlog' {
  // Check for completion marker
  if (rawSection.includes('✅ **COMPLETE**')) {
    return 'complete';
  }

  // Future Enhancements go to backlog
  if (sectionName.includes('Future Enhancements')) {
    return 'backlog';
  }

  // No tasks defined = backlog
  if (tasksTotal === 0) {
    return 'backlog';
  }

  // All tasks complete but no COMPLETE marker = likely complete
  if (tasksComplete === tasksTotal) {
    return 'complete';
  }

  // Mix of complete and incomplete = active
  if (tasksComplete > 0 && tasksComplete < tasksTotal) {
    return 'active';
  }

  // Has tasks but none complete = planned
  if (tasksComplete === 0 && tasksTotal > 0) {
    return 'planned';
  }

  // Default to backlog
  return 'backlog';
}

// ============================================================================
// Kanban Generation
// ============================================================================

/**
 * Generate Kanban markdown from phases
 */
function generateKanbanMarkdown(phases: Phase[]): string {
  // Group phases by column
  const columns: Record<KanbanColumn, Phase[]> = {
    'Backlog': [],
    'Planned': [],
    'Active': [],
    'Done': []
  };

  for (const phase of phases) {
    const column = statusToColumn(phase.status);
    columns[column].push(phase);
  }

  // Build markdown
  const lines: string[] = [];

  // Frontmatter
  lines.push('---');
  lines.push('kanban-plugin: basic');
  lines.push('---');
  lines.push('');

  // Warning comment
  lines.push('> [!WARNING] Auto-Generated Board');
  lines.push('> This Kanban board is automatically generated from `builder-operating-system/tasks/todo.md`.');
  lines.push('> Manual edits will be overwritten on next sync. Run `npm run sync-tasks` to update.');
  lines.push('');

  // Metadata
  const now = new Date();
  const timestamp = now.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
  lines.push(`**Last synced:** ${timestamp}`);
  lines.push('');

  // Generate each column
  for (const columnName of ['Backlog', 'Planned', 'Active', 'Done'] as KanbanColumn[]) {
    lines.push(`## ${columnName}`);
    lines.push('');

    const columnPhases = columns[columnName];

    if (columnPhases.length === 0) {
      lines.push('');
      continue;
    }

    for (const phase of columnPhases) {
      const checkbox = columnName === 'Done' ? '[x]' : '[ ]';
      lines.push(`- ${checkbox} **${phase.name}** — ${phase.description}`);

      // Add metadata
      if (phase.tasksTotal > 0) {
        const percentage = Math.round((phase.tasksComplete / phase.tasksTotal) * 100);
        lines.push(`  - Status: ${percentage}% complete`);
        lines.push(`  - Tasks: ${phase.tasksComplete}/${phase.tasksTotal} completed`);
      } else {
        // No tasks defined - show status based on phase status
        if (phase.status === 'complete') {
          lines.push(`  - Status: Complete ✅`);
        } else if (phase.status === 'planned') {
          lines.push(`  - Status: Planned`);
        } else {
          lines.push(`  - Status: Not started`);
        }
      }

      lines.push('');
    }
  }

  return lines.join('\n');
}

/**
 * Map status to Kanban column
 */
function statusToColumn(status: Phase['status']): KanbanColumn {
  switch (status) {
    case 'complete':
      return 'Done';
    case 'active':
      return 'Active';
    case 'planned':
      return 'Planned';
    case 'backlog':
      return 'Backlog';
  }
}

// ============================================================================
// File I/O
// ============================================================================

/**
 * Sync Kanban board to Obsidian vault
 */
async function syncToObsidian(kanbanContent: string): Promise<void> {
  const obsidianPath = '/Users/kennethluna/Luna/Projects';
  const kanbanFile = path.join(obsidianPath, 'Builder OS - Project Board.md');

  // Create directory if it doesn't exist
  try {
    await fs.mkdir(obsidianPath, { recursive: true });
  } catch (error) {
    // Directory might already exist, that's okay
  }

  // Write Kanban file
  await fs.writeFile(kanbanFile, kanbanContent, 'utf-8');

  console.log(`✅ Kanban board synced to: ${kanbanFile}`);
}

// ============================================================================
// Main Execution
// ============================================================================

async function main() {
  try {
    console.log('🔄 Starting Obsidian Kanban sync...\n');

    // Read todo.md
    const todoPath = path.join(process.cwd(), 'tasks', 'todo.md');
    console.log(`📖 Reading: ${todoPath}`);
    const todoContent = await fs.readFile(todoPath, 'utf-8');

    // Parse phases
    console.log('🔍 Parsing phases...');
    const phases = parsePhases(todoContent);
    console.log(`   Found ${phases.length} phases\n`);

    // Categorize and count
    const counts = {
      'Done': phases.filter(p => p.status === 'complete').length,
      'Active': phases.filter(p => p.status === 'active').length,
      'Planned': phases.filter(p => p.status === 'planned').length,
      'Backlog': phases.filter(p => p.status === 'backlog').length
    };

    console.log('📊 Phase Distribution:');
    console.log(`   ✅ Done: ${counts.Done}`);
    console.log(`   🏗️  Active: ${counts.Active}`);
    console.log(`   📋 Planned: ${counts.Planned}`);
    console.log(`   💡 Backlog: ${counts.Backlog}\n`);

    // Generate Kanban markdown
    console.log('📝 Generating Kanban markdown...');
    const kanbanContent = generateKanbanMarkdown(phases);

    // Write to Obsidian
    console.log('💾 Writing to Obsidian vault...');
    await syncToObsidian(kanbanContent);

    console.log('\n✨ Sync complete!');

  } catch (error) {
    console.error('❌ Error during sync:');
    console.error(error);
    process.exit(1);
  }
}

// Run if executed directly
if (require.main === module) {
  main();
}
