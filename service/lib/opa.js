// Runs the real opa binary against a generated package. This is the reason
// the generation service exists at all: opa cannot run inside an iOS app,
// so "never hand the user a policy that fails its own tests" is only
// enforceable server-side.

import { execFile } from "node:child_process";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const OPA_TIMEOUT_MS = 30_000;

export class OpaUnavailableError extends Error {}
export class OpaVerificationError extends Error {
  constructor(message, details) {
    super(message);
    this.details = details;
  }
}

async function opa(args, cwd) {
  try {
    return await execFileAsync("opa", args, { cwd, timeout: OPA_TIMEOUT_MS, encoding: "utf8" });
  } catch (err) {
    if (err.code === "ENOENT") throw new OpaUnavailableError("opa binary not found on PATH");
    // opa test exits non-zero when tests fail and still writes JSON to
    // stdout; the caller decides what a non-zero exit means.
    return { stdout: err.stdout ?? "", stderr: err.stderr ?? "", exitCode: err.code };
  }
}

export async function opaVersion() {
  const { stdout } = await opa(["version"]);
  const match = /Version:\s*(\S+)/.exec(stdout);
  return match ? match[1] : stdout.trim().split("\n")[0];
}

/**
 * Writes the generated file map to a scratch directory, runs opa check and
 * opa test on its policies, and returns a verification report. Throws
 * OpaVerificationError if either fails -- a package that fails check or
 * its own generated tests must never reach a caller.
 *
 * @param {Record<string,string>} files - repo-relative path -> content
 */
export async function verifyPackage(files) {
  const workdir = await mkdtemp(join(tmpdir(), "legalguard-verify-"));
  try {
    for (const [relPath, content] of Object.entries(files)) {
      const full = join(workdir, relPath);
      await mkdir(dirname(full), { recursive: true });
      await writeFile(full, content);
    }
    const policies = join(workdir, "policies");

    const check = await opa(["check", "--strict", policies]);
    if (check.exitCode) {
      throw new OpaVerificationError("generated package failed opa check", {
        stage: "check",
        output: (check.stderr || check.stdout).trim(),
      });
    }

    const test = await opa(["test", "--format=json", policies]);
    let results;
    try {
      results = JSON.parse(test.stdout || "[]");
    } catch {
      throw new OpaVerificationError("opa test produced unparseable output", {
        stage: "test",
        output: (test.stderr || test.stdout).trim(),
      });
    }
    const failed = results.filter((r) => r.fail === true || r.error);
    if (test.exitCode || failed.length) {
      throw new OpaVerificationError("generated package failed its own opa tests", {
        stage: "test",
        failed: failed.map((r) => `${r.package}.${r.name}`),
        total: results.length,
      });
    }
    return { check: "ok", tests: { passed: results.length, total: results.length } };
  } finally {
    await rm(workdir, { recursive: true, force: true });
  }
}
