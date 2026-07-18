import { useFocusEffect } from 'expo-router';
import { usePostHog } from 'posthog-react-native';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { HOUSEHOLD_ID } from '@/constants/household';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useSelectedMember } from '@/context/member-context';
import {
  approveCommand,
  EndpointNotFoundError,
  listPendingCommands,
  rejectCommand,
  type ApiPendingCommand,
} from '@/lib/api';

type Decision = 'approve' | 'reject';

export default function ApprovalQueueScreen() {
  const member = useSelectedMember();
  const posthog = usePostHog();
  const [commands, setCommands] = useState<ApiPendingCommand[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  // Approve/reject endpoints 404 while the backend is still in progress; once
  // detected, the queue stays visible but read-only.
  const [readOnly, setReadOnly] = useState(false);
  const [decidingId, setDecidingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoadError(null);
      setCommands(await listPendingCommands(HOUSEHOLD_ID, member.id));
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [member.id]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const refresh = () => {
    setRefreshing(true);
    load();
  };

  const decide = async (command: ApiPendingCommand, decision: Decision) => {
    setDecidingId(command.id);
    setActionError(null);
    try {
      const decided =
        decision === 'approve'
          ? await approveCommand(command.id, member.id)
          : await rejectCommand(command.id, member.id);
      posthog.capture(decision === 'approve' ? 'command_approved' : 'command_rejected', {
        verb: command.verb,
        command_id: command.id,
        member_id: member.id,
      });
      setCommands((current) => current.map((c) => (c.id === decided.id ? decided : c)));
    } catch (error) {
      if (error instanceof EndpointNotFoundError) {
        setReadOnly(true);
      } else {
        setActionError(error instanceof Error ? error.message : String(error));
      }
    } finally {
      setDecidingId(null);
    }
  };

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <ThemedText type="title" style={styles.title}>
          Approvals
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary" style={styles.memberLine}>
          Deciding as {member.name}
        </ThemedText>

        {readOnly ? (
          <ThemedView type="backgroundElement" style={styles.banner}>
            <ThemedText type="small" themeColor="textSecondary">
              Approvals are not available on the backend yet. Showing the queue read-only.
            </ThemedText>
          </ThemedView>
        ) : null}
        {actionError ? (
          <ThemedView type="backgroundElement" style={styles.banner}>
            <ThemedText type="small" style={styles.errorText}>
              {actionError}
            </ThemedText>
          </ThemedView>
        ) : null}

        {loading ? (
          <View style={styles.centered}>
            <ActivityIndicator />
          </View>
        ) : (
          <FlatList
            data={commands}
            keyExtractor={(command) => command.id}
            contentContainerStyle={styles.listContent}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
            ListEmptyComponent={
              <View style={styles.centered}>
                <ThemedText themeColor="textSecondary" style={styles.emptyText}>
                  {loadError ?? 'Nothing waiting for approval. Capture a receipt or voice note to get started.'}
                </ThemedText>
              </View>
            }
            renderItem={({ item }) => (
              <CommandCard
                command={item}
                deciding={decidingId === item.id}
                readOnly={readOnly}
                onDecide={decide}
              />
            )}
          />
        )}
      </SafeAreaView>
    </ThemedView>
  );
}

function CommandCard({
  command,
  deciding,
  readOnly,
  onDecide,
}: {
  command: ApiPendingCommand;
  deciding: boolean;
  readOnly: boolean;
  onDecide: (command: ApiPendingCommand, decision: Decision) => void;
}) {
  const pending = command.status === 'pending';
  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <View style={styles.cardHeader}>
        <ThemedView type="backgroundSelected" style={styles.verbBadge}>
          <ThemedText type="smallBold">{command.verb.replaceAll('_', ' ')}</ThemedText>
        </ThemedView>
        {!pending ? (
          <ThemedText type="smallBold" themeColor="textSecondary" style={styles.statusText}>
            {command.status}
          </ThemedText>
        ) : null}
      </View>

      <ThemedText>{command.human_readable}</ThemedText>

      <ThemedText type="small" themeColor="textSecondary">
        Proposed by {command.agent_name} ({command.model_id}) on{' '}
        {new Date(command.created_at).toLocaleString()}
      </ThemedText>

      {pending && !readOnly ? (
        <View style={styles.actions}>
          <Pressable
            accessibilityLabel="Approve command"
            disabled={deciding}
            onPress={() => onDecide(command, 'approve')}
            style={({ pressed }) => [
              styles.actionButton,
              styles.approveButton,
              (pressed || deciding) && styles.pressed,
            ]}>
            {deciding ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <ThemedText type="smallBold" style={styles.approveLabel}>
                Approve
              </ThemedText>
            )}
          </Pressable>
          <Pressable
            accessibilityLabel="Reject command"
            disabled={deciding}
            onPress={() => onDecide(command, 'reject')}
            style={({ pressed }) => [
              styles.actionButton,
              styles.rejectButton,
              (pressed || deciding) && styles.pressed,
            ]}>
            <ThemedText type="smallBold" style={styles.rejectLabel}>
              Reject
            </ThemedText>
          </Pressable>
        </View>
      ) : null}
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
  },
  title: {
    marginTop: Spacing.four,
  },
  memberLine: {
    marginBottom: Spacing.three,
  },
  banner: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    marginBottom: Spacing.three,
  },
  errorText: {
    color: '#d64545',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Spacing.six,
  },
  emptyText: {
    textAlign: 'center',
  },
  listContent: {
    gap: Spacing.three,
    paddingBottom: Spacing.four,
    flexGrow: 1,
  },
  card: {
    borderRadius: Spacing.four,
    padding: Spacing.four,
    gap: Spacing.three,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  verbBadge: {
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.half,
  },
  statusText: {
    textTransform: 'capitalize',
  },
  actions: {
    flexDirection: 'row',
    gap: Spacing.three,
  },
  actionButton: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: Spacing.three,
    paddingVertical: Spacing.three,
    minHeight: 48,
  },
  approveButton: {
    backgroundColor: '#3c87f7',
  },
  approveLabel: {
    color: '#ffffff',
  },
  rejectButton: {
    borderWidth: 1,
    borderColor: '#d64545',
  },
  rejectLabel: {
    color: '#d64545',
  },
  pressed: {
    opacity: 0.6,
  },
});
