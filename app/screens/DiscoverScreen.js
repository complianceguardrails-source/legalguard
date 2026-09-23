// Landing screen: a cloud of use-case categories. Pick any number, then
// explore the matching use cases as a deck of cards (DeckScreen). Counts
// are real -- computed from the loaded use cases, so they match what the
// deck will actually show.

import React, { useEffect, useMemo, useRef, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Pressable, Animated, ActivityIndicator, useWindowDimensions } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Star, ArrowRight } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchUseCases } from "../lib/api";
import { CATEGORIES } from "../lib/categories";
import { getDiscoverState, setSelectedCategories } from "../lib/discoverState";

// A tag cloud, not a list: a category's type size says how many real
// systems it holds, so the shape of the corpus is visible before you pick
// anything. Deliberately mixed in size order -- sorted by size it reads as
// a chart, shuffled by a stable hash it reads as a cloud.
function cloudOrder(slug) {
  let h = 2166136261;
  for (let i = 0; i < slug.length; i++) h = ((h ^ slug.charCodeAt(i)) * 16777619) >>> 0;
  return h;
}

// Type range scales with the viewport: at 375pt the big categories have to
// stay small enough that several tags share a row, or the cloud collapses
// into a list -- which is the one thing it must not look like.
function fontRange(width) {
  if (width < 420) return [10, 15.5];
  if (width < 700) return [12, 22];
  return [13, 27];
}

function CategoryTag({ label, tone, count, max, range, on, onPress }) {
  // Size by share of the largest category, on a square root so the big
  // ones do not swamp the small ones.
  const [minFs, maxFs] = range;
  const fs = minFs + (maxFs - minFs) * Math.sqrt(Math.min(count, max) / (max || 1));
  const grow = useRef(new Animated.Value(0)).current;
  const to = (v) => Animated.spring(grow, { toValue: v, useNativeDriver: true, friction: 7, tension: 120 }).start();
  const scale = grow.interpolate({ inputRange: [0, 1], outputRange: [1, 1.12] });
  return (
    <Animated.View style={{ transform: [{ scale }] }}>
      <Pressable
        onPress={onPress}
        onHoverIn={() => to(1)}
        onHoverOut={() => to(0)}
        onPressIn={() => to(1)}
        onPressOut={() => to(0)}
        style={[
          styles.tag,
          { paddingHorizontal: fs * 0.58, paddingVertical: fs * 0.44, borderRadius: fs * 1.4 },
          on && { backgroundColor: tone, borderColor: tone },
        ]}
        accessibilityRole="button"
        accessibilityState={{ selected: on }}
        accessibilityLabel={`${label}, ${count} use cases`}
      >
        <View style={[styles.dot, { width: fs * 0.42, height: fs * 0.42, borderRadius: fs, backgroundColor: on ? "#FFFFFF" : tone }]} />
        <Text style={[styles.tagText, { fontSize: fs }, on && styles.tagTextOn]}>{label}</Text>
        <Text style={[styles.tagCount, { fontSize: Math.max(11, fs * 0.6) }, on && styles.tagCountOn]}>{count}</Text>
      </Pressable>
    </Animated.View>
  );
}

export default function DiscoverScreen({ navigation }) {
  const { width } = useWindowDimensions();
  const range = useMemo(() => fontRange(width), [width]);
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

  const cloud = useMemo(
    () => CATEGORIES.map((c) => ({ ...c, n: counts[c.slug] || 0 })).sort((a, b) => cloudOrder(a.slug) - cloudOrder(b.slug)),
    [counts]
  );
  const maxCount = useMemo(() => Math.max(1, ...Object.values(counts)), [counts]);

  return (
    <View style={styles.screen}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.h1}>What are you building?</Text>
            <Text style={styles.lede}>
              Pick as many as you like -- bigger means more systems. Every use case is a real system published on
              GitHub or the Hugging Face Hub.
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
            {cloud.map(({ slug, label, tone, n }) => (
              <CategoryTag
                key={slug}
                label={label}
                tone={tone}
                count={n}
                max={maxCount}
                range={range}
                on={selected.has(slug)}
                onPress={() => toggle(slug)}
              />
            ))}
          </View>
        )}
      </ScrollView>

      {useCases && (
        <View style={styles.footer}>
          <TouchableOpacity style={styles.cta} onPress={explore} accessibilityRole="button">
            <Text style={styles.ctaText}>
              {selected.size === 0
                ? `Explore all ${matching} use cases`
                : `Explore ${matching} use case${matching === 1 ? "" : "s"} in ${selected.size} categor${selected.size === 1 ? "y" : "ies"}`}
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
  lede: { fontFamily: type.fontFamily, fontSize: 14.5, color: colors.textMuted, lineHeight: 21, marginTop: 6 },
  starredBtn: {
    flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, paddingVertical: 8,
    borderRadius: radius.chip, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
  },
  starredText: { fontFamily: type.fontFamilyMedium, fontSize: 14.5, color: colors.textMain },
  cloud: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", justifyContent: "center", gap: 7 },
  tag: {
    flexDirection: "row", alignItems: "center", gap: 7,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
  },
  dot: {},
  tagText: { fontFamily: type.fontFamilyMedium, color: colors.textMain },
  tagTextOn: { color: "#FFFFFF" },
  tagCount: { fontFamily: type.fontFamily, color: colors.textMuted, fontVariant: ["tabular-nums"] },
  tagCountOn: { color: "rgba(255,255,255,0.78)" },
  footer: { position: "absolute", left: 0, right: 0, bottom: 0, padding: 16, backgroundColor: colors.background, borderTopWidth: 1, borderTopColor: colors.border },
  cta: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    backgroundColor: colors.accent, paddingVertical: 14, borderRadius: radius.button,
  },
  ctaText: { fontFamily: type.fontFamilyBold, fontSize: 16.5, color: colors.primary },
});
