import React, { useCallback, useEffect, useState } from "react";
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, Alert, Linking } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import {
  GitBranch,
  CheckCircle2,
  XCircle,
  Rocket,
  FolderPlus,
  GitCommit,
  GitPullRequest,
  ShieldCheck,
  Clock,
} from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { getGitHubCredentials, saveGitHubCredentials, clearGitHubCredentials, verifyToken } from "../lib/auth";
import { getPipelineStatus, getRecentLogs } from "../lib/traceability";
import MetadataPill from "../components/MetadataPill";

const STATUS_LABEL = {
  done: "DONE",
  running: "RUNNING",
  failed: "FAILED",
  pending: "PENDING",
  not_applicable: "N/A",
};

const STATUS_VARIANT = {
  done: "success",
  running: "warning",
  failed: "danger",
  pending: "neutral",
  not_applicable: "neutral",
};

const PIPELINE_STEP_DISPLAY = [
  { key: "repository_creation", label: "Repository Creation", Icon: FolderPlus },
  { key: "branch_and_commit", label: "Branch & File Commit", Icon: GitCommit },
  { key: "pull_request_merge", label: "Pull Request & Merge", Icon: GitPullRequest },
  { key: "verification_check", label: "Verification Check", Icon: ShieldCheck },
];

const STATUS_COLORS = {
  done: "success",
  running: "warning",
  failed: "danger",
  pending: "muted",
  not_applicable: "muted",
};

export default function GitOpsConsoleScreen() {
  const [username, setUsername] = useState(null);
  const [tokenInput, setTokenInput] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null); // { type: 'error'|'success', text }
  const [pipeline, setPipeline] = useState(null);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    (async () => {
      const creds = await getGitHubCredentials();
      setUsername(creds.username);
    })();
  }, []);

  // Re-read on every focus (not just mount) -- a dispatch made from the
  // Audit tab writes real events while this screen isn't mounted, so a
  // one-time load on mount would show stale state the next time you switch
  // back here.
  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        const [p, l] = await Promise.all([getPipelineStatus(), getRecentLogs(30)]);
        if (!cancelled) {
          setPipeline(p);
          setLogs(l);
        }
      })();
      return () => {
        cancelled = true;
      };
    }, [])
  );

  const connect = async () => {
    if (!tokenInput.trim()) return;
    setVerifying(true);
    setStatusMessage(null);
    try {
      const user = await verifyToken(tokenInput.trim());
      await saveGitHubCredentials(user.login, tokenInput.trim());
      setUsername(user.login);
      setTokenInput("");
      // Alert.alert is a no-op on react-native-web in most setups, so the
      // inline banner below is the message that actually renders there;
      // Alert still fires as a bonus on native iOS/Android.
      Alert.alert("Connected", `Authenticated as @${user.login}. Token stored securely on this device.`);
    } catch (err) {
      console.error("[GitOpsConsole] connect failed:", err);
      setStatusMessage({ type: "error", text: err.message });
      Alert.alert("Connection failed", err.message);
    } finally {
      setVerifying(false);
    }
  };

  const disconnect = async () => {
    await clearGitHubCredentials();
    setUsername(null);
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={{ paddingBottom: 20 }}>
        <View style={styles.pageHeader}>
              <View style={styles.pageHeaderTitleRow}>
                <Rocket size={18} color={colors.primary} />
                <Text style={styles.pageTitle}>GitOps Dispatch Console</Text>
              </View>
              <Text style={styles.pageSubtitle}>Real-time deployment pipeline & traceability</Text>
            </View>

            <View style={styles.authCard}>
              <View style={styles.authHeaderRow}>
                <GitBranch size={18} color={colors.primary} />
                <Text style={styles.authTitle}>GitHub Connection</Text>
              </View>
              {username ? (
                <View style={styles.connectedRow}>
                  <MetadataPill label={`CONNECTED AS @${username.toUpperCase()}`} variant="success" icon={CheckCircle2} />
                  <TouchableOpacity onPress={disconnect} style={{ marginLeft: "auto" }}>
                    <XCircle size={16} color={colors.danger} />
                  </TouchableOpacity>
                </View>
              ) : (
                <>
                  <Text style={styles.helperText}>
                    Use a classic Personal Access Token with `repo` AND `workflow` scope -- tap the link below (both
                    are pre-checked). `workflow` is required separately from `repo` because every guardrail repo
                    includes a `.github/workflows/compliance_eval.yml` file, and GitHub rejects any write touching
                    `.github/workflows/` without it. Fine-grained tokens can't create new repositories unless you
                    separately grant "Administration" under Account permissions, so classic is simpler and more
                    reliable here. Stored in this device's secure keychain, never sent to LegalGuard's shared
                    backend -- every GitHub call runs directly from your phone.
                  </Text>
                  <TextInput
                    style={styles.tokenInput}
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                    placeholderTextColor={colors.textMuted}
                    secureTextEntry
                    autoCapitalize="none"
                    value={tokenInput}
                    onChangeText={setTokenInput}
                  />
                  <TouchableOpacity style={styles.connectButton} onPress={connect} disabled={verifying}>
                    <Text style={styles.connectButtonText}>{verifying ? "Verifying…" : "Connect"}</Text>
                  </TouchableOpacity>
                  {statusMessage && (
                    <Text
                      style={[styles.statusText, statusMessage.type === "error" ? styles.statusError : styles.statusSuccess]}
                    >
                      {statusMessage.text}
                    </Text>
                  )}
                  <TouchableOpacity onPress={() => Linking.openURL("https://github.com/settings/tokens/new?scopes=repo,workflow")}>
                    <Text style={styles.linkText}>Create a token on GitHub →</Text>
                  </TouchableOpacity>
                </>
              )}
            </View>

            <View style={styles.pipelineCard}>
              <View style={styles.pipelineHeaderRow}>
                <Text style={styles.authTitle}>Pipeline Status</Text>
                <View style={styles.liveDotRow}>
                  <View style={[styles.liveDot, { backgroundColor: pipeline ? colors.accent : colors.border }]} />
                  <Text style={styles.pipelineSubtext} numberOfLines={1}>
                    {pipeline ? pipeline.label : "No dispatch yet"}
                  </Text>
                </View>
              </View>
              <View style={styles.pipelineTilesRow}>
                {PIPELINE_STEP_DISPLAY.map(({ key, label, Icon }) => {
                  const step = pipeline?.steps?.[key];
                  const status = step?.status || "pending";
                  const toneName = STATUS_COLORS[status] || "muted";
                  const tone = toneName === "muted" ? colors.textMuted : colors[toneName];
                  return (
                    <View key={key} style={styles.pipelineTile}>
                      <View style={[styles.pipelineIconBadge, { backgroundColor: `${tone}22` }]}>
                        <Icon size={16} color={tone} />
                      </View>
                      <Text style={styles.pipelineTileLabel} numberOfLines={2}>
                        {label}
                      </Text>
                      <MetadataPill label={STATUS_LABEL[status] || "PENDING"} variant={STATUS_VARIANT[status] || "neutral"} />
                    </View>
                  );
                })}
              </View>
            </View>

            <View style={styles.logsCard}>
              <Text style={styles.authTitle}>Traceability Logs</Text>
              {logs.length === 0 ? (
                <Text style={styles.helperText}>
                  No dispatches yet -- create or update a guardrail from the Audit tab to see real pipeline events
                  here.
                </Text>
              ) : (
                logs.map((entry, idx) => {
                  const failed = /failed/i.test(entry.message || "");
                  const Icon = failed ? XCircle : CheckCircle2;
                  const tone = failed ? colors.danger : colors.success;
                  return (
                    <View key={idx} style={styles.logRow}>
                      <Icon size={14} color={tone} style={{ marginTop: 1 }} />
                      <View style={{ flex: 1 }}>
                        <Text style={styles.logMessage}>{entry.message}</Text>
                        <View style={styles.logMetaRow}>
                          <Clock size={10} color={colors.textMuted} />
                          <Text style={styles.logTime}>{new Date(entry.at).toLocaleString()}</Text>
                        </View>
                      </View>
                    </View>
                  );
                })
              )}
            </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  pageHeader: { paddingHorizontal: 20, paddingTop: 20 },
  pageHeaderTitleRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  pageTitle: { fontFamily: type.fontFamilyBold, fontSize: 18, color: colors.textMain },
  pageSubtitle: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  authCard: {
    margin: 20,
    marginBottom: 8,
    backgroundColor: colors.surface,
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
  },
  authHeaderRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  authTitle: { fontFamily: type.fontFamilyBold, fontSize: 14, color: colors.textMain },
  helperText: { fontFamily: type.fontFamily, fontSize: 11, color: colors.textMuted, lineHeight: 16, marginBottom: 10 },
  tokenInput: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.button,
    padding: 10,
    fontFamily: type.fontFamily,
    fontSize: 13,
    color: colors.textMain,
    marginBottom: 10,
  },
  connectButton: {
    backgroundColor: colors.accent,
    borderRadius: radius.button,
    paddingVertical: 10,
    alignItems: "center",
    marginBottom: 8,
  },
  connectButtonText: { fontFamily: type.fontFamilyMedium, fontSize: 12, color: colors.primary },
  linkText: { fontFamily: type.fontFamily, fontSize: 11, color: colors.secondary, textAlign: "center" },
  statusText: { fontFamily: type.fontFamily, fontSize: 12, textAlign: "center", marginBottom: 8, lineHeight: 16 },
  statusError: { color: colors.danger },
  statusSuccess: { color: colors.success },
  pipelineCard: {
    marginHorizontal: 20,
    marginBottom: 8,
    backgroundColor: colors.surface,
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
  },
  pipelineHeaderRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  liveDotRow: { flexDirection: "row", alignItems: "center", gap: 5, maxWidth: 160 },
  liveDot: { width: 6, height: 6, borderRadius: 3 },
  pipelineSubtext: { fontFamily: type.fontFamily, fontSize: 10, color: colors.textMuted },
  pipelineTilesRow: { flexDirection: "row", gap: 8 },
  pipelineTile: { flex: 1, alignItems: "center", gap: 6 },
  pipelineIconBadge: { padding: 10, borderRadius: 10 },
  pipelineTileLabel: { fontFamily: type.fontFamily, fontSize: 9, color: colors.textMuted, textAlign: "center" },
  logsCard: {
    marginHorizontal: 20,
    marginBottom: 8,
    backgroundColor: colors.surface,
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
  },
  logRow: { flexDirection: "row", gap: 8, marginTop: 10 },
  logMessage: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMain, lineHeight: 16 },
  logMetaRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 2 },
  logTime: { fontFamily: type.fontFamily, fontSize: 10, color: colors.textMuted },
  connectedRow: { flexDirection: "row", alignItems: "center", gap: 8 },
});
