// One use case in depth: what it is, the risk profile the data actually
// holds for it, every regulation matched to it, and the guardrail policy
// the generation service produces for it -- verified with opa before it
// gets here. Deployment is one more deliberate step, on the Audit screen.

import React, { useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, useWindowDimensions, ActivityIndicator, Linking } from "react-native";
import { ArrowLeft, ArrowRight, ChevronDown, ChevronRight, Scale, ShieldCheck, Star, ExternalLink, X } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchRegulations } from "../lib/api";
import { fetchGuardrailPackage } from "../lib/generator";
import { categoryLabel, categoryTone, useCaseTone, sectorLabel, TIER_LABEL } from "../lib/categories";
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
  const { useCase, fromDeck = false } = route.params;
  const { width } = useWindowDimensions();
  const heroH = 220;
  const tone = useCaseTone(useCase);

  const [regulations, setRegulations] = useState(null);
  const [starred, setStarred] = useState(false);
  const [pkg, setPkg] = useState(null);
  const [pkgError, setPkgError] = useState(null);

  useEffect(() => {
    fetchRegulations({ limit: 500 }).then(setRegulations);
    getDiscoverState().then((s) => setStarred(s.starred.includes(useCase.id)));
  }, [useCase.id]);

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

  useEffect(() => {
    if (!regulations) return;
    let cancelled = false;
    setPkg(null);
    setPkgError(null);
    fetchGuardrailPackage(useCase, matched)
      .then((p) => { if (!cancelled) setPkg(p); })
      .catch((err) => { if (!cancelled) setPkgError(err.message); });
    return () => { cancelled = true; };
  }, [regulations, matched, useCase]);

  const rego = pkg?.files?.["policies/rules.rego"] || "";
  const regoPreview = rego.split("\n").slice(0, 40).join("\n");
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
        <UseCaseArt useCase={useCase} width={width} height={heroH} style={StyleSheet.absoluteFill} />
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
            {(useCase.categories || []).map((slug) => (
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
          <Scale size={16} color={colors.textMain} />
          <Text style={styles.h2}>Guardrail policy</Text>
        </View>
        {pkgError ? (
          <Text style={[styles.muted, { color: colors.danger }]}>{pkgError}</Text>
        ) : !pkg ? (
          <Text style={styles.muted}>Generating and verifying with opa…</Text>
        ) : (
          <>
            <Text style={styles.sectionNote}>
              Verified with opa {pkg.verification.opa_version}: check passed, {pkg.verification.tests.passed}/
              {pkg.verification.tests.total} generated tests passing.
            </Text>
            <View style={[styles.code, { borderLeftColor: tone }]}>
              <Text style={styles.codeText}>{regoPreview}{rego.split("\n").length > 40 ? "\n…" : ""}</Text>
            </View>
            <TouchableOpacity
              style={styles.cta}
              onPress={() => navigation.navigate("ImpactDiff", { useCaseId: useCase.id, handoffAt: Date.now() })}
              accessibilityRole="button"
            >
              <Text style={styles.ctaText}>Review and dispatch in Audit</Text>
            </TouchableOpacity>
          </>
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

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { paddingBottom: 40 },
  hero: { justifyContent: "space-between", backgroundColor: colors.primary },
  heroBar: { flexDirection: "row", justifyContent: "space-between", padding: 14 },
  heroBtn: { padding: 8, borderRadius: 999, backgroundColor: "rgba(0,0,0,0.25)" },
  heroText: { padding: 18, gap: 8 },
  cats: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  tag: { paddingHorizontal: 9, paddingVertical: 5, borderRadius: 999 },
  tagText: { fontFamily: type.fontFamilyMedium, fontSize: 10, letterSpacing: 0.6, color: "#FFFFFF", textTransform: "uppercase" },
  title: { fontFamily: type.fontFamilyBold, fontSize: 22, lineHeight: 27, color: "#FFFFFF" },
  section: { paddingHorizontal: 20, paddingTop: 20, gap: 10 },
  h2Row: { flexDirection: "row", alignItems: "center", gap: 8 },
  h2: { fontFamily: type.fontFamilyBold, fontSize: 15, color: colors.textMain },
  sectionNote: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, lineHeight: 17 },
  body: { fontFamily: type.fontFamily, fontSize: 14, color: colors.textMain, lineHeight: 21 },
  muted: { fontFamily: type.fontFamily, fontSize: 13, color: colors.textMuted, lineHeight: 19 },
  provenance: { fontFamily: type.fontFamilyMedium, fontSize: 11, color: colors.textMuted, letterSpacing: 0.4, textTransform: "uppercase" },
  linkRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  link: { fontFamily: type.fontFamily, fontSize: 12, color: colors.secondary, flex: 1 },
  pills: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  tierTap: { flexDirection: "row", alignItems: "center", gap: 4 },
  composition: { gap: 12, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 12 },
  compositionNote: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, lineHeight: 17 },
  family: { gap: 8 },
  familyHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 },
  familyLabel: { flex: 1, fontFamily: type.fontFamilyBold, fontSize: 12.5, color: colors.textMain },
  riskChips: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  riskChip: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.background },
  riskChipText: { fontFamily: type.fontFamilyMedium, fontSize: 11.5, color: colors.textMain },
  riskDescription: { fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMain, lineHeight: 18, paddingLeft: 10, borderLeftWidth: 2, borderLeftColor: colors.border },
  why: { gap: 8, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 12 },
  whyTitle: { fontFamily: type.fontFamilyBold, fontSize: 13, color: colors.textMain },
  whyText: { fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMain, lineHeight: 18 },
  whyPhrase: { fontFamily: type.fontFamilyMedium, color: colors.primary },
  basis: { gap: 2, paddingLeft: 10, borderLeftWidth: 2, borderLeftColor: colors.border },
  basisRef: { fontFamily: type.fontFamilyMedium, fontSize: 11, color: colors.textMuted, letterSpacing: 0.3, textTransform: "uppercase" },
  group: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, backgroundColor: colors.surface, overflow: "hidden" },
  groupHead: { flexDirection: "row", alignItems: "flex-start", gap: 8, padding: 12 },
  groupMeta: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  groupTitle: { flex: 1, fontFamily: type.fontFamilyBold, fontSize: 13.5, color: colors.textMain },
  groupKind: { fontFamily: type.fontFamilyMedium, fontSize: 10.5, letterSpacing: 0.5, textTransform: "uppercase" },
  groupCount: { flexShrink: 0, minWidth: 26, textAlign: "center", paddingHorizontal: 7, paddingVertical: 2, borderRadius: 999, backgroundColor: colors.background, fontFamily: type.fontFamilyMedium, fontSize: 11, color: colors.textMuted, fontVariant: ["tabular-nums"] },
  groupWhy: { fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMain, lineHeight: 18 },
  groupBody: { paddingHorizontal: 12, paddingBottom: 12, gap: 8, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 12 },
  callout: { flexDirection: "row", gap: 10, alignItems: "flex-start", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 12 },
  calloutText: { flex: 1, fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMain, lineHeight: 18 },
  code: { backgroundColor: "#0F1E3D", borderRadius: radius.card, borderLeftWidth: 4, padding: 14 },
  codeText: { fontFamily: "Courier", fontSize: 11, lineHeight: 16, color: "#E6EDF7" },
  cta: { backgroundColor: colors.accent, paddingVertical: 13, borderRadius: radius.button, alignItems: "center" },
  ctaText: { fontFamily: type.fontFamilyBold, fontSize: 14, color: colors.primary },
  footer: { position: "absolute", left: 0, right: 0, bottom: 0, flexDirection: "row", gap: 10, padding: 14, backgroundColor: colors.background, borderTopWidth: 1, borderTopColor: colors.border },
  footBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 13, borderRadius: radius.button },
  footBtnGhost: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  footBtnGhostText: { fontFamily: type.fontFamilyMedium, fontSize: 14, color: colors.textMain },
  footBtnPrimary: { backgroundColor: colors.primary },
  footBtnPrimaryText: { fontFamily: type.fontFamilyBold, fontSize: 14, color: "#FFFFFF" },
});
