import { Pressable, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MEMBERS, type Member } from '@/constants/household';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useMember } from '@/context/member-context';

export function MemberPicker() {
  const { setMember } = useMember();

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ThemedText type="title" style={styles.title}>
          Who are you?
        </ThemedText>
        <ThemedText type="default" themeColor="textSecondary" style={styles.subtitle}>
          Everything you capture and approve is recorded as you.
        </ThemedText>
        {MEMBERS.map((member) => (
          <MemberCard key={member.id} member={member} onSelect={setMember} />
        ))}
      </SafeAreaView>
    </ThemedView>
  );
}

function MemberCard({ member, onSelect }: { member: Member; onSelect: (member: Member) => void }) {
  return (
    <Pressable
      accessibilityLabel={`Continue as ${member.name}`}
      onPress={() => onSelect(member)}
      style={({ pressed }) => [styles.cardWrapper, pressed && styles.pressed]}>
      <ThemedView type="backgroundElement" style={styles.card}>
        <View style={styles.avatar}>
          <ThemedText type="subtitle" style={styles.avatarInitial}>
            {member.name.charAt(0)}
          </ThemedText>
        </View>
        <ThemedText type="subtitle">{member.name}</ThemedText>
      </ThemedView>
    </Pressable>
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
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: Spacing.four,
  },
  cardWrapper: {
    alignSelf: 'stretch',
  },
  card: {
    alignItems: 'center',
    gap: Spacing.three,
    paddingVertical: Spacing.six,
    borderRadius: Spacing.four,
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#3c87f7',
  },
  avatarInitial: {
    color: '#ffffff',
  },
  pressed: {
    opacity: 0.6,
  },
});
