// Decentralized GitOps engine: runs entirely on the user's device against
// the real GitHub REST API (api.github.com), using a Personal Access Token
// the user pastes in once and which is stored ONLY in this device's secure
// storage (see auth.js) -- LegalGuard's shared backend never sees it.
//
// This corrects two real bugs from the earlier design sketch: (1) requests
// must go to api.github.com, not github.com; (2) React Native has no
// built-in btoa/atob for non-Latin1 text, so file content is base64-encoded
// via the 'base-64' package over a UTF-8-safe byte string.

import { encode as base64Encode, decode as base64Decode } from "base-64";
import { appendLog, setPipelineStep, resetPipeline } from "./traceability";

const API_ROOT = "https://api.github.com";

function utf8ToBase64(str) {
  // Standard browser-safe UTF-8 -> binary-string -> base64 trick, ported to
  // the 'base-64' package (which expects a Latin1/byte string as input).
  const binaryString = unescape(encodeURIComponent(str));
  return base64Encode(binaryString);
}

function base64ToUtf8(b64) {
  // Reverse of utf8ToBase64() above -- GitHub's Contents API returns file
  // content as base64 of the raw bytes, which decodes to a Latin1/byte
  // string that still needs the escape/decodeURIComponent round-trip to
  // come back out as proper UTF-8 text.
  return decodeURIComponent(escape(base64Decode(b64)));
}

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
  };
}

async function githubRequest(path, token, options = {}) {
  const res = await fetch(`${API_ROOT}${path}`, {
    ...options,
    headers: { ...authHeaders(token), ...(options.headers || {}) },
  });
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await res.json().catch(() => null) : null;
  if (!res.ok) {
    const message = body?.message || res.statusText;
    // GitHub's top-level `message` on a 422 is often a generic wrapper
    // ("Repository creation failed.") -- the actually useful reason lives
    // in the `errors[]` array (field/code/message per validation failure).
    // Surface it directly instead of making the caller dig through a
    // console.log of err.body that most environments won't even show.
    const errorDetails =
      Array.isArray(body?.errors) && body.errors.length > 0 ? ` -- details: ${JSON.stringify(body.errors)}` : "";
    // GitHub echoes the token's actual granted scopes and what the endpoint
    // needs in these two headers (classic PATs only -- fine-grained tokens
    // don't send them). A scope mismatch here is the single most useful
    // fact for diagnosing an otherwise-generic 404/403 from the Git Data
    // API, so surface it in the thrown message instead of leaving it in
    // dev tools where nobody will think to look for it.
    const grantedScopes = res.headers.get("x-oauth-scopes");
    const neededScopes = res.headers.get("x-accepted-oauth-scopes");
    const scopeHint =
      neededScopes && grantedScopes !== neededScopes
        ? ` [token scopes: "${grantedScopes || "none"}", endpoint wants one of: "${neededScopes}"]`
        : "";
    const err = new Error(
      `GitHub API ${options.method || "GET"} ${path} failed (${res.status}): ${message}${errorDetails}${scopeHint}`
    );
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Retries `fn` on 404s with short backoff -- used right after repo creation,
 * where GitHub's auto_init commit isn't always visible on the very next call. */
async function retryUntilReady(fn, { attempts = 5, baseDelayMs = 600 } = {}) {
  let lastErr;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (err.status !== 404) throw err;
      await sleep(baseDelayMs * (i + 1));
    }
  }
  throw lastErr;
}

/** SHA of the tip commit of `branch`, used as the anchor for a new branch. */
export async function getBranchSha(owner, repo, branch, token) {
  const ref = await githubRequest(`/repos/${owner}/${repo}/git/ref/heads/${branch}`, token);
  return ref.object.sha;
}

/** Creates a new branch pointing at `fromSha`. Idempotent: if the branch
 * already exists (422), this resolves rather than throwing, so retried
 * dispatches (e.g. after a network blip) don't fail the whole pipeline. */
export async function createBranch(owner, repo, newBranch, fromSha, token) {
  try {
    return await githubRequest(`/repos/${owner}/${repo}/git/refs`, token, {
      method: "POST",
      body: JSON.stringify({ ref: `refs/heads/${newBranch}`, sha: fromSha }),
    });
  } catch (err) {
    if (err.status === 422 && /already exists/i.test(err.body?.message || "")) {
      return { alreadyExisted: true };
    }
    throw err;
  }
}

/** Returns the current text content of `path` on `branch`, or null if the
 * file/branch/repo doesn't exist (or isn't reachable with this token) --
 * used to build a real diff against what's actually deployed, rather than
 * only ever showing a freshly-drafted policy with nothing to compare it to. */
export async function getFileContent(owner, repo, path, branch, token) {
  try {
    const file = await githubRequest(
      `/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}?ref=${encodeURIComponent(branch)}`,
      token
    );
    if (!file?.content) return null;
    return base64ToUtf8(file.content.replace(/\n/g, ""));
  } catch (err) {
    if (err.status === 404) return null;
    throw err;
  }
}

/** Opens a PR from `head` into `base`. Idempotent against "already exists". */
export async function openPullRequest(owner, repo, head, base, title, body, token) {
  try {
    return await githubRequest(`/repos/${owner}/${repo}/pulls`, token, {
      method: "POST",
      body: JSON.stringify({ title, head, base, body }),
    });
  } catch (err) {
    if (err.status === 422 && /already exists/i.test(err.body?.errors?.[0]?.message || err.body?.message || "")) {
      const existing = await githubRequest(
        `/repos/${owner}/${repo}/pulls?head=${owner}:${head}&state=open`,
        token
      );
      if (existing?.[0]) return existing[0];
    }
    throw err;
  }
}

/** Merges a PR immediately after opening it -- LegalGuard's dispatch flows
 * call this right after openPullRequest() so a generated guardrail lands on
 * `main` without a manual click, per explicit user instruction to auto-merge
 * every past and future dispatch rather than leave them open for review.
 * Treats "already merged" as success (idempotent against retries), and
 * treats "not mergeable yet" (409, e.g. GitHub still computing mergeability
 * on a just-created PR) as a one-shot-retry case rather than a hard failure. */
export async function mergePullRequest(owner, repo, pullNumber, token, { mergeMethod = "squash" } = {}) {
  try {
    return await githubRequest(`/repos/${owner}/${repo}/pulls/${pullNumber}/merge`, token, {
      method: "PUT",
      body: JSON.stringify({ merge_method: mergeMethod }),
    });
  } catch (err) {
    if (err.status === 405 && /already been merged/i.test(err.body?.message || "")) {
      return { merged: true, alreadyMerged: true };
    }
    if (err.status === 409) {
      // GitHub hasn't finished computing mergeability for a brand-new PR --
      // one short retry covers this without the caller needing to know about it.
      await sleep(1500);
      return githubRequest(`/repos/${owner}/${repo}/pulls/${pullNumber}/merge`, token, {
        method: "PUT",
        body: JSON.stringify({ merge_method: mergeMethod }),
      });
    }
    throw err;
  }
}

/**
 * Polls for the most recent run of `.github/workflows/compliance_eval.yml`
 * on `branch` and returns its real, current state -- 'success' | 'failure' |
 * 'running' | 'not_found' -- with a short retry loop since a workflow run
 * triggered by a push that just happened may not be indexed by the Actions
 * API for a second or two. This is a genuine status check against GitHub's
 * own CI result, not a simulated "tests passed" message: if OPA's `opa test`
 * step actually fails, this reports 'failure', and if the run is still
 * queued/in progress after the retries, it honestly reports 'running'
 * rather than blocking indefinitely or guessing a result.
 */
export async function checkWorkflowVerification(owner, repo, branch, token, { attempts = 4, baseDelayMs = 2000 } = {}) {
  let lastRun = null;
  for (let i = 0; i < attempts; i++) {
    try {
      const runs = await githubRequest(
        `/repos/${owner}/${repo}/actions/workflows/compliance_eval.yml/runs?branch=${encodeURIComponent(branch)}&per_page=1`,
        token
      );
      lastRun = runs?.workflow_runs?.[0] || null;
      if (lastRun && lastRun.status === "completed") {
        return { state: lastRun.conclusion === "success" ? "success" : "failure", run: lastRun };
      }
    } catch (err) {
      // A 404 here usually just means the workflow file hasn't been indexed
      // yet on a repo that was only just created -- worth retrying, not fatal.
      if (err.status !== 404) throw err;
    }
    if (i < attempts - 1) await sleep(baseDelayMs * (i + 1));
  }
  return { state: lastRun ? "running" : "not_found", run: lastRun };
}

// ---------------------------------------------------------------------------
// Atomic multi-file commits (Git Data API)
//
// A guardrail repo's bundle is ~8 files (policies/, middleware/, workflows/,
// docs) that need to land together, every time -- both on first creation and
// on every later update as the use case's matched regulations change. Doing
// that as sequential PUT /contents calls would create a separate commit per
// file and could leave a half-written repo if one call fails partway
// through. These four primitives instead build one tree and one commit, so
// the push is all-or-nothing.
// ---------------------------------------------------------------------------

/** Uploads one file's content as a Git blob, returns its SHA. */
async function createBlob(owner, repo, content, token) {
  const blob = await githubRequest(`/repos/${owner}/${repo}/git/blobs`, token, {
    method: "POST",
    body: JSON.stringify({ content: utf8ToBase64(content), encoding: "base64" }),
  });
  return blob.sha;
}

/**
 * Builds a new tree from `fileEntries` (path -> blob sha), optionally
 * layered on top of `baseTreeSha` to inherit any files not present in
 * `fileEntries`.
 *
 * `baseTreeSha` is nullable -- pass null/undefined when `fileEntries`
 * already represents the complete desired file set (as it does for
 * initializeGuardrailRepo's fully self-contained template, which includes
 * its own README.md rather than relying on the auto_init one). This was
 * confirmed necessary by direct testing: a `base_tree` referencing a
 * repo's very first (auto_init) commit tree can make POST git/trees 404
 * even though that same tree object, and every blob referenced alongside
 * it, are independently readable via GET -- reproduced identically via
 * curl outside this codebase entirely, so it isn't a bug in this request
 * construction. Omitting base_tree when it isn't needed sidesteps the
 * issue rather than working around a still-unexplained GitHub-side quirk.
 */
async function createTree(owner, repo, baseTreeSha, fileEntries, token) {
  // Fail loudly here rather than letting a missing sha turn into a vague
  // 404/422 from GitHub -- JSON.stringify silently drops `sha: undefined`
  // from the request body, so a broken blob upload would otherwise surface
  // as an unexplained failure on this call instead of the one that
  // actually broke.
  const missing = fileEntries.filter((f) => !f.sha || !f.path);
  if (missing.length > 0) {
    throw new Error(
      `createTree: ${missing.length} file(s) missing a blob sha before tree creation (paths: ${missing.map((f) => f.path || "?").join(", ")}) -- a createBlob() call likely returned an unexpected shape.`
    );
  }
  const requestBody = {
    ...(baseTreeSha ? { base_tree: baseTreeSha } : {}),
    tree: fileEntries.map(({ path, sha }) => ({ path, mode: "100644", type: "blob", sha })),
  };
  try {
    const tree = await githubRequest(`/repos/${owner}/${repo}/git/trees`, token, {
      method: "POST",
      body: JSON.stringify(requestBody),
    });
    return tree.sha;
  } catch (err) {
    // Everything before this point (missing-sha guard, empty-baseTreeSha
    // guard) already ruled out the obvious causes without success -- at
    // this point the only way to make progress is to see exactly what was
    // sent, not guess again. Attach it to the error so it surfaces through
    // the same UI/chat channel that's already working, no devtools needed.
    console.error("[createTree] failing request body:", JSON.stringify(requestBody, null, 2));
    err.message += ` | request body: ${JSON.stringify(requestBody)}`;
    throw err;
  }
}

async function createCommit(owner, repo, message, treeSha, parentSha, token) {
  const commit = await githubRequest(`/repos/${owner}/${repo}/git/commits`, token, {
    method: "POST",
    body: JSON.stringify({ message, tree: treeSha, parents: [parentSha] }),
  });
  return commit.sha;
}

async function updateRef(owner, repo, branch, commitSha, token) {
  return githubRequest(`/repos/${owner}/${repo}/git/refs/heads/${branch}`, token, {
    method: "PATCH",
    body: JSON.stringify({ sha: commitSha, force: false }),
  });
}

async function getCommitTreeSha(owner, repo, commitSha, token) {
  const commit = await githubRequest(`/repos/${owner}/${repo}/git/commits/${commitSha}`, token);
  return commit.tree.sha;
}

/**
 * Commits every entry in `files` (path -> content string) onto `branch` as a
 * single commit, in one atomic push. `branch` must already exist (create it
 * with createBranch() first) and must be at `parentSha`.
 *
 * @param {boolean} [useBaseTree] - Set false when `files` is already the
 *   complete desired file set and nothing needs to be inherited from the
 *   parent commit (see createTree()'s doc comment for why this matters --
 *   confirmed by direct testing to avoid a 404 that reproduces even via
 *   curl, independent of this client).
 */
export async function commitMultipleFiles({ owner, repo, branch, parentSha, files, message, token, useBaseTree = true }) {
  const blobs = await Promise.all(
    Object.entries(files).map(async ([path, content]) => ({
      path,
      sha: await createBlob(owner, repo, content, token),
    }))
  );
  const newTreeSha = await retryUntilReady(
    async () => {
      const baseTreeSha = useBaseTree ? await getCommitTreeSha(owner, repo, parentSha, token) : null;
      return createTree(owner, repo, baseTreeSha, blobs, token);
    },
    { attempts: 6, baseDelayMs: 800 }
  );
  const commitSha = await createCommit(owner, repo, message, newTreeSha, parentSha, token);
  await updateRef(owner, repo, branch, commitSha, token);
  return commitSha;
}

/** Creates a brand-new repository under the authenticated user's account --
 * used for the "New Guardrail Initiation" path when a regulatory shift
 * requires an entirely new independent guardrail repo rather than a version
 * bump to an existing one.
 *
 * Idempotent against re-runs: if a prior attempt already created this repo
 * (e.g. creation succeeded but a later step in initializeGuardrailRepo()
 * failed, so the caller retries from the top), GitHub's "name already
 * exists" 422 is treated the same way createBranch()/openPullRequest()
 * already treat their own "already exists" cases -- fetch and reuse the
 * existing repo instead of surfacing a name collision as fatal. */
export async function createRepository(name, description, token, { isPrivate = false } = {}) {
  try {
    return await githubRequest("/user/repos", token, {
      method: "POST",
      body: JSON.stringify({
        name,
        description,
        private: isPrivate,
        auto_init: true, // so the repo has a default branch to branch from immediately
      }),
    });
  } catch (err) {
    const nameTaken = err.status === 422 && (err.body?.errors || []).some((e) => /already exists/i.test(e.message || ""));
    if (!nameTaken) throw err;
    const user = await githubRequest("/user", token);
    return githubRequest(`/repos/${user.login}/${name}`, token);
  }
}

/**
 * Full "New Guardrail Initiation" flow: creates a brand-new repo, then pushes
 * the entire standard guardrail template (see lib/guardrailTemplate.js) as
 * ONE atomic commit on a review branch, opens a PR into the new repo's
 * default branch, and auto-merges it -- per explicit user instruction, every
 * generated guardrail lands on `main` immediately rather than sitting open
 * for manual review. (The template's own docs still flag every policy as an
 * unreviewed default-deny stub -- auto-merge changes when that human review
 * happens, not whether it's still needed.)
 *
 * @param {object} params
 * @param {string} params.repoName - from guardrailNaming.guardrailRepoName()
 * @param {string} params.description
 * @param {Record<string,string>} params.templateFiles - from buildGuardrailTemplate()
 * @param {string} params.branchName - e.g. from guardrailNaming.complianceBranchName()
 * @param {string} params.prTitle
 * @param {string} params.prBody
 * @param {string} params.token
 * @param {boolean} [params.isPrivate]
 * @returns {Promise<{repoUrl: string, prUrl: string}>}
 */
export async function initializeGuardrailRepo({
  repoName,
  description,
  templateFiles,
  branchName,
  prTitle,
  prBody,
  token,
  isPrivate = false,
}) {
  await resetPipeline({ owner: null, repo: repoName, label: `New guardrail repo: ${repoName}` });
  await appendLog({ type: "dispatch_start", repo: repoName, message: `Initializing new guardrail repo ${repoName}` });

  const repoData = await createRepository(repoName, description, token, { isPrivate });
  const owner = repoData.owner.login;
  const repo = repoData.name;
  const baseBranch = repoData.default_branch || "main";
  await setPipelineStep("repository_creation", "done", repoData.html_url);
  await appendLog({ type: "repository_creation", owner, repo, message: `Repository ${owner}/${repo} created`, url: repoData.html_url });

  // auto_init:true gives the new repo an initial commit (the README), but
  // GitHub provisions that commit asynchronously -- calling git/ref
  // immediately after a 201 from repo creation can 404 for a second or two.
  const baseSha = await retryUntilReady(() => getBranchSha(owner, repo, baseBranch, token));
  await createBranch(owner, repo, branchName, baseSha, token);
  // useBaseTree: false -- buildGuardrailTemplate() always generates a
  // complete, self-contained file set (including its own README.md), so
  // nothing needs to be inherited from the auto_init commit. This also
  // sidesteps a confirmed GitHub-side issue where a base_tree referencing
  // a repo's very first commit can make tree creation 404 even though
  // that tree and every referenced blob are independently readable.
  await commitMultipleFiles({
    owner,
    repo,
    branch: branchName,
    parentSha: baseSha,
    files: templateFiles,
    message: "LegalGuard: initial guardrail scaffold",
    token,
    useBaseTree: false,
  });
  const fileCount = Object.keys(templateFiles).length;
  await setPipelineStep("branch_and_commit", "done", `${branchName} (${fileCount} files)`);
  await appendLog({ type: "branch_and_commit", owner, repo, message: `Branch ${branchName} created, ${fileCount} files committed` });

  const pr = await openPullRequest(owner, repo, branchName, baseBranch, prTitle, prBody, token);
  await appendLog({ type: "pull_request_merge", owner, repo, message: `Pull request #${pr.number} opened`, url: pr.html_url });

  // Best-effort, same reasoning as dispatchGuardrailUpdate(): the repo, the
  // scaffold commit, and the PR all already exist by this point, so a merge
  // failure shouldn't be reported as if the whole dispatch failed.
  try {
    await mergePullRequest(owner, repo, pr.number, token);
    await setPipelineStep("pull_request_merge", "done", `#${pr.number} merged to ${baseBranch}`);
    await appendLog({ type: "pull_request_merge", owner, repo, message: `Pull request #${pr.number} merged to ${baseBranch}`, url: pr.html_url });
  } catch (err) {
    console.warn(`[githubClient] auto-merge failed for PR #${pr.number} on ${owner}/${repo}:`, err.message);
    await setPipelineStep("pull_request_merge", "failed", err.message);
    await appendLog({ type: "pull_request_merge", owner, repo, message: `Pull request #${pr.number} opened but auto-merge failed: ${err.message}`, url: pr.html_url });
  }

  try {
    await setPipelineStep("verification_check", "running", null);
    const verification = await checkWorkflowVerification(owner, repo, baseBranch, token);
    await setPipelineStep("verification_check", verification.state, verification.run?.html_url || null);
    await appendLog({
      type: "verification_check",
      owner,
      repo,
      message:
        verification.state === "success"
          ? "OPA policy tests passed"
          : verification.state === "failure"
            ? "OPA policy tests failed -- see the Actions run"
            : verification.state === "running"
              ? "OPA policy tests still running -- check GitHub Actions for the final result"
              : "No compliance_eval.yml run found yet",
      url: verification.run?.html_url,
    });
  } catch (err) {
    console.warn(`[githubClient] verification check failed for ${owner}/${repo}:`, err.message);
  }

  return { repoUrl: repoData.html_url, prUrl: pr.html_url };
}

/**
 * Regenerates and pushes the full guardrail template into an EXISTING
 * guardrail repo -- used when a use case that already has a mapped repo
 * (see repoMapping.js) picks up a new matching regulation, or an existing
 * one changes, so the whole bundled policy stays a fresh reflection of
 * every regulation currently affecting that use case rather than drifting
 * out of sync. Same instrumentation and auto-merge behavior as
 * initializeGuardrailRepo(), minus the repo-creation step since the target
 * already exists.
 *
 * useBaseTree: true (unlike initializeGuardrailRepo's false) -- this repo
 * may already contain files LegalGuard didn't generate (a human's own
 * README edits, extra docs), and those should be preserved. Every path
 * templateFiles DOES cover is still fully overwritten with the fresh
 * content, which is the point: policies/rules.rego, thresholds.json,
 * REGULATORY_PROVENANCE.md, and metadata.json all reflect the current,
 * complete regulation list on every update, not an incremental patch.
 *
 * @param {object} params
 * @param {string} params.owner
 * @param {string} params.repo
 * @param {Record<string,string>} params.templateFiles - from buildGuardrailTemplate()
 * @param {string} params.branchName
 * @param {string} params.prTitle
 * @param {string} params.prBody
 * @param {string} params.token
 * @returns {Promise<string>} the URL of the opened, now-merged pull request
 */
export async function updateGuardrailRepo({ owner, repo, templateFiles, branchName, prTitle, prBody, token }) {
  await resetPipeline({ owner, repo, label: `Updating guardrail: ${owner}/${repo}` });
  await appendLog({ type: "dispatch_start", owner, repo, message: `Updating existing guardrail repo ${owner}/${repo}` });
  // Not a new repo -- nothing for this step to do on an update.
  await setPipelineStep("repository_creation", "not_applicable", "existing repo, not created by this dispatch");

  const repoInfo = await githubRequest(`/repos/${owner}/${repo}`, token);
  const baseBranch = repoInfo.default_branch || "main";
  const baseSha = await getBranchSha(owner, repo, baseBranch, token);
  await createBranch(owner, repo, branchName, baseSha, token);
  await commitMultipleFiles({
    owner,
    repo,
    branch: branchName,
    parentSha: baseSha,
    files: templateFiles,
    message: "LegalGuard: refresh guardrail bundle for current regulation set",
    token,
    useBaseTree: true,
  });
  const fileCount = Object.keys(templateFiles).length;
  await setPipelineStep("branch_and_commit", "done", `${branchName} (${fileCount} files)`);
  await appendLog({ type: "branch_and_commit", owner, repo, message: `Branch ${branchName} created, ${fileCount} files refreshed` });

  const pr = await openPullRequest(owner, repo, branchName, baseBranch, prTitle, prBody, token);
  await appendLog({ type: "pull_request_merge", owner, repo, message: `Pull request #${pr.number} opened`, url: pr.html_url });

  try {
    await mergePullRequest(owner, repo, pr.number, token);
    await setPipelineStep("pull_request_merge", "done", `#${pr.number} merged to ${baseBranch}`);
    await appendLog({ type: "pull_request_merge", owner, repo, message: `Pull request #${pr.number} merged to ${baseBranch}`, url: pr.html_url });
  } catch (err) {
    console.warn(`[githubClient] auto-merge failed for PR #${pr.number} on ${owner}/${repo}:`, err.message);
    await setPipelineStep("pull_request_merge", "failed", err.message);
    await appendLog({ type: "pull_request_merge", owner, repo, message: `Pull request #${pr.number} opened but auto-merge failed: ${err.message}`, url: pr.html_url });
  }

  try {
    await setPipelineStep("verification_check", "running", null);
    const verification = await checkWorkflowVerification(owner, repo, baseBranch, token);
    await setPipelineStep("verification_check", verification.state, verification.run?.html_url || null);
    await appendLog({
      type: "verification_check",
      owner,
      repo,
      message:
        verification.state === "success"
          ? "OPA policy tests passed"
          : verification.state === "failure"
            ? "OPA policy tests failed -- see the Actions run"
            : verification.state === "running"
              ? "OPA policy tests still running -- check GitHub Actions for the final result"
              : "No compliance_eval.yml run found yet",
      url: verification.run?.html_url,
    });
  } catch (err) {
    console.warn(`[githubClient] verification check failed for ${owner}/${repo}:`, err.message);
  }

  return pr.html_url;
}
