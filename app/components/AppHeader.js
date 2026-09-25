import React from "react";
import { View, Text, Image, StyleSheet } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors, type, radius } from "../theme";

// Persistent banner shown identically on every tab, replacing React
// Navigation's default per-screen header title. Each screen keeps its own
// in-body heading for what's specific to that tab; this is just the brand.
export default function AppHeader() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.container, { paddingTop: insets.top + 10 }]}>
      <View style={styles.left}>
        <Image source={require("../assets/icon.png")} style={styles.icon} />
        <View style={{ flexShrink: 1 }}>
          <Text style={styles.title}>LegalGuard</Text>
          <Text style={styles.subtitle} numberOfLines={1}>
            Responsible AI in Action
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: colors.primary,
    paddingHorizontal: 16,
    paddingBottom: 14,
  },
  left: { flexDirection: "row", alignItems: "center", gap: 10, flexShrink: 1 },
  icon: { width: 34, height: 34, borderRadius: 8 },
  title: { fontFamily: type.fontFamilyBold, fontSize: 21, color: "#FFFFFF" },
  subtitle: { fontFamily: type.fontFamily, fontSize: 12.5, color: "#9FB0C9", marginTop: 2 },
});
