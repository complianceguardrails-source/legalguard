import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, Linking } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { FileWarning, ExternalLink, ShieldCheck, ShieldAlert, HelpCircle, Users, Scale, Code2, TrendingUp } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import MetadataPill from "./MetadataPill";

function getHostname(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

// Matches ingestion/source_url_classifier.py's three states. 'unknown'
// gets a neutral, not-alarming icon -- it means "not yet verified", not
// "suspicious".
const SOURCE_BADGE = {
  primary: { icon: ShieldCheck, color: colors.success, label: "Primary source" },
  secondary: { icon: ShieldAlert, color: colors.warning, label: "Secondary source" },
  unknown: { icon: HelpCircle, color: colors.textMuted, label: "Unverified source" },
};

// Matches ingestion/tagger.py::classify_origin_driver's four categories and
// sources/horizon_forecaster.py's ORIGIN_DRIVER_LABELS -- what plausibly
// prompted this regulation to exist, not a certified causal claim (see
// schema.sql's comment on origin_driver_category: "treat as a hypothesis to
// confirm"). Omitted entirely when the tagger hasn't classified this row.
const ORIGIN_DRIVER_LABELS = {
  market_scandal: "Market Scandal",
  capability_leap: "Capability Leap",
  geopolitical_sovereignty: "Geopolitical Sovereignty",
  standards_harmonization: "Standards Harmonization",
};

/** Shared regulation summary card -- used on both the Radar dashboard
 * (recent/pending regulations feed) and the Audit screen (full list to
 * select from). Keeping this in one place means both surfaces show the
 * same jurisdiction/dispatch/impact/source-provenance badges consistently. */
export default function RegulationCard({ item, selected, onPress }) {
  const badge = SOURCE_BADGE[item.source_url_classification] || SOURCE_BADGE.unknown;
  const BadgeIcon = badge.icon;
  const navigation = useNavigation();
  const useCaseCount = (item.affected_use_case_ids || []).length;
  const driverLabel = ORIGIN_DRIVER_LABELS[item.origin_driver_category];

  return (
    <TouchableOpacity style={[styles.regRow, selected && styles.regRowSelected]} onPress={onPress} disabled={!onPress}>
      <View style={styles.regTopRow}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <MetadataPill label={item.jurisdiction} variant="neutral" />
          {!!driverLabel && <MetadataPill label={driverLabel.toUpperCase()} variant="danger" icon={TrendingUp} />}
        </View>
        {/* Real count from the tagger's affected_use_case_ids match, not a
            placeholder -- 0 is shown plainly rather than hidden, since "no
            matches yet" is itself useful signal. */}
        <MetadataPill label={`${useCaseCount} use case${useCaseCount === 1 ? "" : "s"}`} variant="neutral" icon={Users} />
      </View>

      <View style={{ flexDirection: "row", alignItems: "flex-start", marginTop: 8 }}>
        <FileWarning size={14} color={colors.secondary} style={{ marginRight: 8, marginTop: 2 }} />
        <View style={{ flex: 1 }}>
          <Text style={styles.regTitle}>{item.title || item.official_title}</Text>
          <Text style={styles.regMeta}>{item.issuing_body}</Text>
          {!!item.statutory_text && (
            <Text style={styles.regSummary} numberOfLines={2}>
              {item.statutory_text}
            </Text>
          )}
        </View>
      </View>

      <View style={styles.regBottomRow}>
        <Text style={styles.regEffective}>
          {item.effective_date ? `Effective ${item.effective_date}` : "Effective date TBD"}
        </Text>
      </View>

      {!!item.source_url && (
        <View style={styles.sourceRow}>
          <ExternalLink size={12} color={colors.textMuted} />
          <Text style={styles.sourceText} numberOfLines={1}>
            {getHostname(item.source_url)}
          </Text>
          <BadgeIcon size={12} color={badge.color} style={{ marginLeft: 6 }} />
          <Text style={[styles.sourceBadgeText, { color: badge.color }]}>{badge.label}</Text>
        </View>
      )}

      {/* One button for a non-technical reader (the actual statute text),
          one for an engineer (which use cases/guardrails this regulation
          maps to) -- both real navigations, no placeholder targets. */}
      <View style={styles.actionRow}>
        <TouchableOpacity
          style={[styles.actionButton, !item.source_url && styles.actionButtonDisabled]}
          disabled={!item.source_url}
          onPress={() => Linking.openURL(item.source_url)}
        >
          <Scale size={12} color={colors.secondary} style={{ marginRight: 5 }} />
          <Text style={styles.actionButtonText}>View Legal Text</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate("ImpactDiff", { regId: item.reg_id })}
        >
          <Code2 size={12} color={colors.secondary} style={{ marginRight: 5 }} />
          <Text style={styles.actionButtonText}>View Code Spec</Text>
        </TouchableOpacity>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  regRow: {
    backgroundColor: colors.surface,
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 12,
    marginBottom: 10,
  },
  regRowSelected: { borderColor: colors.accent, borderWidth: 1.5 },
  regTopRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 6 },
  regTitle: { fontFamily: type.fontFamilyMedium, fontSize: 13, color: colors.textMain, marginBottom: 2 },
  regMeta: { fontFamily: type.fontFamily, fontSize: 11, color: colors.textMuted, marginBottom: 4 },
  regSummary: { fontFamily: type.fontFamily, fontSize: 11, color: colors.textMuted, lineHeight: 15 },
  regBottomRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  regEffective: { fontFamily: type.fontFamily, fontSize: 11, color: colors.textMuted },
  sourceRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 8 },
  sourceText: { fontFamily: type.fontFamily, fontSize: 10, color: colors.textMuted, flexShrink: 1 },
  sourceBadgeText: { fontFamily: type.fontFamilyMedium, fontSize: 10 },
  actionRow: { flexDirection: "row", gap: 8, marginTop: 10 },
  actionButton: {
    flex: 1,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.button,
    paddingVertical: 7,
  },
  actionButtonDisabled: { opacity: 0.4 },
  actionButtonText: { fontFamily: type.fontFamilyMedium, fontSize: 11, color: colors.secondary },
});
