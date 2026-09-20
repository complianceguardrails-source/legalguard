// Per-device Discover state: which use cases the user starred, which they
// dismissed from the deck, and which categories they last selected. Plain
// AsyncStorage, same as repoMapping.js -- none of this is a secret, and
// none of it belongs in the shared backend. A dismissal is a preference,
// not a deletion: the row still exists everywhere else in the app.

import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "legalguard_discover_v1";

async function read() {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return { starred: parsed.starred || [], dismissed: parsed.dismissed || [], selected: parsed.selected || [] };
  } catch {
    return { starred: [], dismissed: [], selected: [] };
  }
}

async function write(state) {
  await AsyncStorage.setItem(KEY, JSON.stringify(state));
}

export async function getDiscoverState() {
  return read();
}

export async function toggleStar(useCaseId) {
  const state = await read();
  const set = new Set(state.starred);
  set.has(useCaseId) ? set.delete(useCaseId) : set.add(useCaseId);
  state.starred = [...set];
  await write(state);
  return set.has(useCaseId);
}

export async function dismiss(useCaseId) {
  const state = await read();
  if (!state.dismissed.includes(useCaseId)) state.dismissed.push(useCaseId);
  await write(state);
}

export async function clearDismissed() {
  const state = await read();
  state.dismissed = [];
  await write(state);
}

export async function setSelectedCategories(slugs) {
  const state = await read();
  state.selected = slugs;
  await write(state);
}
