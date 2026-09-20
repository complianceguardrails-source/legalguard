// Trending risks: the day's stories from trusted financial outlets and
// regulators, each mapped to the granular risks it covers (see
// ingestion/risk_news_keywords.py for how). Filter by family; tap a story
// to read it at the source. Nothing here is written by us -- title and
// summary are the outlet's own feed text, and the mapping is shown as the
// risk chips so a reader can judge it.

import React, { useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Linking, RefreshControl, ActivityIndicator } from "react-native";
import { ExternalLink, Landmark, Newspaper } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchRiskNews } from "../lib/api";
import { RISK_FAMILIES, RISK_BY_SLUG } from "../lib/riskTaxonomy";

const FAMILY_LABEL = Object.fromEntries(RISK_FAMILIES.map((f) => [f.key, f.label]));
const DAY = 24 * 60 * 60 * 1000;

function bucket(story, now) {
  const t = story.published_at ? new Date(story.published_at).getTime() : new Date(story.fetched_at).getTime();
  const age = now - t;
  if (age < DAY) return "Today";
  if (age < 2 * DAY) return "Yesterday";
  if (age < 7 * DAY) return "This week";
  return "Earlier";
}

function when(story) {
  const d = new Date(story.published_at || story.fetched_at);
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export default function TrendingRisksScreen() {
  const [stories, setStories] = useState(null);
  const [family, setFamily] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => setStories(await fetchRiskNews());
  useEffect(() => { load(); }, []);

  const counts = useMemo(() => {
    const c = {};
    for (const s of stories || []) for (const f of s.families || []) c[f] = (c[f] || 0) + 1;
    return c;
  }, [stories]);

  const sections = useMemo(() => {
    const now = Date.now();
    const rows = (stories || []).filter((s) => !family || (s.families || []).includes(family));
    const order = ["Today", "Yesterday", "This week", "Earlier"];
    const by = {};
    for (const s of rows) (by[bucket(s, now)] ||= []).push(s);
    return order.filter((k) => by[k]).map((k) => ({ title: k, rows: by[k] }));
  }, [stories, family]);

  return (
    <View style={styles.screen}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} tintColor={colors.primary} />}
      >
        <Text style={styles.h1}>Trending risks</Text>
        <Text style={styles.lede}>
          Stories from trusted financial outlets and regulators, each placed against the risk it reports on. Tap a story to
          read it at the source.
        </Text>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
          <Chip label="All" count={(stories || []).length} on={!family} onPress={() => setFamily(null)} />
          {RISK_FAMILIES.map((f) => (
            <Chip key={f.key} label={f.label} count={counts[f.key] || 0} on={family === f.key} onPress={() => setFamily(family === f.key ? null : f.key)} />
          ))}
        </ScrollView>

        {!stories ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
        ) : sections.length === 0 ? (
          <Text style={styles.empty}>No stories matched {family ? FAMILY_LABEL[family].toLowerCase() : "any risk"} yet. The feeds are read on a schedule; pull to refresh.</Text>
        ) : (
          sections.map((sec) => (
            <View key={sec.title} style={styles.section}>
              <Text style={styles.sectionTitle}>{sec.title}</Text>
              {sec.rows.map((s) => <Story key={s.story_id} story={s} />)}
            </View>
          ))
        )}
      </ScrollView>
    </View>
  );
}

function Chip({ label, count, on, onPress }) {
  return (
    <TouchableOpacity onPress={onPress} style={[styles.chip, on && styles.chipOn]} accessibilityRole="button" accessibilityState={{ selected: on }}>
      <Text style={[styles.chipText, on && styles.chipTextOn]}>{label}</Text>
      <Text style={[styles.chipCount, on && styles.chipCountOn]}>{count}</Text>
    </TouchableOpacity>
  );
}

function Story({ story }) {
  const Icon = story.outlet_kind === "regulator" ? Landmark : Newspaper;
  // Google News query feeds hand back a redirect link and a summary that
  // is the title again; show the outlet, not the redirector, and no echo.
  const domain = story.url.replace(/^https?:\/\//, "").split("/")[0];
  const viaGoogle = domain.includes("news.google.com");
  const summary = story.summary && !story.summary.startsWith(story.title.slice(0, 40)) ? story.summary : null;
  return (
    <TouchableOpacity style={styles.card} onPress={() => Linking.openURL(story.url)} accessibilityRole="link">
      <View style={styles.cardMeta}>
        <Icon size={13} color={colors.textMuted} />
        <Text style={styles.outlet}>{story.outlet}</Text>
        <Text style={styles.date}>{when(story)}</Text>
      </View>
      <Text style={styles.title}>{story.title}</Text>
      {!!summary && <Text style={styles.summary} numberOfLines={3}>{summary}</Text>}
      <View style={styles.risks}>
        {(story.risk_slugs || []).map((slug) => (
          <View key={slug} style={styles.riskTag}>
            <Text style={styles.riskTagText}>{RISK_BY_SLUG[slug]?.label || slug}</Text>
          </View>
        ))}
      </View>
      <View style={styles.linkRow}>
        <ExternalLink size={12} color={colors.secondary} />
        <Text style={styles.link} numberOfLines={1}>{viaGoogle ? `${story.outlet} via Google News` : domain}</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: 20, gap: 14 },
  h1: { fontFamily: type.fontFamilyBold, fontSize: 24, color: colors.textMain, lineHeight: 30 },
  lede: { fontFamily: type.fontFamily, fontSize: 13, color: colors.textMuted, lineHeight: 19 },
  chips: { flexDirection: "row", gap: 8, paddingVertical: 2 },
  chip: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.chip, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  chipOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontFamily: type.fontFamilyMedium, fontSize: 12.5, color: colors.textMain },
  chipTextOn: { color: "#FFFFFF" },
  chipCount: { fontFamily: type.fontFamily, fontSize: 11.5, color: colors.textMuted, fontVariant: ["tabular-nums"] },
  chipCountOn: { color: "rgba(255,255,255,0.78)" },
  section: { gap: 10 },
  sectionTitle: { fontFamily: type.fontFamilyBold, fontSize: 15, color: colors.textMain, marginTop: 6 },
  empty: { fontFamily: type.fontFamily, fontSize: 13, color: colors.textMuted, lineHeight: 19, marginTop: 20 },
  card: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 14, gap: 8 },
  cardMeta: { flexDirection: "row", alignItems: "center", gap: 6 },
  outlet: { flex: 1, fontFamily: type.fontFamilyMedium, fontSize: 11, color: colors.textMuted, letterSpacing: 0.4, textTransform: "uppercase" },
  date: { fontFamily: type.fontFamily, fontSize: 11, color: colors.textMuted },
  title: { fontFamily: type.fontFamilyBold, fontSize: 15, color: colors.textMain, lineHeight: 21 },
  summary: { fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMain, lineHeight: 18 },
  risks: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  riskTag: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 999, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border },
  riskTagText: { fontFamily: type.fontFamilyMedium, fontSize: 10.5, color: colors.primary },
  linkRow: { flexDirection: "row", alignItems: "center", gap: 5 },
  link: { fontFamily: type.fontFamily, fontSize: 11.5, color: colors.secondary },
});
