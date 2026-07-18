import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { PostHogProvider } from 'posthog-react-native';
import { useColorScheme } from 'react-native';

import { AnimatedSplashOverlay } from '@/components/animated-icon';
import { MemberPicker } from '@/components/member-picker';
import { MemberProvider, useMember } from '@/context/member-context';

SplashScreen.preventAutoHideAsync();

const POSTHOG_API_KEY = process.env.EXPO_PUBLIC_POSTHOG_API_KEY;
const POSTHOG_HOST = process.env.EXPO_PUBLIC_POSTHOG_HOST;

export default function RootLayout() {
  const colorScheme = useColorScheme();
  return (
    // Without an API key the provider mounts disabled, so usePostHog() stays
    // safe to call and no events leave the device.
    <PostHogProvider
      apiKey={POSTHOG_API_KEY || 'disabled'}
      options={{ host: POSTHOG_HOST || undefined, disabled: !POSTHOG_API_KEY }}
      autocapture={false}>
      <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
        <MemberProvider>
          <AnimatedSplashOverlay />
          <MemberGate />
        </MemberProvider>
      </ThemeProvider>
    </PostHogProvider>
  );
}

// Demo auth: navigation only mounts once a member is picked, so every screen
// can rely on a selection being present.
function MemberGate() {
  const { member } = useMember();
  if (!member) {
    return <MemberPicker />;
  }
  return <Stack screenOptions={{ headerShown: false }} />;
}
