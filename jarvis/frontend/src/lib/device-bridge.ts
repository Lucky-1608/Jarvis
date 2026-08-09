import { registerPlugin } from '@capacitor/core';

export interface DeviceHandsPlugin {
  performAction(options: { action: string; target: string }): Promise<{ success: boolean }>;
}

export const DeviceHands = registerPlugin<DeviceHandsPlugin>('DeviceHands');
