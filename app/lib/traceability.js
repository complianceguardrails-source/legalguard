// Real, on-device record of what the GitOps dispatch pipeline actually did --
// not a mockup. githubClient.js calls appendLog()/setPipelineStep() as each
// step of a real dispatch (repo creation, branch+commit, PR, merge,
// verification) actually happens, so the Dispatch tab's "Pipeline Status"
// and "Traceability Logs" sections reflect genuine API calls and their real
// outcomes (including failures), never simulated steps or invented
// timestamps. Stored with AsyncStorage, same as repoMapping.js -- this is
// just on-device operational history, not a secret.
import AsyncStorage from "@react-native-async-storage/async-storage";

const LOG_KEY = "legalguard_traceability_log_v1";
const PIPELINE_KEY = "legalguard_traceability_pipeline_v1";
const MAX_LOG_ENTRIES = 200;

export const PIPELINE_STEPS = ["repository_creation", "branch_and_commit", "pull_request_merge", "verification_check"];

async function readLog() {
  const raw = await AsyncStorage.getItem(LOG_KEY);
  return raw ? JSON.parse(raw) : [];
}

/** Appends one real event. `type` should be one of PIPELINE_STEPS, or
 * 'dispatch_start' / 'error' for the bookend/failure cases those steps
 * don't cover. */
export async function appendLog({ type, message, repo, owner, url }) {
  const all = await readLog();
  all.push({ type, message, repo, owner, url, at: new Date().toISOString() });
  const trimmed = all.length > MAX_LOG_ENTRIES ? all.slice(all.length - MAX_LOG_ENTRIES) : all;
  await AsyncStorage.setItem(LOG_KEY, JSON.stringify(trimmed));
}

/** Most recent entries first. */
export async function getRecentLogs(limit = 20) {
  const all = await readLog();
  return all.slice(-limit).reverse();
}

/** Resets the "current pipeline" snapshot to all-pending -- call this once,
 * right before starting a new dispatch, so the Pipeline Status tiles reflect
 * *this* run rather than lingering statuses from a previous one. */
export async function resetPipeline({ repo, owner, label }) {
  const state = {
    repo,
    owner,
    label,
    startedAt: new Date().toISOString(),
    steps: Object.fromEntries(PIPELINE_STEPS.map((s) => [s, { status: "pending", detail: null }])),
  };
  await AsyncStorage.setItem(PIPELINE_KEY, JSON.stringify(state));
  return state;
}

/** status: 'pending' | 'done' | 'failed' | 'not_applicable' | 'running' */
export async function setPipelineStep(step, status, detail = null) {
  const raw = await AsyncStorage.getItem(PIPELINE_KEY);
  const state = raw ? JSON.parse(raw) : { steps: Object.fromEntries(PIPELINE_STEPS.map((s) => [s, { status: "pending", detail: null }])) };
  state.steps[step] = { status, detail };
  await AsyncStorage.setItem(PIPELINE_KEY, JSON.stringify(state));
  return state;
}

export async function getPipelineStatus() {
  const raw = await AsyncStorage.getItem(PIPELINE_KEY);
  return raw ? JSON.parse(raw) : null;
}
