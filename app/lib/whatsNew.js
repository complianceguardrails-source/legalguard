// What has arrived since this device last looked.
//
// No account, no push token, nothing sent anywhere: the only thing stored
// is a timestamp per section, on the device. The counts come from the same
// public tables the screens already read. A fresh install records "now"
// and starts from zero rather than announcing a thousand use cases.

import AsyncStorage from "@react-native-async-storage/async-storage";

import { countNewUseCases, countNewRegulations, countNewStories } from "./api";

const KEY = "legalguard_last_seen_v1";
export const SECTIONS = ["useCases", "regulations", "stories"];
const EMPTY = { useCases: 0, regulations: 0, stories: 0 };

async function readLastSeen() {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // A device that cannot read its own storage still gets a working app;
    // it simply never shows a badge.
  }
  return null;
}

async function writeLastSeen(next) {
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* see above */
  }
}

/** Seeds every section to now on first run. Returns the stored map. */
export async function initLastSeen() {
  const existing = await readLastSeen();
  if (existing) return existing;
  const now = new Date().toISOString();
  const seeded = Object.fromEntries(SECTIONS.map((s) => [s, now]));
  await writeLastSeen(seeded);
  return seeded;
}

export async function markSeen(section) {
  const current = (await readLastSeen()) || {};
  const next = { ...current, [section]: new Date().toISOString() };
  await writeLastSeen(next);
  return next;
}

/** { useCases, regulations, stories } -- how many rows arrived since each
 * section was last opened. Never throws: a count that cannot be fetched
 * is reported as zero rather than as a badge that is wrong. */
export async function fetchNewCounts() {
  const seen = await initLastSeen();
  const [useCases, regulations, stories] = await Promise.all([
    countNewUseCases(seen.useCases),
    countNewRegulations(seen.regulations),
    countNewStories(seen.stories),
  ]);
  return { ...EMPTY, useCases, regulations, stories };
}
