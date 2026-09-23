// Trending risks: the day's stories from trusted financial outlets and
// regulators, each mapped to the granular risks it covers (see
// ingestion/risk_news_keywords.py for how). Filter by family; tap a story
// to read it at the source. Nothing here is written by us -- title and
// summary are the outlet's own feed text, and the mapping is shown as the
// risk chips so a reader can judge it.

import React, { useEffect, useMemo, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Linking, RefreshControl, ActivityIndicator, useWindowDimensions } from "react-native";
import Svg, { Rect, Line, Text as SvgText } from "react-native-svg";
import { ExternalLink, Landmark, Newspaper } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchRiskNews } from "../lib/api";
import { RISK_FAMILIES, RISK_BY_SLUG } from "../lib/riskTaxonomy";
import { FAMILY_TONE } from "../lib/riskColors";
import { useArrived } from "../lib/whatsNewContext";

const FAMILY_LABEL = Object.fromEntries(RISK_FAMILIES.map((f) => [f.key, f.label]));
const DAY = 24 * 60 * 60 * 1000;
const CHART_WEEKS = 13; // three months

// Some feeds publish a date in the future (a scheduling slip at the
// outlet). Clamped to now, so such a story sits at the top of the list
// and inside the chart's last week rather than falling off both.
function storyTime(story, now = Date.now()) {
  const t = new Date(story.published_at || story.fetched_at).getTime();
  return Number.isNaN(t) ? now : Math.min(t, now);
}

function bucket(story, now) {
  const t = storyTime(story, now);
  const age = now - t;
  if (age < DAY) return "Today";
  if (age < 2 * DAY) return "Yesterday";
  if (age < 7 * DAY) return "This week";
  return "Earlier";
}

// The year is shown whenever it is not this year: a 2019 story and a
// story from yesterday must not read the same.
function when(story) {
  const d = new Date(story.published_at || story.fetched_at);
  const thisYear = d.getFullYear() === new Date().getFullYear();
  return d.toLocaleDateString(undefined, thisYear ? { day: "numeric", month: "short" } : { day: "numeric", month: "short", year: "numeric" });
}

// Stories per week, stacked by family, over the last CHART_WEEKS weeks.
//
// Bars rather than lines: the counts are small and most weeks are empty,
// and a line drawn between two zero weeks claims a continuity the data
// does not have. A week with no stories is simply no bar. One story can
// report on several risk families, so it is counted in each -- the caption
// says so rather than quietly picking one.
function WeeklyBars({ stories, family, width }) {
  const w = width, h = 170, padL = 26, padR = 8, padT = 12, padB = 26;
  const WEEK = 7 * DAY;
  const end = new Date(); end.setHours(0, 0, 0, 0);
  const start = end.getTime() - (CHART_WEEKS - 1) * WEEK;
  const fams = RISK_FAMILIES.filter((f) => !family || f.key === family);

  // week -> family -> count
  const weeks = Array.from({ length: CHART_WEEKS }, () => ({}));
  for (const st of stories) {
    const i = Math.floor((storyTime(st) - start) / WEEK);
    if (i < 0 || i >= CHART_WEEKS) continue;
    for (const f of st.families || []) {
      if (family && f !== family) continue;
      weeks[i][f] = (weeks[i][f] || 0) + 1;
    }
  }
  const totals = weeks.map((wk) => Object.values(wk).reduce((a, b) => a + b, 0));
  const max = Math.max(1, ...totals);
  const plotW = w - padL - padR, plotH = h - padT - padB;
  const slot = plotW / CHART_WEEKS;
  const barW = Math.min(slot * 0.62, 22);
  const xOf = (i) => padL + slot * i + (slot - barW) / 2;
  const yOf = (v) => padT + plotH * (1 - v / max);
  const gridValues = [...new Set([0, Math.ceil(max / 2), max])];
  const ticks = [0, Math.floor((CHART_WEEKS - 1) / 2), CHART_WEEKS - 1];
  const label = (i) => new Date(start + i * WEEK).toLocaleDateString(undefined, { day: "numeric", month: "short" });

  return (
    <Svg width={w} height={h}>
      {gridValues.map((n) => (
        <React.Fragment key={n}>
          <Line x1={padL} x2={w - padR} y1={yOf(n)} y2={yOf(n)} stroke={colors.border} strokeWidth={1} />
          <SvgText x={padL - 6} y={yOf(n) + 3.5} fill={colors.textMuted} fontSize={10.5} fontFamily={type.fontFamily} textAnchor="end">{n}</SvgText>
        </React.Fragment>
      ))}
      {weeks.map((wk, i) => {
        // Stack in taxonomy order so a family keeps the same position
        // from week to week.
        let cursor = 0;
        return fams.map((f) => {
          const n = wk[f.key] || 0;
          if (!n) return null;
          const yTop = yOf(cursor + n);
          const height = plotH * (n / max);
          cursor += n;
          return (
            <Rect
              key={`${i}-${f.key}`}
              x={xOf(i)}
              y={yTop}
              width={barW}
              height={Math.max(height, 2)}
              rx={2.5}
              fill={FAMILY_TONE[f.key]}
            />
          );
        });
      })}
      {ticks.map((i) => (
        <SvgText
          key={i}
          x={xOf(i) + barW / 2}
          y={h - 8}
          fill={colors.textMuted}
          fontSize={10.5}
          fontFamily={type.fontFamily}
          textAnchor={i === 0 ? "start" : i === CHART_WEEKS - 1 ? "end" : "middle"}
        >
          {label(i)}
        </SvgText>
      ))}
    </Svg>
  );
}

export default function TrendingRisksScreen() {
  const { width } = useWindowDimensions();
  const [stories, setStories] = useState(null);
  const [family, setFamily] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [arrived, onFocusStories] = useArrived("stories");
  useFocusEffect(onFocusStories);

  const load = async () => setStories(await fetchRiskNews());
  useEffect(() => { load(); }, []);

  const counts = useMemo(() => {
    const c = {};
    for (const s of stories || []) for (const f of s.families || []) c[f] = (c[f] || 0) + 1;
    return c;
  }, [stories]);

  // The legend describes the chart, so it counts the same window the
  // chart draws -- a family whose only stories are older than three
  // months has no bar, and its legend entry says so by dimming.
  const windowCounts = useMemo(() => {
    const cutoff = Date.now() - CHART_WEEKS * 7 * DAY;
    const c = {};
    for (const s of stories || []) {
      if (storyTime(s) < cutoff) continue;
      for (const f of s.families || []) c[f] = (c[f] || 0) + 1;
    }
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
        {arrived > 0 && (
          <View style={styles.newStrip}>
            <Text style={styles.newStripText}>{arrived} new stor{arrived === 1 ? "y" : "ies"} since your last visit</Text>
          </View>
        )}

        {!!stories && (
          <View style={styles.chartCard}>
            <Text style={styles.chartTitle}>Stories per week, last 3 months</Text>
            <Text style={styles.chartNote}>A story covering several risk families is counted in each.</Text>
            <WeeklyBars stories={stories} family={family} width={Math.min(width - 40, 600) - 28} />
            <View style={styles.chartLegend}>
              {RISK_FAMILIES.filter((f) => !family || f.key === family).map((f) => {
                const active = (windowCounts[f.key] || 0) > 0;
                return (
                  <View key={f.key} style={[styles.legendItem, !active && styles.legendItemOff]}>
                    <View style={[styles.legendSwatch, { backgroundColor: FAMILY_TONE[f.key] }]} />
                    <Text style={styles.legendText}>{f.label}</Text>
                  </View>
                );
              })}
            </View>
          </View>
        )}

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
  lede: { fontFamily: type.fontFamily, fontSize: 14.5, color: colors.textMuted, lineHeight: 21 },
  newStrip: { backgroundColor: colors.accent, borderRadius: radius.chip, paddingHorizontal: 12, paddingVertical: 8, alignSelf: "flex-start" },
  newStripText: { fontFamily: type.fontFamilyMedium, fontSize: 13, color: colors.primary },
  chartCard: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 14, gap: 8 },
  chartTitle: { fontFamily: type.fontFamilyBold, fontSize: 14.5, color: colors.textMain },
  chartNote: { fontFamily: type.fontFamily, fontSize: 11.5, color: colors.textMuted, marginTop: -4 },
  chartLegend: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 5 },
  legendItemOff: { opacity: 0.32 },
  legendSwatch: { width: 11, height: 11, borderRadius: 3 },
  legendText: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted },
  chips: { flexDirection: "row", gap: 8, paddingVertical: 2 },
  chip: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.chip, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  chipOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontFamily: type.fontFamilyMedium, fontSize: 14, color: colors.textMain },
  chipTextOn: { color: "#FFFFFF" },
  chipCount: { fontFamily: type.fontFamily, fontSize: 13, color: colors.textMuted, fontVariant: ["tabular-nums"] },
  chipCountOn: { color: "rgba(255,255,255,0.78)" },
  section: { gap: 10 },
  sectionTitle: { fontFamily: type.fontFamilyBold, fontSize: 16.5, color: colors.textMain, marginTop: 6 },
  empty: { fontFamily: type.fontFamily, fontSize: 14.5, color: colors.textMuted, lineHeight: 21, marginTop: 20 },
  card: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 14, gap: 8 },
  cardMeta: { flexDirection: "row", alignItems: "center", gap: 6 },
  outlet: { flex: 1, fontFamily: type.fontFamilyMedium, fontSize: 12.5, color: colors.textMuted, letterSpacing: 0.4, textTransform: "uppercase" },
  date: { fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMuted },
  title: { fontFamily: type.fontFamilyBold, fontSize: 16.5, color: colors.textMain, lineHeight: 23 },
  summary: { fontFamily: type.fontFamily, fontSize: 14, color: colors.textMain, lineHeight: 20 },
  risks: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  riskTag: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 999, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border },
  riskTagText: { fontFamily: type.fontFamilyMedium, fontSize: 12, color: colors.primary },
  linkRow: { flexDirection: "row", alignItems: "center", gap: 5 },
  link: { fontFamily: type.fontFamily, fontSize: 13, color: colors.secondary },
});
