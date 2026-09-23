// Trending risks: the day's stories from trusted financial outlets and
// regulators, each mapped to the granular risks it covers (see
// ingestion/risk_news_keywords.py for how). Filter by family; tap a story
// to read it at the source. Nothing here is written by us -- title and
// summary are the outlet's own feed text, and the mapping is shown as the
// risk chips so a reader can judge it.

import React, { useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Linking, RefreshControl, ActivityIndicator, useWindowDimensions } from "react-native";
import Svg, { Polyline, Line, Circle, Text as SvgText } from "react-native-svg";
import { ExternalLink, Landmark, Newspaper } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchRiskNews } from "../lib/api";
import { RISK_FAMILIES, RISK_BY_SLUG } from "../lib/riskTaxonomy";

const FAMILY_LABEL = Object.fromEntries(RISK_FAMILIES.map((f) => [f.key, f.label]));
// Same family tones as the Guardrails wheel, so a colour means one thing
// across the app.
const FAMILY_TONE = { systemic: "#3B3F9E", model: "#0E6B6B", cyber: "#A34A17", legal: "#234FA3", vendor: "#3E5C76", ethical: "#6B2D5C", environmental: "#2E6B3A" };
const DAY = 24 * 60 * 60 * 1000;
const CHART_WEEKS = 13; // three months

function bucket(story, now) {
  const t = story.published_at ? new Date(story.published_at).getTime() : new Date(story.fetched_at).getTime();
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

// Stories per week per family over the last CHART_WEEKS weeks, as lines.
// Weekly bins: a daily line over three months is noise; a weekly one is a
// trend.
function TrendLines({ stories, family, width }) {
  const w = width, h = 160, padL = 28, padR = 10, padT = 10, padB = 24;
  const WEEK = 7 * DAY;
  const end = new Date(); end.setHours(0, 0, 0, 0);
  const start = end.getTime() - (CHART_WEEKS - 1) * WEEK;
  const weekIndex = (t) => Math.floor((t - start) / WEEK);
  const series = RISK_FAMILIES.filter((f) => !family || f.key === family).map((f) => {
    const counts = new Array(CHART_WEEKS).fill(0);
    for (const s of stories) {
      if (!(s.families || []).includes(f.key)) continue;
      const i = weekIndex(new Date(s.published_at || s.fetched_at).getTime());
      if (i >= 0 && i < CHART_WEEKS) counts[i] += 1;
    }
    return { key: f.key, counts };
  });
  const max = Math.max(1, ...series.flatMap((s) => s.counts));
  const x = (i) => padL + (i * (w - padL - padR)) / (CHART_WEEKS - 1);
  const y = (n) => padT + (h - padT - padB) * (1 - n / max);
  const ticks = [0, Math.floor(CHART_WEEKS / 3), Math.floor((2 * CHART_WEEKS) / 3), CHART_WEEKS - 1];
  const label = (i) => new Date(start + i * WEEK).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  return (
    <Svg width={w} height={h}>
      {[0, Math.ceil(max / 2), max].filter((v, i, a) => a.indexOf(v) === i).map((n) => (
        <React.Fragment key={n}>
          <Line x1={padL} x2={w - padR} y1={y(n)} y2={y(n)} stroke={colors.border} strokeWidth={1} />
          <SvgText x={padL - 6} y={y(n) + 3.5} fill={colors.textMuted} fontSize={10.5} fontFamily={type.fontFamily} textAnchor="end">{n}</SvgText>
        </React.Fragment>
      ))}
      {ticks.map((i) => (
        <SvgText key={i} x={x(i)} y={h - 6} fill={colors.textMuted} fontSize={10.5} fontFamily={type.fontFamily} textAnchor={i === 0 ? "start" : i === CHART_WEEKS - 1 ? "end" : "middle"}>
          {label(i)}
        </SvgText>
      ))}
      {series.map((s) => (
        <React.Fragment key={s.key}>
          <Polyline points={s.counts.map((n, i) => `${x(i)},${y(n)}`).join(" ")} fill="none" stroke={FAMILY_TONE[s.key]} strokeWidth={2} strokeLinejoin="round" />
          {s.counts.map((n, i) => (n ? <Circle key={i} cx={x(i)} cy={y(n)} r={3} fill={FAMILY_TONE[s.key]} /> : null))}
        </React.Fragment>
      ))}
    </Svg>
  );
}

export default function TrendingRisksScreen() {
  const { width } = useWindowDimensions();
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

        {!!stories && (
          <View style={styles.chartCard}>
            <Text style={styles.chartTitle}>Stories per week, last 3 months</Text>
            <TrendLines stories={stories} family={family} width={Math.min(width - 40, 600) - 28} />
            <View style={styles.chartLegend}>
              {RISK_FAMILIES.filter((f) => !family || f.key === family).map((f) => (
                <View key={f.key} style={styles.legendItem}>
                  <View style={[styles.legendSwatch, { backgroundColor: FAMILY_TONE[f.key] }]} />
                  <Text style={styles.legendText}>{f.label}</Text>
                </View>
              ))}
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
  chartCard: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 14, gap: 8 },
  chartTitle: { fontFamily: type.fontFamilyBold, fontSize: 14.5, color: colors.textMain },
  chartLegend: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 5 },
  legendSwatch: { width: 10, height: 10, borderRadius: 2 },
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
