// One use case as a swipe card: procedural art behind, white Poppins on
// top. Pure presentation -- gestures and persistence live in DeckScreen.

import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { Star } from "lucide-react-native";

import { type } from "../theme";
import { categoryLabel, orderedCategories, TIER_DOT, TIER_LABEL } from "../lib/categories";
import UseCaseArt from "./UseCaseArt";

const SOURCE_LABEL = { github_mined: "GitHub", huggingface_mined: "Hugging Face" }; // published provenance only

export default function UseCaseCard({ useCase, width, height, starred, onToggleStar, preferred = [] }) {
  // The categories the reader picked lead, so a card dealt in an ESG deck
  // says ESG first even when the system is also compliance and filings.
  const cats = orderedCategories(useCase, preferred).slice(0, 3);
  const blurb = (useCase.description || "").startsWith("Hugging Face model") ? "" : useCase.description;
  return (
    <View style={[styles.card, { width, height }]}>
      <UseCaseArt useCase={useCase} width={width} height={height} style={StyleSheet.absoluteFill} preferred={preferred} />

      {onToggleStar && (
        <TouchableOpacity
          onPress={onToggleStar}
          style={styles.star}
          accessibilityRole="button"
          accessibilityLabel={starred ? "Unstar" : "Star"}
          hitSlop={10}
        >
          <Star size={20} color="#FFFFFF" fill={starred ? "#FFFFFF" : "transparent"} />
        </TouchableOpacity>
      )}

      <View style={styles.body}>
        {!!useCase.translation?.application_short && (
          <View style={styles.adaptBadge}>
            <Text style={styles.adaptBadgeText}>{useCase.translation.application_short}</Text>
          </View>
        )}
        <View style={styles.cats}>
          {cats.map((slug) => (
            <View key={slug} style={styles.tag}>
              <Text style={styles.tagText}>{categoryLabel(slug)}</Text>
            </View>
          ))}
        </View>
        <Text style={styles.title} numberOfLines={3}>{useCase.name}</Text>
        {!!blurb && <Text style={styles.blurb} numberOfLines={3}>{blurb}</Text>}
        <View style={styles.meta}>
          <View style={styles.tier}>
            <View style={[styles.tierDot, { backgroundColor: TIER_DOT[useCase.risk_tier] || TIER_DOT.unclassified }]} />
            <Text style={styles.metaText}>{TIER_LABEL[useCase.risk_tier] || "Unclassified"}</Text>
          </View>
          <Text style={styles.metaText}>
            {[SOURCE_LABEL[useCase.source], (useCase.modality || "").replace("_", " ")].filter(Boolean).join(" · ")}
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 22, overflow: "hidden", backgroundColor: "#2B2D42", justifyContent: "flex-end" },
  star: { position: "absolute", top: 14, right: 14, padding: 8, borderRadius: 999, backgroundColor: "rgba(0,0,0,0.22)" },
  body: { padding: 18, gap: 8 },
  cats: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  adaptBadge: { alignSelf: "flex-start", backgroundColor: "rgba(255,255,255,0.22)", borderWidth: 1, borderColor: "rgba(255,255,255,0.45)", paddingHorizontal: 9, paddingVertical: 5, borderRadius: 999 },
  adaptBadgeText: { fontFamily: type.fontFamilyBold, fontSize: 10, letterSpacing: 0.5, color: "#FFFFFF", textTransform: "uppercase" },
  tag: { backgroundColor: "rgba(255,255,255,0.18)", paddingHorizontal: 9, paddingVertical: 5, borderRadius: 999 },
  tagText: { fontFamily: type.fontFamilyMedium, fontSize: 11.5, letterSpacing: 0.6, color: "#FFFFFF", textTransform: "uppercase" },
  title: { fontFamily: type.fontFamilyBold, fontSize: 20, lineHeight: 25, color: "#FFFFFF" },
  blurb: { fontFamily: type.fontFamily, fontSize: 14, lineHeight: 20, color: "rgba(255,255,255,0.85)" },
  meta: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8, marginTop: 2 },
  tier: { flexDirection: "row", alignItems: "center", gap: 6 },
  tierDot: { width: 7, height: 7, borderRadius: 4, borderWidth: 2, borderColor: "rgba(255,255,255,0.25)" },
  metaText: { fontFamily: type.fontFamilyMedium, fontSize: 12, letterSpacing: 0.4, color: "rgba(255,255,255,0.82)", textTransform: "uppercase" },
});
