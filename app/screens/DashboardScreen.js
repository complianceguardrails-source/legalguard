import React, { useCallback, useEffect, useState } from "react";
import { View, Text, ScrollView, StyleSheet, RefreshControl } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { Database, Scale, GitBranchPlus } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchPendingRegulations, fetchUseCaseCount, fetchRegulationCount } from "../lib/api";
import { getAllRepoMappings } from "../lib/repoMapping";
import RegulationCard from "../components/RegulationCard";

export default function DashboardScreen() {
  const navigation = useNavigation();
  // useCaseCount/regulationCount are real counts from the shared reference
  // database; templatesGenerated is deliberately NOT from that shared
  // backend -- it's read from this device's own local repoMapping.js
  // storage, since the shared DB has no write path for guardrail activity
  // (by design -- see docs/POSTGREST.md) and guardrail dispatch is a
  // per-user, per-device thing, not a cross-user statistic.
  const [useCaseCount, setUseCaseCount] = useState(0);
  const [regulationCount, setRegulationCount] = useState(0);
  const [templatesGenerated, setTemplatesGenerated] = useState(0);
  const [pendingRegulations, setPendingRegulations] = useState([]);
  const [totalPending, setTotalPending] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [ucCount, regCount, mappings, pending] = await Promise.all([
      fetchUseCaseCount(),
      fetchRegulationCount(),
      getAllRepoMappings(),
      fetchPendingRegulations(),
    ]);
    setUseCaseCount(ucCount);
    setRegulationCount(regCount);
    setTemplatesGenerated(Object.keys(mappings).length);
    setPendingRegulations(pending.rows);
    setTotalPending(pending.total);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={{ padding: 20 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
    >
      <View style={styles.metricsRow}>
        <MetricTile icon={Database} label="Finance Use Cases" value={useCaseCount} tone="success" />
        <MetricTile icon={Scale} label="Regulatory Acts" value={regulationCount} tone="warning" />
        <MetricTile icon={GitBranchPlus} label="Composite Guardrails" value={templatesGenerated} tone="info" />
      </View>

      <Text style={styles.sectionTitle}>Pending Regulatory Screens</Text>
      {pendingRegulations.length === 0 && (
        <Text style={styles.emptyText}>No pending guardrail changes — you're caught up.</Text>
      )}
      {pendingRegulations.map((reg) => (
        <RegulationCard
          key={reg.reg_id}
          item={reg}
          onPress={() => navigation.navigate("ImpactDiff", { regId: reg.reg_id })}
        />
      ))}
      {pendingRegulations.length > 0 && (
        <Text style={styles.reviewHint}>
          {totalPending > pendingRegulations.length
            ? `Showing ${pendingRegulations.length} of ${totalPending} pending regulations — open the Audit tab to review the rest.`
            : "Open the Audit tab to review and dispatch a guardrail update."}
        </Text>
      )}
    </ScrollView>
  );
}

// Brand-accent coding for visual distinction between the three tiles, not a
// green/amber/red good/bad scale -- these are informational counts, not
// status indicators (a high "templates generated" count is a good thing,
// so it deliberately isn't colored "danger" the way Base44's original
// Breaches tile was).
const TONE_COLORS = {
  success: colors.accentHover,
  warning: colors.primary,
  // Same green as the "Primary source" badge under each regulation card.
  info: colors.success,
};

function MetricTile({ icon: Icon, label, value, tone }) {
  const valueColor = TONE_COLORS[tone] || colors.primary;
  return (
    <View style={styles.metricTile}>
      <Icon size={18} color={valueColor} />
      <Text style={[styles.metricValue, { color: valueColor }]}>{value}</Text>
      <Text style={[styles.metricLabel, { color: valueColor }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  metricsRow: { flexDirection: "row", gap: 10, marginBottom: 24 },
  metricTile: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 12,
    alignItems: "center",
    gap: 4,
  },
  metricValue: { fontFamily: type.fontFamilyBold, fontSize: 20, color: colors.textMain },
  metricLabel: { fontFamily: type.fontFamilyBold, fontSize: 13, textAlign: "center" },
  sectionTitle: { fontFamily: type.fontFamilyBold, fontSize: 18, color: colors.textMain, marginBottom: 10 },
  emptyText: { fontFamily: type.fontFamily, fontSize: 13, color: colors.textMuted },
  reviewHint: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, fontStyle: "italic", marginTop: 4 },
});
