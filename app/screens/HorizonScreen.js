import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from "react-native";
import { ShieldAlert, TrendingUp, HelpCircle, GitPullRequest, Layers, Clock } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchHorizonForecasts } from "../lib/api";
import MetadataPill from "../components/MetadataPill";

export default function HorizonScreen() {
  const [forecasts, setForecasts] = useState([]);
  const [staged, setStaged] = useState({});

  useEffect(() => {
    fetchHorizonForecasts().then(setForecasts);
  }, []);

  const preStage = (item) => {
    setStaged((prev) => ({ ...prev, [item.id]: true }));
    Alert.alert(
      "Proactive staging branch queued",
      `LegalGuard will open a [PROACTIVE-STAGING] PR on your configured repos for:\n\n${item.projected_bill_name}\n\n` +
        `This is informational only -- it does not touch your default branch until you review it.`
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>
      <Text style={styles.sectionTitle}>Upstream Policy Forecasts</Text>
      <Text style={styles.sectionSubtitle}>
        Tracking predictive regulatory indicators driven by market, capability, and geopolitical catalysts before
        they become binding law.
      </Text>

      {forecasts.map((item) => (
        <View key={item.id} style={styles.card}>
          <View style={styles.cardHeader}>
            <MetadataPill label={item.target_jurisdiction} variant="neutral" icon={ShieldAlert} />
            <View style={{ flexDirection: "row", gap: 6 }}>
              <MetadataPill
                label={`${item.probability_percentage}% PROBABILITY`}
                variant={item.probability_percentage > 75 ? "success" : "warning"}
              />
              <MetadataPill label={item.estimated_arrival_window} variant="info" icon={Clock} />
            </View>
          </View>

          <Text style={styles.billTitle}>{item.projected_bill_name}</Text>
          {/* trend_key is only set by generate_horizon_forecasts.py, derived
              from a real quarter-over-quarter acceleration in ingested
              regulations -- distinguishes it from the hand-authored
              examples in database/seed.sql, which have no trend_key. */}
          {!!item.trend_key && (
            <MetadataPill label="REAL TREND SIGNAL, NOT ILLUSTRATIVE" variant="primary" icon={TrendingUp} />
          )}

          <Text style={styles.subHeading}>Primary upstream drivers</Text>
          <View style={styles.chipContainer}>
            {(item.upstream_catalyst_drivers || []).map((catalyst, idx) => (
              <MetadataPill key={idx} label={catalyst.replace(/_/g, " ").toUpperCase()} variant="danger" icon={TrendingUp} />
            ))}
          </View>

          <Text style={styles.subHeading}>Narrative driver context</Text>
          <Text style={styles.contextText}>{item.underlying_driver_description}</Text>

          <Text style={styles.subHeading}>Profile impact blast radius</Text>
          <View style={styles.radiusBox}>
            {(item.impact_blast_radius_summary || "").split(",").map((repo, idx) => (
              <View key={idx} style={styles.repoRow}>
                <Layers size={12} color={colors.textMuted} style={{ marginRight: 6 }} />
                <Text style={styles.repoText}>{repo.trim()}</Text>
              </View>
            ))}
          </View>

          <View style={styles.actionRow}>
            <TouchableOpacity style={styles.secondaryButton}>
              <HelpCircle size={14} color={colors.secondary} style={{ marginRight: 6 }} />
              <Text style={styles.secondaryButtonText}>Inspect Draft Logic</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.primaryButton, staged[item.id] && styles.disabledButton]}
              onPress={() => preStage(item)}
              disabled={!!staged[item.id]}
            >
              <GitPullRequest size={14} color={staged[item.id] ? colors.textMuted : colors.primary} style={{ marginRight: 6 }} />
              <Text style={[styles.primaryButtonText, staged[item.id] && styles.disabledButtonText]}>
                {staged[item.id] ? "Pre-Staged" : "Pre-Stage PR"}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  sectionTitle: { fontFamily: type.fontFamilyBold, fontSize: 20, color: colors.textMain, marginBottom: 6 },
  sectionSubtitle: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, lineHeight: 17, marginBottom: 18 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.card,
    padding: 16,
    marginBottom: 18,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10, flexWrap: "wrap", gap: 6 },
  billTitle: { fontFamily: type.fontFamilyBold, fontSize: 15, color: colors.textMain, marginBottom: 4, marginTop: 6 },
  subHeading: {
    fontFamily: type.fontFamilyMedium,
    fontSize: 11,
    color: colors.secondary,
    marginTop: 10,
    marginBottom: 6,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  chipContainer: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  contextText: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, lineHeight: 17 },
  radiusBox: {
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  repoRow: { flexDirection: "row", alignItems: "center", marginVertical: 2 },
  repoText: { fontFamily: type.fontFamily, fontSize: 12, color: "#475569" },
  actionRow: { flexDirection: "row", gap: 10, marginTop: 12 },
  primaryButton: {
    flex: 1,
    backgroundColor: colors.accent,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 10,
    borderRadius: radius.button,
  },
  primaryButtonText: { fontFamily: type.fontFamilyMedium, fontSize: 12, color: colors.primary },
  secondaryButton: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: "#CBD5E1",
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 10,
    borderRadius: radius.button,
  },
  secondaryButtonText: { fontFamily: type.fontFamilyMedium, fontSize: 12, color: colors.secondary },
  disabledButton: { backgroundColor: colors.border },
  disabledButtonText: { color: colors.textMuted },
});
