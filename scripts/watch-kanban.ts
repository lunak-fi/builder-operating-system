#!/usr/bin/env tsx

import chokidar from 'chokidar';
import * as path from 'path';
import { main as syncKanban } from './sync-kanban.js';

const TODO_PATH = path.join(process.cwd(), 'tasks', 'todo.md');
const DEBOUNCE_MS = 500;

/**
 * Run sync with error handling
 */
async function runSync() {
  try {
    console.log('\n🔄 Change detected, syncing Kanban...');
    await syncKanban();
  } catch (error) {
    console.error('\n❌ Sync failed (will continue watching):', error);
    // Don't crash - continue watching for next change
  }
}

/**
 * Start file watcher
 */
async function startWatcher() {
  console.log('👀 Watching for changes to tasks/todo.md...');
  console.log('   Press Ctrl+C to stop\n');

  // Run initial sync on startup
  await runSync();

  // Create watcher with debouncing
  const watcher = chokidar.watch(TODO_PATH, {
    persistent: true,
    awaitWriteFinish: {
      stabilityThreshold: DEBOUNCE_MS,
      pollInterval: 100
    }
  });

  // Trigger sync on file changes
  watcher
    .on('change', runSync)
    .on('error', error => console.error('❌ Watcher error:', error));

  // Graceful shutdown handler
  process.on('SIGINT', () => {
    console.log('\n\n👋 Stopping watcher...');
    watcher.close();
    process.exit(0);
  });
}

// Start watching
startWatcher();
