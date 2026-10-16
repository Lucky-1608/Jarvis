import { registerPlugin } from '@capacitor/core';

export interface DeviceHandsPlugin {
  performAction(options: { action: string; target: string; x?: number; y?: number }): Promise<{ success: boolean; message?: string }>;
  launchApp(options: { name: string }): Promise<{ success: boolean; message?: string; error?: string }>;
  readScreen?(): Promise<{ elements: string }>;
}

export const DeviceHands = registerPlugin<DeviceHandsPlugin>('DeviceHands');
