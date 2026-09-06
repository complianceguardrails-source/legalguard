import React, { useEffect, useState } from "react";
import { View, Text, Image, StyleSheet } from "react-native";
import { GitBranch } from "lucide-react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors, type, radius } from "../theme";
import { getGitHubCredentials } from "../lib/auth";

// Persistent banner shown identically on every tab (matches the Base44
// reference design), replacing React Navigation's default per-screen header
// title. Each screen keeps its own in-body heading for what's specific to
// that tab -- this banner is just brand + "which GitHub identity is this
// session's dispatch pipeline actually going to push to."
export default function AppHeader() {
  const insets = useSafeAreaInsets();
  const [username, setUsername] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getGitHubCredentials().then(({ username: u }) => {
      if (!cancelled) setUsername(u || null);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <View style={[styles.container, { paddingTop: insets.top + 10 }]}>
      <View style={styles.left}>
        <Image source={require("../assets/icon.png")} style={styles.icon} />
        <View style={{ flexShrink: 1 }}>
          <Text style={styles.title}>LegalGuard</Text>
          <Text style={styles.subtitle} numberOfLines={1}>
            Guardrail Orchestrator for Regulated AI
          </Text>
        </View>
      </View>
      <View style={styles.orgBadge}>
        <GitBranch size={11} color="#FFFFFF" />
        <Text style={styles.orgBadgeText} numberOfLines={1}>
          {username ? `@${username}` : "Not connected"}
        </Text>
        <View style={[styles.statusDot, { backgroundColor: username ? colors.accent : colors.textMuted }]} />
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
  title: { fontFamily: type.fontFamilyBold, fontSize: 17, color: "#FFFFFF" },
  subtitle: { fontFamily: type.fontFamily, fontSize: 10, color: "#9FB0C9", marginTop: 1 },
  orgBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: colors.secondary,
    borderRadius: radius.chip,
    paddingHorizontal: 10,
    paddingVertical: 6,
    maxWidth: 150,
    marginLeft: 8,
  },
  orgBadgeText: { fontFamily: type.fontFamilyMedium, fontSize: 11, color: "#FFFFFF", flexShrink: 1 },
  statusDot: { width: 6, height: 6, borderRadius: 3 },
});
