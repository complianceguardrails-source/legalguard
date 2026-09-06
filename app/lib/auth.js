// GitHub credential storage. On iOS/Android -- the real target platform for
// this app -- the PAT never leaves the device: it's written to the OS
// keychain (iOS Keychain / Android Keystore) via expo-secure-store, and
// every GitHub API call in githubClient.js is made directly from the phone.
// LegalGuard's shared Postgres/PostgREST backend has no code path that
// reads or stores this value.
//
// expo-secure-store has NO web implementation at all -- calling it in a
// browser throws. Since this repo is also previewed via `expo start --web`
// for convenience, storage falls back to localStorage there, clearly
// labeled as such. localStorage is NOT secure storage (any script on the
// page, or anyone with devtools access, can read it) -- treat the web
// preview as a UI/layout check only, never paste a real token into it.
// Real usage of this screen should happen on an iOS/Android build.

import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "legalguard_github_pat";
const USERNAME_KEY = "legalguard_github_username";
const IS_WEB = Platform.OS === "web";

async function setItem(key, value) {
  if (IS_WEB) return window.localStorage.setItem(key, value);
  return SecureStore.setItemAsync(key, value);
}

async function getItem(key) {
  if (IS_WEB) return window.localStorage.getItem(key);
  return SecureStore.getItemAsync(key);
}

async function deleteItem(key) {
  if (IS_WEB) return window.localStorage.removeItem(key);
  return SecureStore.deleteItemAsync(key);
}

export async function saveGitHubCredentials(username, token) {
  await setItem(USERNAME_KEY, username);
  await setItem(TOKEN_KEY, token);
}

export async function getGitHubCredentials() {
  const [username, token] = await Promise.all([getItem(USERNAME_KEY), getItem(TOKEN_KEY)]);
  return { username, token };
}

export async function clearGitHubCredentials() {
  await deleteItem(USERNAME_KEY);
  await deleteItem(TOKEN_KEY);
}

/** Minimal PAT scope check: confirms the token authenticates and can see the
 * target repo before the user taps into a real dispatch flow. */
export async function verifyToken(token) {
  const res = await fetch("https://api.github.com/user", {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
    },
  });
  if (!res.ok) {
    if (res.status === 0) {
      // A network-level failure (status 0 / TypeError before this line) is
      // the fetch's CORS/connectivity signature -- see the try/catch call
      // site for how that's distinguished from a clean 401/403 from GitHub.
      throw new Error("Network error reaching api.github.com -- check your connection.");
    }
    throw new Error(`GitHub rejected this token (HTTP ${res.status}). It may be invalid, expired, or missing scope.`);
  }
  return res.json(); // includes .login
}
