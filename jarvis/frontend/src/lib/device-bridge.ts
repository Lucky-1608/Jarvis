import { registerPlugin } from '@capacitor/core';

export interface DeviceHandsPlugin {
  performAction(options: { action: string; target: string }): Promise<{ success: boolean }>;
  launchApp(options: { name: string }): Promise<{ success: boolean, message?: string, error?: string }>;
}

export const DeviceHands = registerPlugin<DeviceHandsPlugin>('DeviceHands');
