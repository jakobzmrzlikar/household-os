import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
} from 'expo-audio';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { File } from 'expo-file-system';
import { fetch } from 'expo/fetch';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { HOUSEHOLD_ID } from '@/constants/household';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useSelectedMember } from '@/context/member-context';

const API_URL = process.env.EXPO_PUBLIC_API_URL;

async function uploadCapture(fileUri: string, memberId: string): Promise<string> {
  if (!API_URL) {
    throw new Error('EXPO_PUBLIC_API_URL is not set');
  }
  const body = new FormData();
  body.append('household_id', HOUSEHOLD_ID);
  body.append('member_id', memberId);
  // Expo's WinterCG fetch rejects RN's legacy {uri, name, type} descriptors;
  // expo-file-system's File implements Blob and carries name + MIME type.
  body.append('file', new File(fileUri) as unknown as Blob);
  const response = await fetch(`${API_URL}/create_capture`, { method: 'POST', body });
  if (!response.ok) {
    throw new Error(`Upload failed (${response.status}): ${await response.text()}`);
  }
  const json = (await response.json()) as { id: string; kind: string };
  return json.id;
}

export default function CaptureScreen() {
  const member = useSelectedMember();
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const cameraRef = useRef<CameraView>(null);
  const [showCamera, setShowCamera] = useState(false);
  const [recording, setRecording] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  // Resolves true when the in-flight hold-to-record gesture actually started
  // recording; lets a release that beats prepareToRecordAsync wait for it.
  const recordingStartRef = useRef<Promise<boolean> | null>(null);

  useEffect(() => {
    // Ask for the microphone and enable a recording-capable audio session once
    // at mount (the documented expo-audio setup): switching the session mode
    // inside the press gesture races prepareToRecordAsync and gets it rejected.
    (async () => {
      const permission = await AudioModule.requestRecordingPermissionsAsync();
      if (!permission.granted) {
        setStatus('Microphone permission denied');
        return;
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
    })().catch((error: unknown) => {
      setStatus(error instanceof Error ? error.message : String(error));
    });
  }, []);

  const submit = async (fileUri: string) => {
    setUploading(true);
    setStatus(null);
    try {
      const id = await uploadCapture(fileUri, member.id);
      setStatus(`Capture created: ${id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setUploading(false);
    }
  };

  const openCamera = async () => {
    if (!cameraPermission?.granted) {
      const result = await requestCameraPermission();
      if (!result.granted) {
        setStatus('Camera permission denied');
        return;
      }
    }
    setShowCamera(true);
  };

  const takePhoto = async () => {
    const photo = await cameraRef.current?.takePictureAsync();
    setShowCamera(false);
    if (!photo?.uri) {
      setStatus('Could not take a photo');
      return;
    }
    await submit(photo.uri);
  };

  const startRecording = () => {
    recordingStartRef.current = (async () => {
      try {
        await recorder.prepareToRecordAsync();
        recorder.record();
        setRecording(true);
        return true;
      } catch (error) {
        setStatus(
          `Could not start recording: ${error instanceof Error ? error.message : String(error)}`,
        );
        return false;
      }
    })();
  };

  const stopRecording = async () => {
    const started = recordingStartRef.current;
    if (!started) {
      return;
    }
    recordingStartRef.current = null;
    const isRecording = await started;
    setRecording(false);
    if (!isRecording) {
      return;
    }
    try {
      await recorder.stop();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
      return;
    }
    const uri = recorder.uri;
    if (!uri) {
      setStatus('No recording captured');
      return;
    }
    await submit(uri);
  };

  if (showCamera) {
    return (
      <View style={styles.cameraContainer}>
        <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" />
        <SafeAreaView style={styles.cameraOverlay}>
          <Pressable
            accessibilityLabel="Take photo"
            style={({ pressed }) => [styles.shutter, pressed && styles.pressed]}
            onPress={takePhoto}
          />
          <Pressable onPress={() => setShowCamera(false)}>
            <ThemedText style={styles.cancelText}>Cancel</ThemedText>
          </Pressable>
        </SafeAreaView>
      </View>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ThemedText type="title" style={styles.title}>
          Capture
        </ThemedText>

        <Pressable
          onPress={openCamera}
          disabled={uploading}
          style={({ pressed }) => [pressed && styles.pressed, styles.buttonWrapper]}>
          <ThemedView type="backgroundElement" style={styles.bigButton}>
            <ThemedText type="subtitle">Photo receipt</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              Tap to open the camera
            </ThemedText>
          </ThemedView>
        </Pressable>

        <Pressable
          onPressIn={startRecording}
          onPressOut={stopRecording}
          disabled={uploading}
          style={({ pressed }) => [pressed && styles.pressed, styles.buttonWrapper]}>
          <ThemedView
            type={recording ? 'backgroundSelected' : 'backgroundElement'}
            style={styles.bigButton}>
            <ThemedText type="subtitle">
              {recording ? 'Recording…' : 'Voice note'}
            </ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              Hold to record, release to send
            </ThemedText>
          </ThemedView>
        </Pressable>

        <View style={styles.statusRow}>
          {uploading ? <ActivityIndicator /> : null}
          {status ? (
            <ThemedText type="small" themeColor="textSecondary" style={styles.statusText}>
              {status}
            </ThemedText>
          ) : null}
        </View>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'center',
  },
  safeArea: {
    flex: 1,
    maxWidth: MaxContentWidth,
    paddingHorizontal: Spacing.four,
    justifyContent: 'center',
    gap: Spacing.four,
  },
  title: {
    textAlign: 'center',
    marginBottom: Spacing.four,
  },
  buttonWrapper: {
    alignSelf: 'stretch',
  },
  bigButton: {
    alignItems: 'center',
    gap: Spacing.two,
    paddingVertical: Spacing.six,
    borderRadius: Spacing.four,
  },
  pressed: {
    opacity: 0.6,
  },
  statusRow: {
    minHeight: 80,
    alignItems: 'center',
    gap: Spacing.two,
  },
  statusText: {
    textAlign: 'center',
  },
  cameraContainer: {
    flex: 1,
    backgroundColor: '#000000',
  },
  cameraOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: Spacing.four,
    paddingBottom: Spacing.six,
  },
  shutter: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#ffffff',
    borderWidth: 4,
    borderColor: '#D0D0D3',
  },
  cancelText: {
    color: '#ffffff',
  },
});
