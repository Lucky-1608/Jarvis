import { registerPlugin } from '@capacitor/core';

export interface DeviceHandsPlugin {
  launchApp(options: { name: string }): Promise<{ success: boolean; message?: string; error?: string }>;
  closeApp(options: { name?: string }): Promise<{ success: boolean; message?: string; error?: string }>;
  minimizeApp(): Promise<{ success: boolean }>;
  performAction(options: {
    action: string;
    target?: string;
    x?: number;
    y?: number;
    text?: string;
    direction?: string;
  }): Promise<{ success: boolean; message?: string }>;
  readScreen(): Promise<{ elements: string }>;
  sendSMS(options: { number: string; message: string }): Promise<{ success: boolean; message?: string }>;
  makeCall(options: { number: string }): Promise<{ success: boolean; message?: string }>;
  getBattery(): Promise<{ level: number; charging: boolean; output: string }>;
  showNotification(options: { title: string; message: string }): Promise<{ success: boolean }>;
  openAccessibilitySettings(): Promise<{ success: boolean }>;
  openNotificationSettings(): Promise<{ success: boolean }>;
  requestBatteryOptimization(): Promise<{ success: boolean }>;
  getPermissionsStatus(): Promise<{
    accessibilityEnabled: boolean;
    batteryOptimizationIgnored: boolean;
    notificationAccessEnabled: boolean;
  }>;
}

export const DeviceHands = registerPlugin<DeviceHandsPlugin>('DeviceHands');
