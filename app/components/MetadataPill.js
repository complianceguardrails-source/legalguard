// Shared high-contrast metadata pill -- one visual language for every card
// across Radar/Inventory/Audit/Horizon so a legal, compliance, or engineering
// reader can scan the same row and pull out the fact relevant to them. Every
// call site supplies real data already present in the schema; this component
// only renders it, it never invents a value (no fabricated coverage
// percentages, versions, or sync states -- see guardrailThresholds.js for why
// that line matters in this project).
import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, type, radius } from "../theme";

const VARIANTS = {
  danger: { background: `${colors.danger}22`, text: colors.danger },
  success: { background: `${colors.success}1F`, text: colors.success },
  warning: { background: `${colors.warning}33`, text: colors.secondary },
  neutral: { background: "#F1F5F9", text: colors.secondary },
  primary: { background: colors.primary, text: "#FFFFFF" },
  info: { background: `${colors.secondary}1A`, text: colors.secondary },
};

// backgroundColor/textColor let a caller match an existing, already-specific
// hue (e.g. RISK_TIER_STYLE's distinct high_risk orange) without adding a new
// named variant for every one-off shade.
export default function MetadataPill({ label, variant = "neutral", icon: Icon, iconSize = 10, backgroundColor, textColor }) {
  const fallback = VARIANTS[variant] || VARIANTS.neutral;
  const background = backgroundColor || fallback.background;
  const text = textColor || fallback.text;
  return (
    <View style={[styles.pill, { backgroundColor: background }]}>
      {Icon && <Icon size={iconSize} color={text} style={styles.icon} />}
      <Text style={[styles.text, { color: text }]} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.chip,
  },
  icon: { marginRight: 3 },
  text: { fontFamily: type.fontFamilyMedium, fontSize: 10 },
});
