// Landing screen: a cloud of use-case categories. Pick any number, then
// explore the matching use cases as a deck of cards (DeckScreen). Counts
// are real -- computed from the loaded use cases, so they match what the
// deck will actually show.

import React, { useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Star, ArrowRight } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchUseCases } from "../lib/api";
import { CATEGORIES } from "../lib/categories";
import { getDiscoverState, setSelectedCategories } from "../lib/discoverState";

export default function DiscoverScreen({ navigation }) {
  const [useCases, setUseCases] = useState(null);
  const [selected, setSelected] = useState(() => new Set());
  const [starredCount, setStarredCount] = useState(0);

  useEffect(() => {
    fetchUseCases().then(setUseCases);
    getDiscoverState().then((s) => setSelected(new Set(s.selected)));
  }, []);

  useFocusEffect(
    React.useCallback(() => {
      getDiscoverState().then((s) => setStarredCount(s.starred.length));
    }, [])
  );

  const counts = useMemo(() => {
    const c = {};
    for (const uc of useCases || []) for (const slug of uc.categories || []) c[slug] = (c[slug] || 0) + 1;
    return c;
  }, [useCases]);

  const matching = useMemo(() => {
    if (!useCases) return 0;
    if (selected.size === 0) return useCases.length;
    return useCases.filter((uc) => (uc.categories || []).some((s) => selected.has(s))).length;
  }, [useCases, selected]);

  const toggle = (slug) => {
    const next = new Set(selected);
    next.has(slug) ? next.delete(slug) : next.add(slug);
    setSelected(next);
    setSelectedCategories([...next]);
  };

  const explore = () => navigation.navigate("Deck", { slugs: [...selected], mode: "explore" });

  return (
    <View style={styles.screen}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.h1}>What are you building?</Text>
            <Text style={styles.lede}>
              Pick one or more categories. Each use case below is a real system mined from GitHub or Hugging Face, or
              curated by hand.
            </Text>
          </View>
          <TouchableOpacity
            style={styles.starredBtn}
            onPress={() => navigation.navigate("Deck", { slugs: [], mode: "starred" })}
            accessibilityRole="button"
            accessibilityLabel={`Starred, ${starredCount}`}
          >
            <Star size={14} color={colors.primary} fill={starredCount ? colors.accent : "transparent"} />
            <Text style={styles.starredText}>{starredCount}</Text>
          </TouchableOpacity>
        </View>

        {!useCases ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
        ) : (
          <View style={styles.cloud}>
            {CATEGORIES.map(({ slug, label, tone }) => {
              const on = selected.has(slug);
              const n = counts[slug] || 0;
              return (
                <TouchableOpacity
                  key={slug}
                  onPress={() => toggle(slug)}
                  style={[styles.chip, on && { backgroundColor: tone, borderColor: tone }]}
                  accessibilityRole="button"
                  accessibilityState={{ selected: on }}
                >
                  <View style={[styles.dot, { backgroundColor: on ? "#FFFFFF" : tone }]} />
                  <Text style={[styles.chipText, on && styles.chipTextOn]}>{label}</Text>
                  <Text style={[styles.chipCount, on && styles.chipCountOn]}>{n}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
        )}
      </ScrollView>

      {useCases && (
        <View style={styles.footer}>
          <TouchableOpacity style={styles.cta} onPress={explore} accessibilityRole="button">
            <Text style={styles.ctaText}>
              {selected.size === 0 ? `Explore all ${matching} use cases` : `Explore ${matching} use case${matching === 1 ? "" : "s"}`}
            </Text>
            <ArrowRight size={16} color={colors.primary} />
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: 20, paddingBottom: 110, gap: 18 },
  headerRow: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  h1: { fontFamily: type.fontFamilyBold, fontSize: 24, color: colors.textMain, lineHeight: 30 },
  lede: { fontFamily: type.fontFamily, fontSize: 13, color: colors.textMuted, lineHeight: 19, marginTop: 6 },
  starredBtn: {
    flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, paddingVertical: 8,
    borderRadius: radius.chip, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
  },
  starredText: { fontFamily: type.fontFamilyMedium, fontSize: 13, color: colors.textMain },
  cloud: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 13, paddingVertical: 10,
    borderRadius: radius.chip, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
  },
  dot: { width: 9, height: 9, borderRadius: 5 },
  chipText: { fontFamily: type.fontFamilyMedium, fontSize: 13, color: colors.textMain },
  chipTextOn: { color: "#FFFFFF" },
  chipCount: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, fontVariant: ["tabular-nums"] },
  chipCountOn: { color: "rgba(255,255,255,0.78)" },
  footer: { position: "absolute", left: 0, right: 0, bottom: 0, padding: 16, backgroundColor: colors.background, borderTopWidth: 1, borderTopColor: colors.border },
  cta: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    backgroundColor: colors.accent, paddingVertical: 14, borderRadius: radius.button,
  },
  ctaText: { fontFamily: type.fontFamilyBold, fontSize: 15, color: colors.primary },
});
