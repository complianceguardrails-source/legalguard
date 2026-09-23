// One use case in depth: what it is, the risk profile the data actually
// holds for it (tier, and the granular risks the tier is made of), every
// regulation matched to it, and the existing open-source guardrails that
// control each of those risks -- real repositories, linked, not policy we
// generate.

import React, { useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, useWindowDimensions, ActivityIndicator, Linking } from "react-native";
import { ArrowLeft, ArrowRight, ChevronDown, ChevronRight, ShieldCheck, Star, ExternalLink, X, Code2, Box, BookMarked } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchRegulations, fetchGuardrailRepos, fetchFinosFramework } from "../lib/api";
import { categoryLabel, categoryTone, useCaseTone, orderedCategories, sectorLabel, TIER_LABEL } from "../lib/categories";
import { getDiscoverState, toggleStar, dismiss } from "../lib/discoverState";
import UseCaseArt from "../components/UseCaseArt";
import { RISK_FAMILIES, RISK_BY_SLUG } from "../lib/riskTaxonomy";
import RegulationCard from "../components/RegulationCard";
import MetadataPill from "../components/MetadataPill";

// Only published provenance is ever shown; any other source renders no
// provenance line at all rather than a label for it.
const SOURCE_LABEL = { github_mined: "Published on GitHub", huggingface_mined: "Published on Hugging Face" };
const GROUP_LABEL = { category: "Because of what it does", basis: "Because of how it was classified", baseline: "Baseline for any AI system in a regulated firm", overlap: "Candidate from text overlap" };
const GROUP_TONE = { category: colors.primary, basis: "#8A6A16", baseline: colors.textMuted, overlap: colors.textMuted };
const TIER_VARIANT = { prohibited: "danger", high_risk: "warning", limited_risk: "info", minimal_risk: "success", unclassified: "neutral" };

export default function UseCaseDetailScreen({ route, navigation }) {
  const { useCase, fromDeck = false, preferred = [] } = route.params;
  const { width } = useWindowDimensions();
  const heroH = 220;
  const tone = useCaseTone(useCase, preferred);

  const [regulations, setRegulations] = useState(null);
  const [starred, setStarred] = useState(false);
  const [repos, setRepos] = useState(null);
  const [finos, setFinos] = useState([]);

  useEffect(() => {
    fetchRegulations({ limit: 500 }).then(setRegulations);
    fetchGuardrailRepos().then(setRepos);
    fetchFinosFramework().then(setFinos);
    getDiscoverState().then((s) => setStarred(s.starred.includes(useCase.id)));
  }, [useCase.id]);

  // Existing guardrails for this use case: every stored repository whose
  // controlled risks overlap the use case's own, grouped by risk in
  // taxonomy order, most-starred first within a risk. A risk with no
  // repository is listed as such -- the gap is information.
  const guardrails = useMemo(() => {
    const factors = useCase.risk_factors || [];
    if (!repos || !factors.length) return [];
    return factors.map((slug) => {
      // Two kinds of guardrail for the same risk: open-source tools, and
      // the organisational controls the FINOS framework names. Both are
      // labelled with where they come from.
      const finosRisks = finos.filter((e) => e.kind === "risk" && (e.risk_slugs || []).includes(slug));
      const ids = new Set(finosRisks.map((r) => r.external_id));
      return {
        slug,
        label: RISK_BY_SLUG[slug]?.label || slug,
        repos: repos.filter((r) => (r.risk_slugs || []).includes(slug)).sort((a, b) => (b.stars || 0) - (a.stars || 0)),
        controls: finos.filter((e) => e.kind === "mitigation" && (e.mitigates || []).some((m) => ids.has(m))),
      };
    });
  }, [repos, finos, useCase.risk_factors]);
  const [guardrailOpen, setGuardrailOpen] = useState(() => new Set());

  const matched = useMemo(
    () => (regulations || []).filter((r) => (r.affected_use_case_ids || []).includes(useCase.id)),
    [regulations, useCase.id]
  );

  // Matched regulations, grouped by the reason they matched: each entry of
  // regulation_basis is one rule from ingestion/category_regulation_map.py
  // with its own "why". Anything matched but not explained by a rule was
  // linked by word overlap at regulation ingestion, and is labelled as such
  // rather than dressed up as a legal basis.
  const groups = useMemo(() => {
    const byId = new Map(matched.map((r) => [r.reg_id, r]));
    const explained = new Set();
    const out = [];
    // A regulation two rules both reach (SFDR Art. 13 is in the ESG
    // disclosures and the greenwashing rule) is shown once, under the
    // first rule that names it, so the counts add up to the total.
    for (const entry of useCase.regulation_basis || []) {
      const regs = entry.reg_ids.map((id) => byId.get(id)).filter((r) => r && !explained.has(r.reg_id));
      if (!regs.length) continue;
      regs.forEach((r) => explained.add(r.reg_id));
      out.push({ key: entry.rule, title: entry.title || GROUP_LABEL[entry.kind], kind: entry.kind, why: entry.why, regs });
    }
    const rest = matched.filter((r) => !explained.has(r.reg_id));
    if (rest.length) out.push({ key: "overlap", title: "Text overlap", kind: "overlap", why: "Linked by word overlap between this use case's description and the regulation text -- a candidate to confirm, not a stated basis.", regs: rest });
    const order = { category: 0, basis: 1, baseline: 2, overlap: 3 };
    return out.sort((a, b) => order[a.kind] - order[b.kind]);
  }, [matched, useCase.regulation_basis]);
  const [open, setOpen] = useState(() => new Set());

  // What the tier is made of: the use case's granular risks, by family.
  // Tapping the tier pill opens it; tapping a risk shows its description.
  const [tierOpen, setTierOpen] = useState(false);
  const [riskOpen, setRiskOpen] = useState(null);
  const riskFamilies = useMemo(() => {
    const bySlug = new Set(useCase.risk_factors || []);
    return RISK_FAMILIES.map((fam) => ({
      ...fam,
      risks: Object.values(RISK_BY_SLUG).filter((r) => r.family === fam.key && bySlug.has(r.slug)),
    })).filter((fam) => fam.risks.length);
  }, [useCase.risk_factors]);
  const riskCount = (useCase.risk_factors || []).length;
  const toggleGroup = (key) => setOpen((prev) => { const next = new Set(prev); next.has(key) ? next.delete(key) : next.add(key); return next; });

  const blurb = (useCase.description || "").startsWith("Hugging Face model") ? null : useCase.description;
  const link = useCase.github_reference_url || (useCase.hf_model_id ? `https://huggingface.co/${useCase.hf_model_id}` : null);

  // Coming from the deck, the two ways off a card are offered here too, so
  // reading the detail never strands you: Dismiss removes it and returns,
  // Next card returns and advances the deck by one.
  const onDismiss = async () => {
    await dismiss(useCase.id);
    navigation.goBack();
  };

  return (
    <View style={styles.screen}>
    <ScrollView style={styles.screen} contentContainerStyle={[styles.content, fromDeck && { paddingBottom: 96 }]}>
      <View style={[styles.hero, { height: heroH }]}>
        <UseCaseArt useCase={useCase} width={width} height={heroH} style={StyleSheet.absoluteFill} preferred={preferred} />
        <View style={styles.heroBar}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.heroBtn} hitSlop={10} accessibilityRole="button" accessibilityLabel="Back">
            <ArrowLeft size={20} color="#FFFFFF" />
          </TouchableOpacity>
          <TouchableOpacity
            onPress={async () => setStarred(await toggleStar(useCase.id))}
            style={styles.heroBtn}
            hitSlop={10}
            accessibilityRole="button"
            accessibilityLabel={starred ? "Unstar" : "Star"}
          >
            <Star size={20} color="#FFFFFF" fill={starred ? "#FFFFFF" : "transparent"} />
          </TouchableOpacity>
        </View>
        <View style={styles.heroText}>
          <View style={styles.cats}>
            {orderedCategories(useCase, preferred).map((slug) => (
              <View key={slug} style={[styles.tag, { backgroundColor: categoryTone(slug) }]}>
                <Text style={styles.tagText}>{categoryLabel(slug)}</Text>
              </View>
            ))}
          </View>
          <Text style={styles.title}>{useCase.name}</Text>
        </View>
      </View>

      <View style={styles.section}>
        {blurb ? <Text style={styles.body}>{blurb}</Text> : <Text style={styles.muted}>No description is stored for this use case.</Text>}
        {!!SOURCE_LABEL[useCase.source] && <Text style={styles.provenance}>{SOURCE_LABEL[useCase.source]}</Text>}
        {link && (
          <TouchableOpacity onPress={() => Linking.openURL(link)} style={styles.linkRow}>
            <ExternalLink size={13} color={colors.secondary} />
            <Text style={styles.link} numberOfLines={1}>{link.replace("https://", "")}</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.section}>
        <Text style={styles.h2}>Risk profile</Text>
        <Text style={styles.sectionNote}>
          What the data holds for this system. Heuristic classifications, not a legal determination.
        </Text>
        <View style={styles.pills}>
          <TouchableOpacity
            onPress={() => setTierOpen((v) => !v)}
            disabled={!riskCount}
            accessibilityRole="button"
            accessibilityState={{ expanded: tierOpen }}
            accessibilityLabel={`${TIER_LABEL[useCase.risk_tier] || "Unclassified"}, ${riskCount} risks`}
            style={styles.tierTap}
          >
            <MetadataPill label={`${TIER_LABEL[useCase.risk_tier] || "Unclassified"}${riskCount ? ` · ${riskCount} risks` : ""}`} variant={TIER_VARIANT[useCase.risk_tier] || "neutral"} />
            {!!riskCount && (tierOpen ? <ChevronDown size={14} color={colors.textMuted} /> : <ChevronRight size={14} color={colors.textMuted} />)}
          </TouchableOpacity>
          {!!sectorLabel(useCase.parent_sector) && <MetadataPill label={sectorLabel(useCase.parent_sector)} variant="neutral" />}
          {!!useCase.modality && <MetadataPill label={useCase.modality.replace("_", " ")} variant="neutral" />}
          {!!useCase.model_modality && <MetadataPill label={useCase.model_modality} variant="info" />}
          {!!useCase.system_interface_type && <MetadataPill label={useCase.system_interface_type} variant="info" />}
          {(useCase.agent_operational_tools || []).map((t) => <MetadataPill key={t} label={t} variant="warning" />)}
        </View>
        {tierOpen && (
          <View style={styles.composition}>
            <Text style={styles.compositionNote}>
              What this tier is made of: {riskCount} risk{riskCount === 1 ? "" : "s"} in {riskFamilies.length} famil{riskFamilies.length === 1 ? "y" : "ies"}, each assigned by a rule from what the system does and what it is. Tap one for what it means.
            </Text>
            {riskFamilies.map((fam) => (
              <View key={fam.key} style={styles.family}>
                <View style={styles.familyHead}>
                  <Text style={styles.familyLabel}>{fam.label}</Text>
                  <Text style={styles.groupCount}>{fam.risks.length}</Text>
                </View>
                <View style={styles.riskChips}>
                  {fam.risks.map((r) => {
                    const on = riskOpen === r.slug;
                    return (
                      <TouchableOpacity key={r.slug} onPress={() => setRiskOpen(on ? null : r.slug)} style={[styles.riskChip, on && { backgroundColor: tone, borderColor: tone }]} accessibilityRole="button" accessibilityState={{ expanded: on }}>
                        <Text style={[styles.riskChipText, on && { color: "#FFFFFF" }]}>{r.label}</Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>
                {fam.risks.some((r) => r.slug === riskOpen) && (
                  <Text style={styles.riskDescription}>{RISK_BY_SLUG[riskOpen].description}</Text>
                )}
              </View>
            ))}
          </View>
        )}
        {useCase.risk_tier && useCase.risk_tier !== "unclassified" && (
          <View style={styles.why}>
            <Text style={styles.whyTitle}>Why {(TIER_LABEL[useCase.risk_tier] || useCase.risk_tier).toLowerCase()}</Text>
            {useCase.risk_basis ? (
              <>
                {useCase.risk_basis.from === "category_default" ? (
                  <Text style={styles.whyText}>
                    No phrase in this system's name or description matched the classifier. This is the default tier for{" "}
                    <Text style={styles.whyPhrase}>{useCase.risk_basis.basis.map((b) => categoryLabel(b.category)).join(", ")}</Text>
                    {" "}-- a starting point for a reviewer to confirm.
                  </Text>
                ) : (
                  <Text style={styles.whyText}>
                    The classifier found{" "}
                    {useCase.risk_basis.matched.map((m, i) => (
                      <Text key={m} style={styles.whyPhrase}>{i ? ", " : ""}“{m}”</Text>
                    ))}{" "}
                    in this system's own name or description.
                  </Text>
                )}
                {useCase.risk_basis.basis.map((b) => (
                  <View key={b.summary} style={styles.basis}>
                    {!!b.reference && <Text style={styles.basisRef}>{b.reference}</Text>}
                    <Text style={styles.whyText}>{b.summary}</Text>
                  </View>
                ))}
              </>
            ) : (
              <Text style={styles.whyText}>
                This tier was set by hand, or from repository signals that were not kept, so there is no matched phrase to show.
                Treat it as a reviewer's call, not a derivation.
              </Text>
            )}
          </View>
        )}
        {useCase.llm_compiled_requirement && (
          <View style={styles.callout}>
            <ShieldCheck size={16} color={colors.primary} />
            <Text style={styles.calloutText}>
              A compliance obligation was extracted from this system's own README:{" "}
              <Text style={{ fontFamily: type.fontFamilyMedium }}>{useCase.llm_compiled_requirement.rationale}</Text>
            </Text>
          </View>
        )}
      </View>

      <View style={styles.section}>
        <Text style={styles.h2}>Regulations it must comply with</Text>
        {!regulations ? (
          <ActivityIndicator color={colors.primary} />
        ) : matched.length === 0 ? (
          <Text style={styles.muted}>No regulation has been matched to this use case yet.</Text>
        ) : (
          <>
            <Text style={styles.sectionNote}>
              {matched.length} regulation{matched.length === 1 ? "" : "s"}, for {groups.length} reason{groups.length === 1 ? "" : "s"}. Each reason is the claim a reviewer would have to defend.
            </Text>
            {groups.map((g) => {
              const isOpen = open.has(g.key);
              const Chevron = isOpen ? ChevronDown : ChevronRight;
              return (
                <View key={g.key} style={styles.group}>
                  <TouchableOpacity onPress={() => toggleGroup(g.key)} style={styles.groupHead} accessibilityRole="button" accessibilityState={{ expanded: isOpen }}>
                    <Chevron size={16} color={colors.textMuted} />
                    <View style={{ flex: 1, gap: 3 }}>
                      <View style={styles.groupMeta}>
                        <Text style={styles.groupTitle} numberOfLines={1}>{g.title}</Text>
                        <Text style={styles.groupCount}>{g.regs.length}</Text>
                      </View>
                      <Text style={[styles.groupKind, { color: GROUP_TONE[g.kind] }]}>{GROUP_LABEL[g.kind]}</Text>
                      {isOpen && <Text style={styles.groupWhy}>{g.why}</Text>}
                    </View>
                  </TouchableOpacity>
                  {isOpen && <View style={styles.groupBody}>{g.regs.map((r) => <RegulationCard key={r.reg_id} item={r} />)}</View>}
                </View>
              );
            })}
          </>
        )}
      </View>

      <View style={styles.section}>
        <View style={styles.h2Row}>
          <ShieldCheck size={16} color={colors.textMain} />
          <Text style={styles.h2}>Existing guardrails</Text>
        </View>
        <Text style={styles.sectionNote}>
          What exists for each of this system's risks: open-source tools (real repositories on GitHub and models on the
          Hugging Face Hub, with their own stars and last activity) and the organisational controls the FINOS AI
          Governance Framework names. Every entry says where it came from.
        </Text>
        {!repos ? (
          <ActivityIndicator color={colors.primary} />
        ) : guardrails.length === 0 ? (
          <Text style={styles.muted}>No granular risks are recorded for this use case yet.</Text>
        ) : (
          guardrails.map((g) => {
            const isOpen = guardrailOpen.has(g.slug);
            const Chevron = isOpen ? ChevronDown : ChevronRight;
            return (
              <View key={g.slug} style={styles.group}>
                <TouchableOpacity
                  onPress={() => setGuardrailOpen((prev) => { const n = new Set(prev); n.has(g.slug) ? n.delete(g.slug) : n.add(g.slug); return n; })}
                  style={styles.groupHead}
                  disabled={!g.repos.length && !g.controls.length}
                  accessibilityRole="button"
                  accessibilityState={{ expanded: isOpen }}
                >
                  <Chevron size={16} color={g.repos.length || g.controls.length ? colors.textMuted : "transparent"} />
                  <View style={{ flex: 1, gap: 3 }}>
                    <View style={styles.groupMeta}>
                      <Text style={styles.groupTitle} numberOfLines={1}>{g.label}</Text>
                      <Text style={styles.groupCount}>{g.repos.length + g.controls.length}</Text>
                    </View>
                    <Text style={[styles.groupKind, { color: g.repos.length || g.controls.length ? colors.primary : colors.textMuted }]}>
                      {[
                        g.repos.length ? `${g.repos.length} open-source tool${g.repos.length === 1 ? "" : "s"}` : null,
                        g.controls.length ? `${g.controls.length} FINOS control${g.controls.length === 1 ? "" : "s"}` : null,
                      ].filter(Boolean).join(" · ") || "No known control"}
                    </Text>
                  </View>
                </TouchableOpacity>
                {isOpen && (
                  <View style={styles.groupBody}>
                    {g.controls.map((c) => <ControlRow key={c.entry_id} control={c} />)}
                    {g.repos.map((r) => <RepoRow key={r.repo_id} repo={r} />)}
                  </View>
                )}
              </View>
            );
          })
        )}
      </View>
    </ScrollView>
      {fromDeck && (
        <View style={styles.footer}>
          <TouchableOpacity style={[styles.footBtn, styles.footBtnGhost]} onPress={onDismiss} accessibilityRole="button" accessibilityLabel="Dismiss this use case">
            <X size={16} color={colors.textMain} />
            <Text style={styles.footBtnGhostText}>Dismiss</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.footBtn, styles.footBtnPrimary]}
            // Back to the deck it came from, asking it to advance; merge
            // keeps the deck's own params (slugs, mode) intact.
            onPress={() => navigation.navigate({ name: "Deck", params: { advance: Date.now() }, merge: true })}
            accessibilityRole="button"
            accessibilityLabel="Next card"
          >
            <Text style={styles.footBtnPrimaryText}>Next card</Text>
            <ArrowRight size={16} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

// A control from the FINOS AI Governance Framework, carrying its
// provenance the same way a repository carries GitHub or the Hub.
function ControlRow({ control }) {
  return (
    <TouchableOpacity onPress={() => Linking.openURL(control.url)} style={styles.repo} accessibilityRole="link">
      <View style={styles.repoHead}>
        <BookMarked size={14} color={colors.textMain} />
        <Text style={styles.repoName} numberOfLines={2}>{control.title}</Text>
        <ExternalLink size={12} color={colors.textMuted} />
      </View>
      {!!control.summary && <Text style={styles.repoDesc} numberOfLines={2}>{control.summary}</Text>}
      <Text style={styles.repoMeta}>
        FINOS {control.external_id.toUpperCase()}
        {control.type_label ? ` · ${control.type_label}` : ""}
        {control.doc_status ? ` · ${control.doc_status.replace(/-/g, " ")}` : ""}
      </Text>
    </TouchableOpacity>
  );
}

function RepoRow({ repo }) {
  const Icon = repo.platform === "github" ? Code2 : Box;
  const meta = [
    repo.platform === "github" ? "GitHub" : "Hugging Face",
    repo.stars != null ? `${repo.stars.toLocaleString()} ${repo.platform === "github" ? "stars" : "likes"}` : null,
    repo.downloads != null ? `${repo.downloads.toLocaleString()} downloads` : null,
    repo.language,
    repo.license,
    repo.last_pushed_at ? `updated ${new Date(repo.last_pushed_at).toLocaleDateString(undefined, { month: "short", year: "numeric" })}` : null,
  ].filter(Boolean).join(" · ");
  return (
    <TouchableOpacity onPress={() => Linking.openURL(repo.url)} style={styles.repo} accessibilityRole="link">
      <View style={styles.repoHead}>
        <Icon size={14} color={colors.textMain} />
        <Text style={styles.repoName} numberOfLines={1}>{repo.external_id}</Text>
      </View>
      {!!repo.description && <Text style={styles.repoDesc} numberOfLines={2}>{repo.description}</Text>}
      <Text style={styles.repoMeta}>{meta}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { paddingBottom: 40 },
  hero: { justifyContent: "space-between", backgroundColor: colors.primary },
  heroBar: { flexDirection: "row", justifyContent: "space-between", padding: 14 },
  heroBtn: { padding: 8, borderRadius: 999, backgroundColor: "rgba(0,0,0,0.25)" },
  heroText: { padding: 18, gap: 8 },
  cats: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  tag: { paddingHorizontal: 9, paddingVertical: 5, borderRadius: 999 },
  tagText: { fontFamily: type.fontFamilyMedium, fontSize: 11.5, letterSpacing: 0.6, color: "#FFFFFF", textTransform: "uppercase" },
  title: { fontFamily: type.fontFamilyBold, fontSize: 22, lineHeight: 27, color: "#FFFFFF" },
  section: { paddingHorizontal: 20, paddingTop: 20, gap: 10 },
  h2Row: { flexDirection: "row", alignItems: "center", gap: 8 },
  h2: { fontFamily: type.fontFamilyBold, fontSize: 16.5, color: colors.textMain },
  sectionNote: { fontFamily: type.fontFamily, fontSize: 13.5, color: colors.textMuted, lineHeight: 19 },
  body: { fontFamily: type.fontFamily, fontSize: 15.5, color: colors.textMain, lineHeight: 23 },
  muted: { fontFamily: type.fontFamily, fontSize: 14.5, color: colors.textMuted, lineHeight: 21 },
  provenance: { fontFamily: type.fontFamilyMedium, fontSize: 12.5, color: colors.textMuted, letterSpacing: 0.4, textTransform: "uppercase" },
  linkRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  link: { fontFamily: type.fontFamily, fontSize: 13.5, color: colors.secondary, flex: 1 },
  pills: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  tierTap: { flexDirection: "row", alignItems: "center", gap: 4 },
  composition: { gap: 12, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 12 },
  compositionNote: { fontFamily: type.fontFamily, fontSize: 13.5, color: colors.textMuted, lineHeight: 19 },
  family: { gap: 8 },
  familyHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 },
  familyLabel: { flex: 1, fontFamily: type.fontFamilyBold, fontSize: 14, color: colors.textMain },
  riskChips: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  riskChip: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.background },
  riskChipText: { fontFamily: type.fontFamilyMedium, fontSize: 13, color: colors.textMain },
  riskDescription: { fontFamily: type.fontFamily, fontSize: 14, color: colors.textMain, lineHeight: 20, paddingLeft: 10, borderLeftWidth: 2, borderLeftColor: colors.border },
  why: { gap: 8, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 12 },
  whyTitle: { fontFamily: type.fontFamilyBold, fontSize: 14.5, color: colors.textMain },
  whyText: { fontFamily: type.fontFamily, fontSize: 14, color: colors.textMain, lineHeight: 20 },
  whyPhrase: { fontFamily: type.fontFamilyMedium, color: colors.primary },
  basis: { gap: 2, paddingLeft: 10, borderLeftWidth: 2, borderLeftColor: colors.border },
  basisRef: { fontFamily: type.fontFamilyMedium, fontSize: 12.5, color: colors.textMuted, letterSpacing: 0.3, textTransform: "uppercase" },
  group: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, backgroundColor: colors.surface, overflow: "hidden" },
  groupHead: { flexDirection: "row", alignItems: "flex-start", gap: 8, padding: 12 },
  groupMeta: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  groupTitle: { flex: 1, fontFamily: type.fontFamilyBold, fontSize: 15, color: colors.textMain },
  groupKind: { fontFamily: type.fontFamilyMedium, fontSize: 12, letterSpacing: 0.5, textTransform: "uppercase" },
  groupCount: { flexShrink: 0, minWidth: 26, textAlign: "center", paddingHorizontal: 7, paddingVertical: 2, borderRadius: 999, backgroundColor: colors.background, fontFamily: type.fontFamilyMedium, fontSize: 12.5, color: colors.textMuted, fontVariant: ["tabular-nums"] },
  groupWhy: { fontFamily: type.fontFamily, fontSize: 14, color: colors.textMain, lineHeight: 20 },
  groupBody: { paddingHorizontal: 12, paddingBottom: 12, gap: 8, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 12 },
  callout: { flexDirection: "row", gap: 10, alignItems: "flex-start", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 12 },
  calloutText: { flex: 1, fontFamily: type.fontFamily, fontSize: 14, color: colors.textMain, lineHeight: 20 },
  repo: { gap: 4, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.border },
  repoHead: { flexDirection: "row", alignItems: "center", gap: 6 },
  repoName: { flex: 1, fontFamily: type.fontFamilyBold, fontSize: 14.5, color: colors.textMain },
  repoDesc: { fontFamily: type.fontFamily, fontSize: 13.5, color: colors.textMain, lineHeight: 19 },
  repoMeta: { fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMuted },
  footer: { position: "absolute", left: 0, right: 0, bottom: 0, flexDirection: "row", gap: 10, padding: 14, backgroundColor: colors.background, borderTopWidth: 1, borderTopColor: colors.border },
  footBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 13, borderRadius: radius.button },
  footBtnGhost: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  footBtnGhostText: { fontFamily: type.fontFamilyMedium, fontSize: 15.5, color: colors.textMain },
  footBtnPrimary: { backgroundColor: colors.primary },
  footBtnPrimaryText: { fontFamily: type.fontFamilyBold, fontSize: 15.5, color: "#FFFFFF" },
});
