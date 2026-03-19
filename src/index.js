#!/usr/bin/env node

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createMcpServer } from './server.js';
import { initializeMonitoring } from './request-monitor.js';

async function main() {
  try {
    initializeMonitoring();

    const server = createMcpServer();
    const transport = new StdioServerTransport();

    await server.connect(transport);

    console.error('[tuya-mcp] Server started (stdio transport)');
  } catch (err) {
    console.error('[tuya-mcp] Failed to start server:', err.message);
    process.exit(1);
  }
}

main();
