import type { CapacitorConfig } from '@capacitor/cli';

/**
 * PMC Managers — Capacitor config.
 * The frontend already ships as a React build; Capacitor wraps that build in a
 * native iOS / Android shell.
 *
 * Build flow:
 *   yarn build                          # Compile the React app to /build
 *   npx cap sync                        # Copy build/ into ios and android platforms
 *   npx cap open ios                    # Launch Xcode
 *   npx cap open android                # Launch Android Studio
 */
const config: CapacitorConfig = {
  appId: 'com.pmcmanagers.tenders',
  appName: 'PMC Tenders',
  webDir: 'build',
  bundledWebRuntime: false,
  ios: {
    contentInset: 'always',
    scheme: 'PMC Tenders',
    limitsNavigationsToAppBoundDomains: true,
    backgroundColor: '#0b1e3fff',
  },
  android: {
    backgroundColor: '#0b1e3fff',
    allowMixedContent: false,
    captureInput: true,
  },
  server: {
    // For production leave this out — the app serves /build directly.
    // For dev, uncomment and point at your preview URL:
    // url: 'https://tender-hub-57.preview.emergentagent.com',
    // cleartext: false,
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1500,
      launchAutoHide: true,
      backgroundColor: '#0b1e3fff',
      showSpinner: true,
      spinnerColor: '#ffcf76',
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
  },
};

export default config;
