import Tuya from '@caseman72/tuya-api';
import { getProjectRoot } from './config.js';

let tuyaInstance = null;

export function getTuyaClient() {
  if (tuyaInstance) {
    return tuyaInstance;
  }

  // tuya-api reads devices from .tuya-devices.json in:
  // - Current working directory / devicesPath
  // - ~/.config/tuya-api/.tuya-devices.json
  tuyaInstance = new Tuya({ devicesPath: getProjectRoot() });

  return tuyaInstance;
}

export function refreshTuyaClient() {
  tuyaInstance = null;
  return getTuyaClient();
}
