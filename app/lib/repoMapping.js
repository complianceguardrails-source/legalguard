// Local, per-device mapping of "use case name" -> which of the user's own
// GitHub repos guardrail PRs should land in. Stored with AsyncStorage (not
// secure storage, since a repo name isn't a secret) so it's just plain
// on-device app state, kept out of the shared Postgres/PostgREST backend.

import AsyncStorage from "@react-native-async-storage/async-storage";

const STORAGE_KEY = "legalguard_repo_mapping_v1";

async function readAll() {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : {};
}

export async function getRepoMapping(useCaseName) {
  const all = await readAll();
  return all[useCaseName] || null;
}

export async function setRepoMapping(useCaseName, { owner, repo }) {
  const all = await readAll();
  all[useCaseName] = { owner, repo };
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}

export async function getAllRepoMappings() {
  return readAll();
}
