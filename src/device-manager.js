import { getTuyaClient } from './tuya-client.js';

function normalizeSearch(str) {
  return (str || '').toLowerCase().trim();
}

export function getDevices() {
  const tuya = getTuyaClient();
  return tuya.getDevices();
}

export function findDevice(idOrName) {
  const tuya = getTuyaClient();
  return tuya.getDevice(idOrName);
}

export async function getDeviceStatus(idOrName) {
  const tuya = getTuyaClient();
  return tuya.getStatus(idOrName);
}

export async function getAllStatuses() {
  const tuya = getTuyaClient();
  return tuya.getAllStatuses();
}
