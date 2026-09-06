import React, { useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, Alert, Linking } from "react-native";
import { Code2, FolderPlus, RefreshCw, Scale, GitBranchPlus, ExternalLink } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchRegulations, fetchUseCases, fetchAdminReferenceGuardrails } from "../lib/api";
import { getGitHubCredentials } from "../lib/auth";
import { getAllRepoMappings, setRepoMapping } from "../lib/repoMapping";
import { initializeGuardrailRepo, updateGuardrailRepo, getFileContent } from "../lib/githubClient";
import { guardrailRepoName, guardrailBranchName } from "../lib/guardrailNaming";
import { buildGuardrailTemplate } from "../lib/guardrailTemplate";
import { getThresholdsForSector } from "../lib/guardrailThresholds";
import { diffLines } from "../lib/diff";
import { MODALITY_ICON, RISK_TIER_STYLE } from "../lib/useCaseDisplay";
import RegulationCard from "../components/RegulationCard";
import MetadataPill from "../components/MetadataPill";

// EU AI Act-style severity gradient, matching RISK_TIER_STYLE -- used to
// order the use-case list so the riskiest ones (the ones a guardrail most
// urgently needs to cover) surface first instead of alphabetically.
const RISK_TIER_RANK = { prohibited: 0, high_risk: 1, limited_risk: 2, minimal_risk: 3, unclassified: 4 };
function sortByRiskDesc(list) {
  return [...list].sort((a, b) => (RISK_TIER_RANK[a.risk_tier] ?? 5) - (RISK_TIER_RANK[b.risk_tier] ?? 5));
}

function parseOwnerRepo(repoUrl) {
  try {
    const [, owner, repo] = new URL(repoUrl).pathname.split("/");
    return { owner, repo };
  } catch {
    return { owner: null, repo: null };
  }
}

export default function ImpactDiffScreen({ route }) {
  const [regulations, setRegulations] = useState([]);
  const [useCases, setUseCases] = useState([]);
  const [selectedUseCaseId, setSelectedUseCaseId] = useState(null);
  const [mappings, setMappings] = useState({}); // useCaseName -> { owner, repo }
  // use_case_id -> guardrail_packages row, admin-curated reference repos only
  // (is_admin_reference = true) -- see api.js's fetchAdminReferenceGuardrails.
  // Distinct from `mappings` above, which is this device's OWN generated
  // repos, never written to the shared DB.
  const [adminReferences, setAdminReferences] = useState({});
  const [busy, setBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null); // { type: 'error'|'success', text }
  // null while checking (or nothing to check), '' once confirmed there's no
  // currently-deployed bundle to diff against, a string once one's found.
  const [deployedContent, setDeployedContent] = useState(null);
  const [diffChecking, setDiffChecking] = useState(false);

  useEffect(() => {
    fetchRegulations({ limit: 200 }).then(setRegulations);
    fetchUseCases().then(setUseCases);
    getAllRepoMappings().then(setMappings);
    fetchAdminReferenceGuardrails().then((rows) => {
      setAdminReferences(Object.fromEntries(rows.map((r) => [r.use_case_id, r])));
    });
  }, []);

  // How many regulations currently match each use case -- computed once per
  // regulations load rather than per-render per-card.
  const matchCountByUseCase = useMemo(() => {
    const counts = {};
    for (const r of regulations) {
      for (const id of r.affected_use_case_ids || []) {
        counts[id] = (counts[id] || 0) + 1;
      }
    }
    return counts;
  }, [regulations]);

  // Arriving here from the Radar tab's "tap a regulation card" navigation
  // (see DashboardScreen.js) filters the use-case list down to just that
  // regulation's matches, instead of pre-selecting a regulation directly --
  // this screen is use-case-first now, so "which use cases does this
  // regulation affect" is a filter on the primary list, not a different mode.
  // React Navigation keeps this screen mounted across tab switches, so a
  // stale selection from a previous visit would otherwise stick around
  // under a newly-arrived filter -- clear it whenever the param changes.
  useEffect(() => {
    setSelectedUseCaseId(null);
  }, [route?.params?.regId]);

  const navReg = route?.params?.regId ? regulations.find((r) => r.reg_id === route.params.regId) : null;
  const listData = navReg
    ? sortByRiskDesc(useCases.filter((u) => (navReg.affected_use_case_ids || []).includes(u.id)))
    : sortByRiskDesc(useCases);

  const selectedUseCase = useCases.find((u) => u.id === selectedUseCaseId);
  // Every regulation the tagger has matched to this use case, not just the
  // one that brought you here -- the whole point of bundling is that one
  // guardrail repo reflects ALL of a use case's applicable policies at once.
  const matchedRegulations = selectedUseCase
    ? regulations.filter((r) => (r.affected_use_case_ids || []).includes(selectedUseCase.id))
    : [];
  const existingMapping = selectedUseCase ? mappings[selectedUseCase.name] : null;
  const templateFiles = selectedUseCase ? buildGuardrailTemplate(selectedUseCase, matchedRegulations) : null;
  const draftPreview = templateFiles ? templateFiles["policies/rules.rego"] : "";

  // Real diff, not a mockup: fetches whatever's actually deployed at
  // policies/rules.rego in this use case's mapped repo (if one exists yet)
  // and compares it against the freshly-regenerated bundle above, so
  // "Generated policy (draft)" shows what would actually change on an
  // update rather than just the new text in isolation.
  useEffect(() => {
    let cancelled = false;
    setDeployedContent(null);
    if (!selectedUseCaseId) {
      setDiffChecking(false);
      return;
    }
    const uc = useCases.find((u) => u.id === selectedUseCaseId);
    const mapping = uc ? mappings[uc.name] : null;
    setDiffChecking(true);
    (async () => {
      try {
        const { username, token } = await getGitHubCredentials();
        if (!token || !mapping?.repo) {
          if (!cancelled) setDeployedContent("");
          return;
        }
        const owner = mapping.owner || username;
        const content = await getFileContent(owner, mapping.repo, "policies/rules.rego", "main", token);
        if (!cancelled) setDeployedContent(content || "");
      } catch (err) {
        console.warn("[ImpactDiff] couldn't check deployed policy for diff:", err.message);
        if (!cancelled) setDeployedContent("");
      } finally {
        if (!cancelled) setDiffChecking(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedUseCaseId, mappings, useCases]);

  const handleDispatch = async () => {
    if (!selectedUseCase) return;
    if (matchedRegulations.length === 0) {
      setStatusMessage({ type: "error", text: "No regulations matched to this use case yet -- nothing to bundle." });
      return;
    }
    setBusy(true);
    setStatusMessage(null);
    try {
      const { token } = await getGitHubCredentials();
      if (!token) {
        setStatusMessage({ type: "error", text: "Connect GitHub first, in the Dispatch tab." });
        return;
      }
      const branchName = guardrailBranchName(selectedUseCase);
      const regList = matchedRegulations.map((r) => `${r.official_title} (${r.jurisdiction})`).join(", ");

      if (existingMapping?.repo) {
        const prUrl = await updateGuardrailRepo({
          owner: existingMapping.owner,
          repo: existingMapping.repo,
          templateFiles,
          branchName,
          prTitle: `[LegalGuard] Refresh guardrail bundle: ${selectedUseCase.name}`,
          prBody: `Regenerated for the current set of ${matchedRegulations.length} matched regulation(s): ${regList}.\n\nSee REGULATORY_PROVENANCE.md in this PR for the full mandate.`,
          token,
        });
        setStatusMessage({ type: "success", text: `Guardrail updated and merged: ${prUrl}` });
        Alert.alert("Guardrail updated and merged to main", prUrl);
      } else {
        const { repoUrl, prUrl } = await initializeGuardrailRepo({
          repoName: guardrailRepoName(selectedUseCase),
          description: `LegalGuard-generated guardrail for ${selectedUseCase.name}`,
          templateFiles,
          branchName,
          prTitle: `[LegalGuard] Initial guardrail: ${selectedUseCase.name}`,
          prBody: `New guardrail repository bundling ${matchedRegulations.length} matched regulation(s): ${regList}.\n\nSee REGULATORY_PROVENANCE.md in this PR for the full mandate.`,
          token,
        });
        const { owner, repo } = parseOwnerRepo(repoUrl);
        if (owner && repo) {
          await setRepoMapping(selectedUseCase.name, { owner, repo });
          setMappings((prev) => ({ ...prev, [selectedUseCase.name]: { owner, repo } }));
        }
        setStatusMessage({ type: "success", text: `Repo created and merged: ${repoUrl}` });
        Alert.alert("Repo created and merged to main", `${repoUrl}\n\n${prUrl}`);
      }
    } catch (err) {
      console.error("[ImpactDiff] dispatch failed:", err);
      setStatusMessage({ type: "error", text: err.message });
      Alert.alert("Dispatch failed", err.message);
    } finally {
      setBusy(false);
    }
  };

  // Rendered inline, directly below the selected card in the (virtualized)
  // list -- not as a FlatList footer. 451 real use cases (mined from GitHub,
  // not mock data -- see mockData.js/api.js) means this list MUST stay
  // virtualized; a plain ScrollView rendering all 451 cards at once produced
  // a >48,000px-tall content box that silently broke real mouse-wheel
  // scrolling in Chrome (keyboard PageDown still worked -- a giant
  // GPU-composited scroll layer, not a click/state bug) while leaving every
  // programmatic scrollTop check looking fine. Expanding the detail pane as
  // part of the selected row's own renderItem output keeps it inside FlatList's
  // normal per-item layout measurement instead of a footer-resize edge case.
  function renderDetailPane() {
    // Every pill here reads a value the screen already computed for other
    // purposes (existingMapping from repoMapping.js, the deployedContent vs.
    // draftPreview diff) -- no coverage percentage, version number, or commit
    // SHA gets invented for a repo we haven't actually fetched that data from.
    const inSync = !diffChecking && !!deployedContent && deployedContent === draftPreview;
    const driftDetected = !diffChecking && !!deployedContent && deployedContent !== draftPreview;
    // Admin-curated reference implementation for this use case, if the
    // maintainer has hand-built and registered one (see
    // ingestion/register_admin_reference.py) -- entirely separate from
    // existingMapping above, which is THIS device's own generated repo.
    const adminReference = adminReferences[selectedUseCase.id];
    return (
      <View style={styles.diffPane}>
        <View style={styles.detailPillRow}>
          {existingMapping?.repo ? (
            <MetadataPill label={`${existingMapping.owner}/${existingMapping.repo}`} variant="primary" icon={GitBranchPlus} />
          ) : (
            <MetadataPill label="NO REPO YET" variant="neutral" />
          )}
          {!diffChecking && deployedContent === "" && existingMapping?.repo && (
            <MetadataPill label="NO POLICY FILE DEPLOYED" variant="warning" />
          )}
          {inSync && <MetadataPill label="IN SYNC WITH DEPLOYED POLICY" variant="success" />}
          {driftDetected && <MetadataPill label="DRAFT DIFFERS FROM DEPLOYED" variant="warning" />}
        </View>

        <View style={[styles.referenceBox, adminReference ? styles.referenceBoxFound : styles.referenceBoxMissing]}>
          {adminReference ? (
            <>
              <Text style={styles.diffHeader}>Reference implementation available</Text>
              <Text style={styles.blueprintIntro}>
                A hand-built reference guardrail already exists for this use case -- open it for a working example,
                or generate your own below (they're independent; dispatching doesn't touch this one).
              </Text>
              <TouchableOpacity onPress={() => Linking.openURL(adminReference.github_repo_url)}>
                <MetadataPill
                  label={`${adminReference.github_owner}/${parseOwnerRepo(adminReference.github_repo_url).repo || adminReference.name}`}
                  variant="success"
                  icon={ExternalLink}
                />
              </TouchableOpacity>
            </>
          ) : (
            <MetadataPill label="NO REFERENCE IMPLEMENTATION YET -- YOU CAN GENERATE ONE BELOW" variant="neutral" />
          )}
        </View>

        <View style={styles.diffColumn}>
          <Text style={styles.diffHeader}>
            Policies applicable to {selectedUseCase.name} ({matchedRegulations.length})
          </Text>
          {matchedRegulations.length === 0 ? (
            <Text style={styles.remediationMissing}>
              No regulations auto-matched to this use case yet -- matches come from the keyword tagger run during
              ingestion.
            </Text>
          ) : (
            matchedRegulations.map((r) => <RegulationCard key={r.reg_id} item={r} />)
          )}
        </View>

        <View style={styles.blueprintBox}>
          <Text style={styles.diffHeader}>Blueprint of controls -- {selectedUseCase.parent_sector || "Uncategorized"}</Text>
          <Text style={styles.blueprintIntro}>
            What dispatching will actually bundle into this use case's single guardrail repo: real, citable
            thresholds where one exists, an explicit TODO where it doesn't (see guardrailThresholds.js -- no
            fabricated defaults either way).
          </Text>
          {getThresholdsForSector(selectedUseCase.parent_sector).map((t) => (
            <View key={t.key} style={styles.blueprintRow}>
              <View style={styles.blueprintRowHeader}>
                <Text style={styles.blueprintKey}>{t.key}</Text>
                <Text style={[styles.blueprintValue, t.value === null && styles.blueprintValueTodo]}>
                  {t.value === null ? "TODO" : JSON.stringify(t.value)}
                </Text>
              </View>
              <Text style={styles.blueprintCitation}>{t.citation}</Text>
            </View>
          ))}
        </View>

        <View style={styles.diffColumn}>
          <View style={styles.diffHeaderRow}>
            <Code2 size={12} color={colors.secondary} />
            <Text style={styles.diffHeader}>Generated policy (draft)</Text>
          </View>
          {diffChecking ? (
            <Text style={styles.remediationMissing}>Checking the mapped repo for a currently-deployed version…</Text>
          ) : deployedContent ? (
            <View style={styles.diffCodeBlock}>
              {diffLines(deployedContent, draftPreview).map((d, idx) => (
                <Text
                  key={idx}
                  style={[
                    styles.diffLine,
                    d.type === "remove" && styles.diffLineRemove,
                    d.type === "add" && styles.diffLineAdd,
                  ]}
                >
                  {d.type === "remove" ? "- " : d.type === "add" ? "+ " : "  "}
                  {d.line}
                </Text>
              ))}
            </View>
          ) : (
            <>
              <Text style={styles.diffCode} numberOfLines={10}>
                {draftPreview}
              </Text>
              <Text style={styles.remediationMissing}>
                {existingMapping?.repo
                  ? "No policies/rules.rego found yet at the mapped repo -- showing the full draft, not a diff against nothing."
                  : "No guardrail repo exists for this use case yet -- showing what a new one would contain."}
              </Text>
            </>
          )}
        </View>

        <TouchableOpacity style={styles.primaryButton} onPress={handleDispatch} disabled={busy || matchedRegulations.length === 0}>
          {existingMapping?.repo ? (
            <RefreshCw size={14} color={colors.primary} style={{ marginRight: 6 }} />
          ) : (
            <FolderPlus size={14} color={colors.primary} style={{ marginRight: 6 }} />
          )}
          <Text style={styles.primaryButtonText}>
            {busy
              ? "Working…"
              : existingMapping?.repo
                ? `Update Guardrail Repo (${existingMapping.owner}/${existingMapping.repo})`
                : "New Guardrail Repo"}
          </Text>
        </TouchableOpacity>
        {statusMessage && (
          <Text style={[styles.statusText, statusMessage.type === "error" ? styles.statusError : styles.statusSuccess]}>
            {statusMessage.text}
          </Text>
        )}
      </View>
    );
  }

  // A stable primitive (not a fresh object/array each render) so FlatList
  // actually re-renders the affected row when any of these change -- an
  // object-literal extraData re-renders every row on every render (expensive
  // no-op most of the time); omitting extraData entirely means FlatList never
  // re-renders rows for state outside `data` at all.
  const extraDataKey = [
    selectedUseCaseId,
    diffChecking,
    deployedContent == null ? "null" : deployedContent.length,
    busy,
    statusMessage ? `${statusMessage.type}:${statusMessage.text}` : "",
    JSON.stringify(mappings),
    Object.keys(adminReferences).length,
  ].join("|");

  return (
    <View style={styles.container}>
      <FlatList
        style={styles.scrollArea}
        contentContainerStyle={{ padding: 20 }}
        data={listData}
        keyExtractor={(item) => item.id}
        extraData={extraDataKey}
        ListHeaderComponent={
          <Text style={styles.sectionTitle}>
            {navReg ? `Use cases affected by: ${navReg.title || navReg.official_title}` : "Select a use case to review its guardrail"}
          </Text>
        }
        renderItem={({ item }) => {
          const isSelected = selectedUseCaseId === item.id;
          return (
            <View>
              <UseCaseListCard
                item={item}
                policyCount={matchCountByUseCase[item.id] || 0}
                hasRepo={!!mappings[item.name]?.repo}
                selected={isSelected}
                onPress={() => {
                  setSelectedUseCaseId(item.id === selectedUseCaseId ? null : item.id);
                  setStatusMessage(null);
                }}
              />
              {isSelected && renderDetailPane()}
            </View>
          );
        }}
      />
    </View>
  );
}

function UseCaseListCard({ item, policyCount, hasRepo, selected, onPress }) {
  const Icon = MODALITY_ICON[item.modality] || Scale;
  const riskStyle = RISK_TIER_STYLE[item.risk_tier || "unclassified"] || RISK_TIER_STYLE.unclassified;
  return (
    <TouchableOpacity style={[styles.ucRow, selected && styles.ucRowSelected]} onPress={onPress}>
      <View style={styles.ucTopRow}>
        <View style={styles.ucIconBadge}>
          <Icon size={14} color={colors.primary} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.ucTitle} numberOfLines={1}>
            {item.name}
          </Text>
          <Text style={styles.ucMeta} numberOfLines={1}>
            {item.parent_sector || "Uncategorized"} · {(item.modality || "").replace("_", " ")}
          </Text>
        </View>
      </View>
      <View style={styles.ucBottomRow}>
        <MetadataPill
          label={(item.risk_tier || "unclassified").replace("_", " ").toUpperCase()}
          backgroundColor={riskStyle.background}
          textColor={riskStyle.color}
        />
        <MetadataPill
          label={`${policyCount} polic${policyCount === 1 ? "y" : "ies"}`}
          variant="neutral"
          icon={Scale}
        />
        {hasRepo && <MetadataPill label="GUARDRAIL LINKED" variant="success" icon={GitBranchPlus} />}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  scrollArea: { flex: 1 },
  sectionTitle: { fontFamily: type.fontFamilyBold, fontSize: 16, color: colors.textMain, marginBottom: 12 },
  ucRow: {
    backgroundColor: colors.surface,
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 12,
    marginBottom: 10,
  },
  ucRowSelected: { borderColor: colors.accent, borderWidth: 1.5 },
  ucTopRow: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginBottom: 8 },
  ucIconBadge: { backgroundColor: "#F1F5F9", padding: 6, borderRadius: 6 },
  ucTitle: { fontFamily: type.fontFamilyMedium, fontSize: 13, color: colors.textMain },
  ucMeta: { fontFamily: type.fontFamily, fontSize: 11, color: colors.textMuted, marginTop: 1 },
  ucBottomRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  detailPillRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 12 },
  diffPane: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.card,
    backgroundColor: colors.surface,
    padding: 16,
    marginTop: -4,
    marginBottom: 10,
  },
  diffColumn: { marginBottom: 12 },
  diffHeaderRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 4 },
  diffHeader: {
    fontFamily: type.fontFamilyMedium,
    fontSize: 11,
    color: colors.secondary,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  diffCode: {
    fontFamily: "Courier",
    fontSize: 11,
    color: colors.primary,
    backgroundColor: colors.background,
    padding: 10,
    borderRadius: 8,
  },
  diffCodeBlock: {
    backgroundColor: colors.background,
    padding: 10,
    borderRadius: 8,
  },
  diffLine: { fontFamily: "Courier", fontSize: 11, color: colors.primary, lineHeight: 16 },
  diffLineRemove: { color: colors.danger, backgroundColor: "#EF476F15" },
  diffLineAdd: { color: colors.success, backgroundColor: "#06D6A015" },
  remediationMissing: {
    fontFamily: type.fontFamily,
    fontSize: 11,
    color: colors.textMuted,
    fontStyle: "italic",
    marginBottom: 12,
  },
  referenceBox: {
    borderWidth: 1,
    borderRadius: radius.card,
    padding: 12,
    marginBottom: 12,
  },
  referenceBoxFound: { backgroundColor: `${colors.success}14`, borderColor: `${colors.success}55` },
  referenceBoxMissing: { backgroundColor: "#F1F5F9", borderColor: colors.border },
  blueprintBox: {
    backgroundColor: "#F1F5F9",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.card,
    padding: 12,
    marginBottom: 12,
  },
  blueprintIntro: {
    fontFamily: type.fontFamily,
    fontSize: 11,
    color: colors.textMuted,
    lineHeight: 15,
    marginBottom: 8,
  },
  blueprintRow: { marginBottom: 8 },
  blueprintRowHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  blueprintKey: { fontFamily: "Courier", fontSize: 11, color: colors.primary, flexShrink: 1 },
  blueprintValue: { fontFamily: type.fontFamilyMedium, fontSize: 11, color: colors.success, marginLeft: 8 },
  blueprintValueTodo: { color: colors.warning },
  blueprintCitation: { fontFamily: type.fontFamily, fontSize: 10, color: colors.textMuted, lineHeight: 14, marginTop: 1 },
  primaryButton: {
    backgroundColor: colors.accent,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 12,
    borderRadius: radius.button,
    marginTop: 4,
  },
  primaryButtonText: { fontFamily: type.fontFamilyMedium, fontSize: 12, color: colors.primary, textAlign: "center" },
  statusText: { fontFamily: type.fontFamily, fontSize: 12, textAlign: "center", marginTop: 12, lineHeight: 16 },
  statusError: { color: colors.danger },
  statusSuccess: { color: colors.success },
});
