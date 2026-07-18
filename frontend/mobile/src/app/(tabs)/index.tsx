import { useFocusEffect } from 'expo-router';
import { usePostHog } from 'posthog-react-native';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { HOUSEHOLD_ID, MEMBERS } from '@/constants/household';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useSelectedMember } from '@/context/member-context';
import { useTheme } from '@/hooks/use-theme';
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
  const theme = useTheme();

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
            <ThemedText type="small" style={{ color: theme.danger }}>
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
            ListEmptyComponent={<EmptyState error={loadError} />}
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

function EmptyState({ error }: { error: string | null }) {
  const theme = useTheme();

  if (error) {
    return (
      <View style={styles.centered}>
        <ThemedText type="small" style={[styles.emptyBody, { color: theme.danger }]}>
          {error}
        </ThemedText>
      </View>
    );
  }
  return (
    <View style={styles.centered}>
      <View style={[styles.emptyIconCircle, { borderColor: theme.textSecondary }]}>
        <View style={[styles.emptyIconCheck, { borderColor: theme.textSecondary }]} />
      </View>
      <ThemedText type="smallBold">All caught up</ThemedText>
      <ThemedText type="small" themeColor="textSecondary" style={styles.emptyBody}>
        Capture a receipt or voice note and proposals will land here.
      </ThemedText>
    </View>
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
  const theme = useTheme();
  const pending = command.status === 'pending';
  const summary = summarize(command);
  const items = extractLineItems(command.payload);
  const transcript = asString(command.payload.transcript);

  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <View style={styles.cardHeader}>
        <ThemedView type="backgroundSelected" style={styles.provenancePill}>
          <ThemedText type="small" themeColor="textSecondary" style={styles.provenanceText}>
            {provenanceLabel(command)}
          </ThemedText>
        </ThemedView>
        {pending ? (
          <ThemedText type="small" themeColor="textSecondary" style={styles.metaText}>
            {formatTimestamp(command.created_at)}
          </ThemedText>
        ) : (
          <ThemedText type="smallBold" themeColor="textSecondary" style={styles.statusText}>
            {command.status}
          </ThemedText>
        )}
      </View>

      <View style={styles.summaryBlock}>
        <ThemedText style={styles.headline}>{summary.headline}</ThemedText>
        {summary.amount ? <ThemedText style={styles.amount}>{summary.amount}</ThemedText> : null}
        <ThemedText type="small" themeColor="textSecondary">
          {summary.subline}
        </ThemedText>
      </View>

      {items.length > 0 ? (
        <View style={styles.lineItems}>
          {items.map((item, index) => (
            <View key={index} style={styles.lineItemRow}>
              <ThemedText type="small" themeColor="textSecondary" style={styles.lineItemName}>
                {item.name}
              </ThemedText>
              {item.detail ? (
                <ThemedText type="small" themeColor="textSecondary">
                  {item.detail}
                </ThemedText>
              ) : null}
            </View>
          ))}
        </View>
      ) : null}

      {transcript ? (
        <View style={[styles.transcript, { borderLeftColor: theme.backgroundSelected }]}>
          <ThemedText type="small" themeColor="textSecondary" style={styles.transcriptText}>
            &ldquo;{transcript}&rdquo;
          </ThemedText>
        </View>
      ) : null}

      {pending && !readOnly ? (
        <View style={styles.actions}>
          <Pressable
            accessibilityLabel="Approve command"
            disabled={deciding}
            onPress={() => onDecide(command, 'approve')}
            style={({ pressed }) => [
              styles.actionButton,
              { backgroundColor: theme.accent },
              (pressed || deciding) && styles.pressed,
            ]}>
            {deciding ? (
              <ActivityIndicator color={theme.onAccent} />
            ) : (
              <ThemedText type="smallBold" style={{ color: theme.onAccent }}>
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
              { borderColor: theme.danger },
              (pressed || deciding) && styles.pressed,
            ]}>
            <ThemedText type="smallBold" style={{ color: theme.danger }}>
              Reject
            </ThemedText>
          </Pressable>
        </View>
      ) : null}
    </ThemedView>
  );
}

type CardSummary = {
  headline: string;
  amount: string | null;
  subline: string;
};

type CardLineItem = {
  name: string;
  detail: string | null;
};

function summarize(command: ApiPendingCommand): CardSummary {
  const payload = command.payload;
  if (command.verb === 'record_expense') {
    const amount = asNumber(payload.amount);
    const currency = asString(payload.currency);
    const payer = asString(payload.payer_member_id);
    const split = payload.split;
    const parts = ['Record expense'];
    if (payer) {
      parts.push(`paid by ${memberName(payer)}`);
    }
    if (typeof split === 'object' && split !== null && Object.keys(split).length > 1) {
      parts.push(`split ${Object.keys(split).length} ways`);
    }
    return {
      headline: asString(payload.merchant) ?? 'Expense',
      amount: amount === null ? null : formatAmount(amount, currency),
      subline: parts.join(' · '),
    };
  }
  if (command.verb === 'adjust_pantry_item') {
    const quantity = asNumber(payload.quantity);
    const unit = asString(payload.unit);
    return {
      headline: asString(payload.name) ?? 'Pantry item',
      amount: quantity === null ? null : `${quantity} ${unit ?? ''}`.trim(),
      subline: 'Add to pantry',
    };
  }
  // Unreachable for the current verb union; keeps unknown verbs renderable.
  return {
    headline: command.human_readable,
    amount: null,
    subline: String(command.verb).replaceAll('_', ' '),
  };
}

// Payloads are agent-produced JSON; render line items only when they are
// present and well-formed rather than trusting the shape.
function extractLineItems(payload: Record<string, unknown>): CardLineItem[] {
  const raw = payload.line_items;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.flatMap((entry: unknown): CardLineItem[] => {
    if (typeof entry !== 'object' || entry === null) {
      return [];
    }
    const item = entry as Record<string, unknown>;
    const name = asString(item.name);
    if (name === null) {
      return [];
    }
    const quantity = asNumber(item.quantity);
    const unit = asString(item.unit);
    const detail = quantity === null ? null : `${quantity} ${unit ?? ''}`.trim();
    return [{ name, detail }];
  });
}

function provenanceLabel(command: ApiPendingCommand): string {
  const agent = command.agent_name.toLowerCase();
  if (agent.includes('voice') || agent.includes('audio') || agent.includes('transcript')) {
    return 'voice note';
  }
  const source = agent.includes('receipt') ? 'receipt' : command.agent_name.replaceAll('_', ' ');
  return `${source} · ${command.model_id}`;
}

function memberName(memberId: string): string {
  return MEMBERS.find((member) => member.id === memberId)?.name ?? memberId;
}

function formatAmount(amount: number, currency: string | null): string {
  if (!currency) {
    return amount.toFixed(2);
  }
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amount);
  } catch {
    // Unknown/invalid currency code from the agent; show it verbatim.
    return `${amount.toFixed(2)} ${currency}`;
  }
}

function formatTimestamp(isoDate: string): string {
  return new Date(isoDate).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
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
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two,
    paddingVertical: Spacing.six,
  },
  emptyIconCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.two,
  },
  emptyIconCheck: {
    width: 22,
    height: 12,
    borderLeftWidth: 2.5,
    borderBottomWidth: 2.5,
    transform: [{ rotate: '-45deg' }],
    marginTop: -4,
  },
  emptyBody: {
    textAlign: 'center',
    maxWidth: 260,
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
    gap: Spacing.two,
  },
  provenancePill: {
    borderRadius: 999,
    paddingHorizontal: Spacing.two + Spacing.half,
    paddingVertical: Spacing.half,
  },
  provenanceText: {
    fontSize: 11,
    lineHeight: 14,
  },
  metaText: {
    fontSize: 11,
    lineHeight: 14,
  },
  statusText: {
    textTransform: 'capitalize',
  },
  summaryBlock: {
    gap: Spacing.half,
  },
  headline: {
    fontSize: 17,
    lineHeight: 22,
    fontWeight: 600,
  },
  amount: {
    fontSize: 30,
    lineHeight: 36,
    fontWeight: 700,
  },
  lineItems: {
    gap: Spacing.one,
  },
  lineItemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: Spacing.two,
  },
  lineItemName: {
    flexShrink: 1,
  },
  transcript: {
    borderLeftWidth: 3,
    paddingLeft: Spacing.two + Spacing.half,
  },
  transcriptText: {
    fontStyle: 'italic',
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
  rejectButton: {
    borderWidth: 1,
  },
  pressed: {
    opacity: 0.6,
  },
});
