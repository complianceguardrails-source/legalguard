// Horizon: regulation that has not bound anyone yet, and which parts of
// the catalogue it would reach when it does.
//
// The question this screen answers is "what does this land on?" -- so each
// forecast carries the use-case categories matched from its own text
// (ingestion/tag_horizon_categories.py), with the live count of published
// systems in each, and a tap straight into that deck. A forecast that
// matched no category says so rather than showing an empty box.

import React, { useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { ShieldAlert, TrendingUp, Clock, ArrowRight, AlertTriangle } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchHorizonForecasts, fetchUseCases } from "../lib/api";
import { categoryLabel, categoryTone } from "../lib/categories";
import MetadataPill from "../components/MetadataPill";

// Sooner and likelier first: what a reader should prepare for next.
const QUARTER = /([HQ])([1-4])\s*(\d{4})/i;
function arrivalKey(window) {
  const m = QUARTER.exec(window || "");
  if (!m) return Number.MAX_SAFE_INTEGER;
  const [, kind, n, year] = m;
  const month = kind.toUpperCase() === "H" ? (Number(n) - 1) * 6 : (Number(n) - 1) * 3;
  return Number(year) * 12 + month;
}

export default function HorizonScreen() {
  const navigation = useNavigation();
  const [forecasts, setForecasts] = useState(null);
  const [useCases, setUseCases] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    const [f, u] = await Promise.all([fetchHorizonForecasts(), fetchUseCases()]);
    setForecasts(f);
    setUseCases(u);
  };
  useEffect(() => { load(); }, []);

  // How many published systems sit in each category today -- the size of
  // what a forecast would land on.
  const counts = useMemo(() => {
    const c = {};
    for (const uc of useCases || []) for (const slug of uc.categories || []) c[slug] = (c[slug] || 0) + 1;
    return c;
  }, [useCases]);

  const ordered = useMemo(
    () =>
      [...(forecasts || [])].sort(
        (a, b) =>
          arrivalKey(a.estimated_arrival_window) - arrivalKey(b.estimated_arrival_window) ||
          (b.probability_percentage || 0) - (a.probability_percentage || 0)
      ),
    [forecasts]
  );

  // What the whole horizon points at: categories ranked by how many
  // forecasts reach them, so the pressure is visible before the detail.
  const pressure = useMemo(() => {
    const byCat = {};
    for (const f of forecasts || []) {
      for (const slug of f.affected_categories || []) {
        (byCat[slug] ||= { slug, forecasts: 0, systems: counts[slug] || 0 }).forecasts += 1;
      }
    }
    return Object.values(byCat).sort((a, b) => b.forecasts - a.forecasts || b.systems - a.systems);
  }, [forecasts, counts]);

  const openDeck = (slug) =>
    navigation.navigate("DiscoverFlow", { screen: "Deck", params: { slugs: [slug], mode: "explore" } });

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} tintColor={colors.primary} />}
    >
      <Text style={styles.sectionTitle}>Upstream policy forecasts</Text>
      <Text style={styles.sectionSubtitle}>
        Regulation that is coming but not yet binding, and the parts of the catalogue it would reach. Categories are
        matched from each forecast's own text; tap one to see the systems in it today.
      </Text>

      {!forecasts ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
      ) : (
        <>
          {pressure.length > 0 && (
            <View style={styles.pressureCard}>
              <Text style={styles.pressureTitle}>Where the pressure is</Text>
              <Text style={styles.pressureNote}>
                Categories by how many forecasts reach them, with the systems you would have to review in each.
              </Text>
              {pressure.map((p) => (
                <TouchableOpacity key={p.slug} style={styles.pressureRow} onPress={() => openDeck(p.slug)} accessibilityRole="button">
                  <View style={[styles.dot, { backgroundColor: categoryTone(p.slug) }]} />
                  <Text style={styles.pressureLabel} numberOfLines={1}>{categoryLabel(p.slug)}</Text>
                  <Text style={styles.pressureCount}>
                    {p.forecasts} forecast{p.forecasts === 1 ? "" : "s"} · {p.systems} system{p.systems === 1 ? "" : "s"}
                  </Text>
                  <ArrowRight size={14} color={colors.textMuted} />
                </TouchableOpacity>
              ))}
            </View>
          )}

          {ordered.map((item) => (
            <View key={item.id} style={styles.card}>
              <View style={styles.cardHeader}>
                <MetadataPill label={item.target_jurisdiction} variant="neutral" icon={ShieldAlert} />
                <View style={{ flexDirection: "row", gap: 6 }}>
                  <MetadataPill
                    label={`${item.probability_percentage}% probability`}
                    variant={item.probability_percentage > 75 ? "success" : "warning"}
                  />
                  <MetadataPill label={item.estimated_arrival_window} variant="info" icon={Clock} />
                </View>
              </View>

              <Text style={styles.billTitle}>{item.projected_bill_name}</Text>
              {/* trend_key is only set by generate_horizon_forecasts.py, from a
                  real quarter-over-quarter acceleration in ingested regulations
                  -- it separates those from the hand-authored examples in
                  database/seed.sql, which have no trend_key. */}
              {!!item.trend_key && (
                <MetadataPill label="Real trend signal, not illustrative" variant="primary" icon={TrendingUp} />
              )}

              <Text style={styles.subHeading}>Use-case categories it would reach</Text>
              {(item.affected_categories || []).length === 0 ? (
                <View style={styles.noMatch}>
                  <AlertTriangle size={13} color={colors.textMuted} />
                  <Text style={styles.noMatchText}>
                    No category matched this forecast's text. It may still reach systems here -- it just cannot be
                    placed automatically.
                  </Text>
                </View>
              ) : (
                <View style={styles.chipContainer}>
                  {item.affected_categories.map((slug) => (
                    <TouchableOpacity
                      key={slug}
                      style={[styles.catChip, { backgroundColor: categoryTone(slug) }]}
                      onPress={() => openDeck(slug)}
                      accessibilityRole="button"
                      accessibilityLabel={`${categoryLabel(slug)}, ${counts[slug] || 0} systems`}
                    >
                      <Text style={styles.catChipText}>{categoryLabel(slug)}</Text>
                      <Text style={styles.catChipCount}>{counts[slug] || 0}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}

              <Text style={styles.subHeading}>Why it is coming</Text>
              <Text style={styles.contextText}>{item.underlying_driver_description}</Text>

              {(item.upstream_catalyst_drivers || []).length > 0 && (
                <View style={[styles.chipContainer, { marginTop: 8 }]}>
                  {item.upstream_catalyst_drivers.map((catalyst, idx) => (
                    <MetadataPill key={idx} label={catalyst.replace(/_/g, " ")} variant="danger" icon={TrendingUp} />
                  ))}
                </View>
              )}

              {!!item.suggested_proactive_guardrail_logic && (
                <>
                  <Text style={styles.subHeading}>What it would require</Text>
                  <Text style={styles.contextText}>{item.suggested_proactive_guardrail_logic}</Text>
                </>
              )}
            </View>
          ))}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  sectionTitle: { fontFamily: type.fontFamilyBold, fontSize: 22, color: colors.textMain, marginBottom: 6 },
  sectionSubtitle: { fontFamily: type.fontFamily, fontSize: 13.5, color: colors.textMuted, lineHeight: 19, marginBottom: 18 },
  pressureCard: {
    backgroundColor: colors.surface, borderRadius: radius.card, borderWidth: 1, borderColor: colors.border,
    padding: 16, marginBottom: 18, gap: 4,
  },
  pressureTitle: { fontFamily: type.fontFamilyBold, fontSize: 15, color: colors.textMain },
  pressureNote: { fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMuted, lineHeight: 18, marginBottom: 6 },
  pressureRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.border },
  dot: { width: 9, height: 9, borderRadius: 5 },
  pressureLabel: { flex: 1, fontFamily: type.fontFamilyMedium, fontSize: 13.5, color: colors.textMain },
  pressureCount: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, fontVariant: ["tabular-nums"] },
  card: {
    backgroundColor: colors.surface, borderRadius: radius.card, padding: 16, marginBottom: 18,
    borderWidth: 1, borderColor: colors.border,
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10, flexWrap: "wrap", gap: 6 },
  billTitle: { fontFamily: type.fontFamilyBold, fontSize: 16, color: colors.textMain, marginBottom: 4, marginTop: 6, lineHeight: 22 },
  subHeading: {
    fontFamily: type.fontFamilyMedium, fontSize: 11.5, color: colors.secondary, marginTop: 12, marginBottom: 6,
    textTransform: "uppercase", letterSpacing: 0.5,
  },
  chipContainer: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  catChip: { flexDirection: "row", alignItems: "center", gap: 7, paddingHorizontal: 11, paddingVertical: 7, borderRadius: 999 },
  catChipText: { fontFamily: type.fontFamilyMedium, fontSize: 12.5, color: "#FFFFFF" },
  catChipCount: { fontFamily: type.fontFamily, fontSize: 11.5, color: "rgba(255,255,255,0.8)", fontVariant: ["tabular-nums"] },
  noMatch: { flexDirection: "row", alignItems: "flex-start", gap: 7, backgroundColor: colors.background, borderRadius: 8, padding: 10, borderWidth: 1, borderColor: colors.border },
  noMatchText: { flex: 1, fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, lineHeight: 17 },
  contextText: { fontFamily: type.fontFamily, fontSize: 13, color: colors.textMain, lineHeight: 19 },
});
