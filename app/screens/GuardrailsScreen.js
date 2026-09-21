// Guardrails: how well the open-source ecosystem covers the risk taxonomy,
// today. The sunburst is the whole taxonomy at once -- seven families on
// the inner ring, all fifty-nine risks on the outer -- with each risk
// shaded by how many guardrail repositories control it, hollow where none
// do. Tap a risk for its repositories. Below: coverage per family, the
// state of the art (most-starred, recently active) and what emerged this
// quarter. Everything is read from guardrail_repos, refreshed nightly.

import React, { useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Linking, RefreshControl, ActivityIndicator, useWindowDimensions } from "react-native";
import Svg, { Path, G, Circle, Text as SvgText } from "react-native-svg";
import { Code2, Box, ExternalLink, Sparkles, Trophy } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchGuardrailRepos } from "../lib/api";
import { RISK_FAMILIES, RISKS, RISK_BY_SLUG } from "../lib/riskTaxonomy";

// One tone per family, dark enough for white text; the shading of a risk
// segment is this tone at an opacity that grows with coverage.
const FAMILY_TONE = {
  systemic: "#3B3F9E",
  model: "#0E6B6B",
  cyber: "#A34A17",
  legal: "#234FA3",
  vendor: "#3E5C76",
  ethical: "#6B2D5C",
  environmental: "#2E6B3A",
};
const FAMILY_SHORT = {
  systemic: "Systemic",
  model: "Model",
  cyber: "Cyber",
  legal: "Legal",
  vendor: "Vendor",
  ethical: "Ethical",
  environmental: "Environment",
};
const DAY = 24 * 60 * 60 * 1000;

function coverageOpacity(n) {
  if (n === 0) return 0;
  if (n <= 2) return 0.35;
  if (n <= 5) return 0.6;
  if (n <= 9) return 0.8;
  return 1;
}

function polar(cx, cy, r, deg) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

// Annular sector from a0 to a1 degrees (clockwise from 12 o'clock).
function sector(cx, cy, r0, r1, a0, a1) {
  const large = a1 - a0 > 180 ? 1 : 0;
  const p0 = polar(cx, cy, r1, a0), p1 = polar(cx, cy, r1, a1);
  const q1 = polar(cx, cy, r0, a1), q0 = polar(cx, cy, r0, a0);
  return `M ${p0.x} ${p0.y} A ${r1} ${r1} 0 ${large} 1 ${p1.x} ${p1.y} L ${q1.x} ${q1.y} A ${r0} ${r0} 0 ${large} 0 ${q0.x} ${q0.y} Z`;
}

export default function GuardrailsScreen() {
  const { width } = useWindowDimensions();
  const [repos, setRepos] = useState(null);
  const [selected, setSelected] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => setRepos(await fetchGuardrailRepos());
  useEffect(() => { load(); }, []);

  // Per-risk repos, per-family coverage, and the two lists.
  const model = useMemo(() => {
    const byRisk = Object.fromEntries(RISKS.map((r) => [r.slug, []]));
    for (const repo of repos || []) for (const slug of repo.risk_slugs || []) byRisk[slug]?.push(repo);
    for (const slug of Object.keys(byRisk)) byRisk[slug].sort((a, b) => (b.stars || 0) - (a.stars || 0));
    const families = RISK_FAMILIES.map((f) => {
      const risks = RISKS.filter((r) => r.family === f.key);
      const covered = risks.filter((r) => byRisk[r.slug].length);
      const repoSet = new Set(risks.flatMap((r) => byRisk[r.slug].map((x) => x.repo_id)));
      return { ...f, risks, covered: covered.length, repos: repoSet.size };
    });
    const now = Date.now();
    const sota = [...(repos || [])].filter((r) => r.last_pushed_at && now - new Date(r.last_pushed_at).getTime() < 365 * DAY).sort((a, b) => (b.stars || 0) - (a.stars || 0)).slice(0, 8);
    const emerging = [...(repos || [])].filter((r) => r.created_at && now - new Date(r.created_at).getTime() < 90 * DAY).sort((a, b) => (b.stars || 0) - (a.stars || 0));
    const fetched = (repos || []).reduce((m, r) => (r.fetched_at > m ? r.fetched_at : m), "");
    const coveredTotal = RISKS.filter((r) => byRisk[r.slug].length).length;
    return { byRisk, families, sota, emerging, fetched, coveredTotal };
  }, [repos]);

  // Sunburst geometry: equal angle per risk, families as contiguous arcs.
  const size = Math.min(width - 40, 380);
  const cx = size / 2, cy = size / 2;
  const r0 = size * 0.17, r1 = size * 0.30, r2 = size * 0.48;
  const per = 360 / RISKS.length;
  const gap = 0.6;
  const segments = useMemo(() => {
    let a = 0;
    const fams = [];
    const risks = [];
    for (const f of RISK_FAMILIES) {
      const fr = RISKS.filter((r) => r.family === f.key);
      const start = a;
      for (const r of fr) {
        risks.push({ slug: r.slug, family: f.key, a0: a + gap / 2, a1: a + per - gap / 2 });
        a += per;
      }
      fams.push({ key: f.key, a0: start + gap / 2, a1: a - gap / 2, mid: (start + a) / 2 });
    }
    return { fams, risks };
  }, [per]);

  const sel = selected ? RISK_BY_SLUG[selected] : null;
  const selRepos = selected ? model.byRisk[selected] : [];

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} tintColor={colors.primary} />}
    >
      <Text style={styles.h1}>Guardrail coverage</Text>
      <Text style={styles.lede}>
        Every risk in the taxonomy, shaded by how many open-source guardrails control it. Hollow means no known
        technical control. Tap a segment.
      </Text>

      {!repos ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
      ) : (
        <>
          <View style={styles.chartWrap}>
            <View style={{ width: size, height: size }}>
            <Svg width={size} height={size}>
              <G>
                {segments.fams.map((f) => (
                  <Path key={f.key} d={sector(cx, cy, r0, r1, f.a0, f.a1)} fill={FAMILY_TONE[f.key]} onPress={() => setSelected(null)} />
                ))}
                {segments.risks.map((s) => {
                  const n = model.byRisk[s.slug].length;
                  const on = selected === s.slug;
                  return (
                    <Path
                      key={s.slug}
                      d={sector(cx, cy, r1 + 2, on ? r2 + 6 : r2, s.a0, s.a1)}
                      fill={n ? FAMILY_TONE[s.family] : "none"}
                      fillOpacity={n ? coverageOpacity(n) : 1}
                      stroke={on ? colors.accent : n ? "none" : FAMILY_TONE[s.family]}
                      strokeWidth={on ? 2.5 : 1}
                      strokeDasharray={n || on ? undefined : "3,2"}
                      onPress={() => setSelected(on ? null : s.slug)}
                    />
                  );
                })}
                {segments.fams.map((f) => {
                  // Every family is named. A narrow arc (Vendor: 4 risks,
                  // Ethical: 6) gets a smaller face, still on its own band.
                  const p = polar(cx, cy, (r0 + r1) / 2, f.mid);
                  const span = f.a1 - f.a0;
                  const fs = span > 40 ? (size < 340 ? 8 : 9.5) : span > 30 ? 7.5 : 6.5;
                  return (
                    <SvgText key={`t-${f.key}`} x={p.x} y={p.y + fs * 0.35} fill="#FFFFFF" fontSize={fs} fontWeight="700" fontFamily={type.fontFamilyBold} textAnchor="middle">
                      {FAMILY_SHORT[f.key]}
                    </SvgText>
                  );
                })}
                <Circle cx={cx} cy={cy} r={r0 - 3} fill={colors.surface} />
              </G>
            </Svg>
            {/* The centre figure is native text laid over the SVG: SVG text
                baselines differ between web and iOS, and this must sit dead
                centre on both. */}
            <View pointerEvents="none" style={[styles.centre, { width: (r0 - 4) * 2, height: (r0 - 4) * 2, left: cx - (r0 - 4), top: cy - (r0 - 4) }]}>
              <Text style={styles.centreValue}>{model.coveredTotal}/{RISKS.length}</Text>
              <Text style={styles.centreLabel}>risks covered</Text>
            </View>
            </View>
          </View>

          <View style={styles.legend}>
            {[["none", 0], ["1–2", 0.35], ["3–5", 0.6], ["6–9", 0.8], ["10+", 1]].map(([label, op]) => (
              <View key={label} style={styles.legendItem}>
                <View style={[styles.swatch, op ? { backgroundColor: colors.primary, opacity: op } : { borderWidth: 1, borderStyle: "dashed", borderColor: colors.primary }]} />
                <Text style={styles.legendText}>{label}</Text>
              </View>
            ))}
          </View>

          <View style={styles.selected}>
            {sel ? (
              <>
                <View style={styles.selHead}>
                  <View style={[styles.dot, { backgroundColor: FAMILY_TONE[sel.family] }]} />
                  <Text style={styles.selTitle}>{sel.label}</Text>
                  <Text style={styles.count}>{selRepos.length}</Text>
                </View>
                <Text style={styles.selFamily}>{RISK_FAMILIES.find((f) => f.key === sel.family)?.label}</Text>
                <Text style={styles.selDesc}>{sel.description}</Text>
                {selRepos.length === 0 ? (
                  <Text style={styles.gap}>No known technical control. This is a gap in the ecosystem, not something the app hides.</Text>
                ) : (
                  selRepos.map((r) => <RepoRow key={r.repo_id} repo={r} />)
                )}
              </>
            ) : (
              <Text style={styles.selHint}>Tap a risk on the ring to see the guardrails that control it.</Text>
            )}
          </View>

          <Text style={styles.h2}>Coverage by family</Text>
          {model.families.map((f) => (
            <View key={f.key} style={styles.famRow}>
              <View style={styles.famHead}>
                <View style={[styles.dot, { backgroundColor: FAMILY_TONE[f.key] }]} />
                <Text style={styles.famLabel} numberOfLines={1}>{f.label}</Text>
                <Text style={styles.famStat}>{f.covered}/{f.risks.length} risks · {f.repos} repos</Text>
              </View>
              <View style={styles.bar}>
                <View style={[styles.barFill, { width: `${(100 * f.covered) / f.risks.length}%`, backgroundColor: FAMILY_TONE[f.key] }]} />
              </View>
            </View>
          ))}

          <View style={styles.h2Row}>
            <Trophy size={16} color={colors.textMain} />
            <Text style={styles.h2}>State of the art</Text>
          </View>
          <Text style={styles.note}>Most-starred controls with activity in the last year.</Text>
          {model.sota.map((r) => <RepoRow key={r.repo_id} repo={r} showRisks />)}

          <View style={styles.h2Row}>
            <Sparkles size={16} color={colors.textMain} />
            <Text style={styles.h2}>Emerging this quarter</Text>
          </View>
          <Text style={styles.note}>Created in the last 90 days and already picked up. Found by the nightly search, not curated.</Text>
          {model.emerging.length === 0 ? (
            <Text style={styles.gap}>Nothing new this quarter has cleared the star floor yet.</Text>
          ) : (
            model.emerging.map((r) => <RepoRow key={r.repo_id} repo={r} showRisks />)
          )}

          {!!model.fetched && (
            <Text style={styles.freshness}>
              {repos.length} repositories · last refreshed {new Date(model.fetched).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}. Seeds and searches re-run nightly.
            </Text>
          )}
        </>
      )}
    </ScrollView>
  );
}

function RepoRow({ repo, showRisks }) {
  const Icon = repo.platform === "github" ? Code2 : Box;
  const meta = [
    repo.stars != null ? `${repo.stars.toLocaleString()} ${repo.platform === "github" ? "stars" : "likes"}` : null,
    repo.downloads != null ? `${repo.downloads.toLocaleString()} downloads` : null,
    repo.license,
    repo.last_pushed_at ? `updated ${new Date(repo.last_pushed_at).toLocaleDateString(undefined, { month: "short", year: "numeric" })}` : null,
  ].filter(Boolean).join(" · ");
  return (
    <TouchableOpacity onPress={() => Linking.openURL(repo.url)} style={styles.repo} accessibilityRole="link">
      <View style={styles.repoHead}>
        <Icon size={14} color={colors.textMain} />
        <Text style={styles.repoName} numberOfLines={1}>{repo.external_id}</Text>
        <ExternalLink size={12} color={colors.textMuted} />
      </View>
      {!!repo.description && <Text style={styles.repoDesc} numberOfLines={2}>{repo.description}</Text>}
      <Text style={styles.repoMeta}>{meta}</Text>
      {showRisks && (
        <View style={styles.riskTags}>
          {(repo.risk_slugs || []).slice(0, 4).map((s) => (
            <View key={s} style={[styles.riskTag, { borderColor: FAMILY_TONE[RISK_BY_SLUG[s]?.family] || colors.border }]}>
              <Text style={[styles.riskTagText, { color: FAMILY_TONE[RISK_BY_SLUG[s]?.family] || colors.textMain }]}>{RISK_BY_SLUG[s]?.label || s}</Text>
            </View>
          ))}
          {(repo.risk_slugs || []).length > 4 && <Text style={styles.more}>+{repo.risk_slugs.length - 4}</Text>}
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: 20, gap: 12, paddingBottom: 40 },
  h1: { fontFamily: type.fontFamilyBold, fontSize: 24, color: colors.textMain, lineHeight: 30 },
  lede: { fontFamily: type.fontFamily, fontSize: 13, color: colors.textMuted, lineHeight: 19 },
  chartWrap: { alignItems: "center", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, paddingVertical: 12 },
  centre: { position: "absolute", alignItems: "center", justifyContent: "center" },
  centreValue: { fontFamily: type.fontFamilyBold, fontSize: 22, color: colors.textMain, lineHeight: 26, textAlign: "center" },
  centreLabel: { fontFamily: type.fontFamily, fontSize: 10, color: colors.textMuted, textAlign: "center" },
  legend: { flexDirection: "row", justifyContent: "center", gap: 14, flexWrap: "wrap" },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 5 },
  swatch: { width: 12, height: 12, borderRadius: 3 },
  legendText: { fontFamily: type.fontFamily, fontSize: 11, color: colors.textMuted },
  selected: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 14, gap: 6 },
  selHint: { fontFamily: type.fontFamily, fontSize: 13, color: colors.textMuted, textAlign: "center" },
  selHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  dot: { width: 9, height: 9, borderRadius: 5 },
  selTitle: { flex: 1, fontFamily: type.fontFamilyBold, fontSize: 15, color: colors.textMain },
  count: { minWidth: 26, textAlign: "center", paddingHorizontal: 7, paddingVertical: 2, borderRadius: 999, backgroundColor: colors.background, fontFamily: type.fontFamilyMedium, fontSize: 11, color: colors.textMuted },
  selFamily: { fontFamily: type.fontFamilyMedium, fontSize: 10.5, color: colors.textMuted, letterSpacing: 0.5, textTransform: "uppercase" },
  selDesc: { fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMain, lineHeight: 18, marginBottom: 4 },
  gap: { fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMuted, lineHeight: 18, fontStyle: "italic" },
  h2Row: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 8 },
  h2: { fontFamily: type.fontFamilyBold, fontSize: 16, color: colors.textMain, marginTop: 8 },
  note: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, marginTop: -6 },
  famRow: { gap: 5 },
  famHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  famLabel: { flex: 1, fontFamily: type.fontFamilyMedium, fontSize: 13, color: colors.textMain },
  famStat: { fontFamily: type.fontFamily, fontSize: 11.5, color: colors.textMuted, fontVariant: ["tabular-nums"] },
  bar: { height: 8, borderRadius: 4, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  barFill: { height: "100%", borderRadius: 4 },
  repo: { gap: 4, paddingVertical: 9, borderBottomWidth: 1, borderBottomColor: colors.border },
  repoHead: { flexDirection: "row", alignItems: "center", gap: 6 },
  repoName: { flex: 1, fontFamily: type.fontFamilyBold, fontSize: 13, color: colors.textMain },
  repoDesc: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMain, lineHeight: 17 },
  repoMeta: { fontFamily: type.fontFamily, fontSize: 11, color: colors.textMuted },
  riskTags: { flexDirection: "row", flexWrap: "wrap", gap: 5, alignItems: "center" },
  riskTag: { paddingHorizontal: 7, paddingVertical: 3, borderRadius: 999, borderWidth: 1 },
  riskTagText: { fontFamily: type.fontFamilyMedium, fontSize: 10 },
  more: { fontFamily: type.fontFamily, fontSize: 10.5, color: colors.textMuted },
  freshness: { fontFamily: type.fontFamily, fontSize: 11.5, color: colors.textMuted, textAlign: "center", marginTop: 10 },
});
