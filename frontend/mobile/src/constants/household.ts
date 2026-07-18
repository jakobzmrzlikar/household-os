// Demo auth (no real accounts): the household is fixed and members are picked
// from a hardcoded roster on first launch.

export type Member = {
  id: string;
  name: string;
};

export const HOUSEHOLD_ID = 'demo-household';

export const MEMBERS: Member[] = [
  { id: 'jan', name: 'Jan' },
  { id: 'anna', name: 'Anna' },
];
