// One use case in depth: what it is, the risk profile the data actually
// holds for it, every regulation matched to it, and the guardrail policy
// the generation service produces for it -- verified with opa before it
// gets here. Deployment is one more deliberate step, on the Audit screen.

import React, { useEffect, useMemo, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, useWindowDimensions, ActivityIndicator, Linking } from "react-native";
import { ArrowLeft, Scale, ShieldCheck, Star, ExternalLink } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchRegulations } from "../lib/api";
import { fetchGuardrailPackage } from "../lib/generator";
import { categoryLabel, categoryTone, useCaseTone, TIER_LABEL } from "../lib/categories";
import { getDiscoverState, toggleStar } from "../lib/discoverState";
import UseCaseArt from "../components/UseCaseArt";
import RegulationCard from "../components/RegulationCard";
import MetadataPill from "../components/MetadataPill";

const SOURCE_LABEL = { github_mined: "Mined from GitHub", huggingface_mined: "Mined from Hugging Face", curated: "Hand-curated", user_submitted: "User-submitted" };
const TIER_VARIANT = { prohibited: "danger", high_risk: "warning", limited_risk: "info", minimal_risk: "success", unclassified: "neutral" };

export default function UseCaseDetailScreen({ route, navigation }) {
  const { useCase } = route.params;
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

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
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
        <Text style={styles.provenance}>{SOURCE_LABEL[useCase.source] || useCase.source}</Text>
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
          <MetadataPill label={TIER_LABEL[useCase.risk_tier] || "Unclassified"} variant={TIER_VARIANT[useCase.risk_tier] || "neutral"} />
          {!!useCase.parent_sector && <MetadataPill label={useCase.parent_sector} variant="neutral" />}
          {!!useCase.modality && <MetadataPill label={useCase.modality.replace("_", " ")} variant="neutral" />}
          {!!useCase.model_modality && <MetadataPill label={useCase.model_modality} variant="info" />}
          {!!useCase.system_interface_type && <MetadataPill label={useCase.system_interface_type} variant="info" />}
          {(useCase.agent_operational_tools || []).map((t) => <MetadataPill key={t} label={t} variant="warning" />)}
        </View>
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
          matched.map((r) => <RegulationCard key={r.reg_id} item={r} />)
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
  callout: { flexDirection: "row", gap: 10, alignItems: "flex-start", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.card, padding: 12 },
  calloutText: { flex: 1, fontFamily: type.fontFamily, fontSize: 12.5, color: colors.textMain, lineHeight: 18 },
  code: { backgroundColor: "#0F1E3D", borderRadius: radius.card, borderLeftWidth: 4, padding: 14 },
  codeText: { fontFamily: "Courier", fontSize: 11, lineHeight: 16, color: "#E6EDF7" },
  cta: { backgroundColor: colors.accent, paddingVertical: 13, borderRadius: radius.button, alignItems: "center" },
  ctaText: { fontFamily: type.fontFamilyBold, fontSize: 14, color: colors.primary },
});
