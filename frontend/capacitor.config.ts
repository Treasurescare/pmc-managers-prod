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
    backgroundColor: '#162921ff',
  },
  android: {
    backgroundColor: '#162921ff',
    allowMixedContent: false,
    captureInput: true,
  },
  server: {
    // The app opens the live site, so every website release reaches the app without a new install.
    url: 'https://pmcmanagers.com',
    allowNavigation: ['pmcmanagers.com', '*.pmcmanagers.com'],
    cleartext: false,
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1500,
      launchAutoHide: true,
      backgroundColor: '#162921ff',
      showSpinner: true,
      spinnerColor: '#d9bd72',
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
  },
};

export default config;
