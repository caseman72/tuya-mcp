import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { getTuyaClient } from './tuya-client.js';
import { getDevices, findDevice } from './device-manager.js';
import { createToolWrapper } from './request-monitor.js';

export function createMcpServer() {
  const server = new McpServer({
    name: 'tuya-mcp',
    version: '1.0.0'
  });

  // Tool: list_devices
  server.tool(
    'list_devices',
    'List all configured Tuya climate devices.',
    {},
    createToolWrapper('list_devices', async () => {
      const devices = getDevices();
      const deviceList = devices.map(d => ({
        id: d.id,
        name: d.name,
        ip: d.ip || 'auto-discover'
      }));

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({ count: deviceList.length, devices: deviceList }, null, 2)
        }]
      };
    })
  );

  // Tool: get_status
  server.tool(
    'get_status',
    'Get current status of a mini-split: power, temperature, mode, fan speed.',
    {
      deviceId: z.string().describe('Device ID or name')
    },
    createToolWrapper('get_status', async ({ deviceId }) => {
      const tuya = getTuyaClient();
      try {
        const status = await tuya.getStatus(deviceId);
        return {
          content: [{ type: 'text', text: JSON.stringify(status, null, 2) }]
        };
      } catch (err) {
        return {
          content: [{ type: 'text', text: JSON.stringify({ error: err.message }) }],
          isError: true
        };
      }
    })
  );

  // Tool: get_all_statuses
  server.tool(
    'get_all_statuses',
    'Get current status of all mini-splits at once.',
    {},
    createToolWrapper('get_all_statuses', async () => {
      const tuya = getTuyaClient();
      const statuses = await tuya.getAllStatuses();
      return {
        content: [{ type: 'text', text: JSON.stringify({ count: statuses.length, devices: statuses }, null, 2) }]
      };
    })
  );

  // Tool: set_power
  server.tool(
    'set_power',
    'Turn a mini-split on or off.',
    {
      deviceId: z.string().describe('Device ID or name'),
      state: z.enum(['on', 'off']).describe('Desired power state')
    },
    createToolWrapper('set_power', async ({ deviceId, state }) => {
      const tuya = getTuyaClient();
      try {
        const result = await tuya.setPower(deviceId, state === 'on');
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      } catch (err) {
        return {
          content: [{ type: 'text', text: JSON.stringify({ error: err.message }) }],
          isError: true
        };
      }
    })
  );

  // Tool: set_temperature
  server.tool(
    'set_temperature',
    'Set the target temperature on a mini-split.',
    {
      deviceId: z.string().describe('Device ID or name'),
      temperature: z.number().describe('Target temperature in °F')
    },
    createToolWrapper('set_temperature', async ({ deviceId, temperature }) => {
      const tuya = getTuyaClient();
      try {
        const result = await tuya.setTemperature(deviceId, temperature);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      } catch (err) {
        return {
          content: [{ type: 'text', text: JSON.stringify({ error: err.message }) }],
          isError: true
        };
      }
    })
  );

  // Tool: set_mode
  server.tool(
    'set_mode',
    'Set the operating mode on a mini-split: heat or cool.',
    {
      deviceId: z.string().describe('Device ID or name'),
      mode: z.enum(['heat', 'cool']).describe('Operating mode')
    },
    createToolWrapper('set_mode', async ({ deviceId, mode }) => {
      const tuya = getTuyaClient();
      try {
        const result = await tuya.setMode(deviceId, mode);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      } catch (err) {
        return {
          content: [{ type: 'text', text: JSON.stringify({ error: err.message }) }],
          isError: true
        };
      }
    })
  );

  // Tool: set_fan_speed
  server.tool(
    'set_fan_speed',
    'Set the fan speed on a mini-split.',
    {
      deviceId: z.string().describe('Device ID or name'),
      speed: z.enum(['low', 'medium', 'high', 'auto']).describe('Fan speed')
    },
    createToolWrapper('set_fan_speed', async ({ deviceId, speed }) => {
      const tuya = getTuyaClient();
      try {
        const result = await tuya.setFanSpeed(deviceId, speed);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      } catch (err) {
        return {
          content: [{ type: 'text', text: JSON.stringify({ error: err.message }) }],
          isError: true
        };
      }
    })
  );

  // Tool: scan_device
  server.tool(
    'scan_device',
    'Read all raw DPS values from a device. Use to discover the DPS mapping.',
    {
      deviceId: z.string().describe('Device ID or name')
    },
    createToolWrapper('scan_device', async ({ deviceId }) => {
      const tuya = getTuyaClient();
      try {
        const result = await tuya.scan(deviceId);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      } catch (err) {
        return {
          content: [{ type: 'text', text: JSON.stringify({ error: err.message }) }],
          isError: true
        };
      }
    })
  );

  return server;
}
