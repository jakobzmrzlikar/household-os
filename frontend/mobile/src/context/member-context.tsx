import { createContext, useContext, useState, type ReactNode } from 'react';

import { type Member } from '@/constants/household';

type MemberContextValue = {
  member: Member | null;
  setMember: (member: Member) => void;
};

const MemberContext = createContext<MemberContextValue | null>(null);

export function MemberProvider({ children }: { children: ReactNode }) {
  const [member, setMember] = useState<Member | null>(null);

  return <MemberContext.Provider value={{ member, setMember }}>{children}</MemberContext.Provider>;
}

export function useMember(): MemberContextValue {
  const context = useContext(MemberContext);
  if (!context) {
    throw new Error('useMember must be used within a MemberProvider');
  }
  return context;
}

// For screens behind the member gate, where a selection is guaranteed.
export function useSelectedMember(): Member {
  const { member } = useMember();
  if (!member) {
    throw new Error('No member selected; this screen renders behind the member gate');
  }
  return member;
}
