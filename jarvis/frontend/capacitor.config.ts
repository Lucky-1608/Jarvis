import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.jarvis.app',
  appName: 'Jarvis',
  webDir: 'dist',
  server: {
    url: 'https://jarvisos-gdhfgnc4gscqecav.centralindia-01.azurewebsites.net',
    androidScheme: 'http',
    cleartext: true
  }
};

export default config;
