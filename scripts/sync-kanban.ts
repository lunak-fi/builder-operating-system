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
  // Look for **Goal:** or first paragraph after header
  const goalMatch = rawSection.match(/\*\*Goal:\*\*\s*(.+?)(?:\n\n|$)/s);
  if (goalMatch) {
    return goalMatch[1].trim().replace(/\n/g, ' ');
  }

  // Look for **Problem:** pattern
  const problemMatch = rawSection.match(/\*\*Problem:\*\*\s*(.+?)(?:\n\n|$)/s);
  if (problemMatch) {
    return problemMatch[1].trim().replace(/\n/g, ' ');
  }

  // Look for **Implementation complete:** pattern
  const implMatch = rawSection.match(/\*\*Implementation complete:\*\*\s*(.+?)(?:\n\n|$)/s);
  if (implMatch) {
    return implMatch[1].trim().replace(/\n/g, ' ').split('\n')[0];
  }

  // Fall back to first paragraph
  const lines = rawSection.split('\n').slice(1); // Skip header line
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('**') && !trimmed.startsWith('-') && !trimmed.startsWith('#')) {
      return trimmed;
    }
  }

  return 'No description available';
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
        lines.push(`  - Status: Not started`);
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
