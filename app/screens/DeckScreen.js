// The deck: one use case at a time as a swipe card. Swipe one way to
// dismiss it, the other way to open its detail; star it from the card.
// No gesture on this screen ever deploys anything -- deployment stays a
// deliberate action on the Audit screen, behind the detail view.
//
// Built on React Native's own PanResponder + Animated rather than
// gesture-handler/reanimated: a fling-off card doesn't need them, and
// skipping them means no babel plugin and no new native modules.

import React, { useEffect, useMemo, useRef, useState } from "react";
import { View, Text, StyleSheet, Animated, PanResponder, TouchableOpacity, useWindowDimensions, ActivityIndicator } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { ArrowLeft, RotateCcw, X, Search } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchUseCases } from "../lib/api";
import { categoryLabel } from "../lib/categories";
import { getDiscoverState, toggleStar, dismiss, clearDismissed } from "../lib/discoverState";
import UseCaseCard from "../components/UseCaseCard";

// The one place the mapping lives. As specified: right dismisses, left
// digs deeper. Flip these two if that ever changes.
const SWIPE = { dismiss: "right", detail: "left" };
const THRESHOLD = 110; // px of horizontal travel that commits a swipe
const FLING_MS = 220;

export default function DeckScreen({ route, navigation }) {
  const { slugs = [], mode = "explore" } = route.params || {};
  const { width, height } = useWindowDimensions();
  const cardW = Math.min(width - 40, 420);
  const cardH = Math.min(cardW * 1.38, height * 0.62);

  const [all, setAll] = useState(null);
  const [state, setState] = useState({ starred: [], dismissed: [] });
  const pan = useRef(new Animated.ValueXY()).current;

  useEffect(() => {
    fetchUseCases().then(setAll);
  }, []);
  useFocusEffect(
    React.useCallback(() => {
      getDiscoverState().then((s) => setState({ starred: s.starred, dismissed: s.dismissed }));
    }, [])
  );

  const deck = useMemo(() => {
    if (!all) return [];
    const starred = new Set(state.starred);
    const dismissed = new Set(state.dismissed);
    if (mode === "starred") return all.filter((uc) => starred.has(uc.id));
    return all.filter(
      (uc) => !dismissed.has(uc.id) && (slugs.length === 0 || (uc.categories || []).some((s) => slugs.includes(s)))
    );
  }, [all, state, slugs, mode]);

  // The deck itself shrinks as cards are dismissed, so the top card is
  // always the first one; no cursor to keep in sync.
  const current = deck[0];
  const next = deck[1];

  const rotate = pan.x.interpolate({ inputRange: [-width, 0, width], outputRange: ["-12deg", "0deg", "12deg"] });
  const dismissHint = pan.x.interpolate({ inputRange: SWIPE.dismiss === "right" ? [0, THRESHOLD] : [-THRESHOLD, 0], outputRange: SWIPE.dismiss === "right" ? [0, 1] : [1, 0], extrapolate: "clamp" });
  const detailHint = pan.x.interpolate({ inputRange: SWIPE.detail === "left" ? [-THRESHOLD, 0] : [0, THRESHOLD], outputRange: SWIPE.detail === "left" ? [1, 0] : [0, 1], extrapolate: "clamp" });

  const settle = () => Animated.spring(pan, { toValue: { x: 0, y: 0 }, useNativeDriver: false, friction: 6 }).start();
  const fling = (dir, then) =>
    Animated.timing(pan, { toValue: { x: dir === "right" ? width * 1.2 : -width * 1.2, y: 0 }, duration: FLING_MS, useNativeDriver: false }).start(() => {
      pan.setValue({ x: 0, y: 0 });
      then();
    });

  const onDismiss = () => {
    if (!current) return;
    fling(SWIPE.dismiss, async () => {
      if (mode !== "starred") await dismiss(current.id);
      setState((s) => ({ ...s, dismissed: [...s.dismissed, current.id] }));
    });
  };
  const onDetail = () => {
    if (!current) return;
    // The card comes back: opening detail is a look, not a decision.
    settle();
    navigation.navigate("UseCaseDetail", { useCase: current });
  };

  const responder = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 6 && Math.abs(g.dx) > Math.abs(g.dy),
        onPanResponderMove: Animated.event([null, { dx: pan.x, dy: pan.y }], { useNativeDriver: false }),
        // A card drag never yields to a parent. Without this, rightward
        // drags were being terminated mid-swipe -- a navigator upstream
        // treats them as a back gesture -- so right-swipes never released,
        // while left-swipes worked. Found on web, refused on every platform.
        onPanResponderTerminationRequest: () => false,
        onPanResponderRelease: (_, g) => {
          const dir = g.dx > THRESHOLD ? "right" : g.dx < -THRESHOLD ? "left" : null;
          if (dir === SWIPE.dismiss) onDismiss();
          else if (dir === SWIPE.detail) onDetail();
          else settle();
        },
        onPanResponderTerminate: settle,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [current?.id, mode]
  );

  const onStar = async () => {
    if (!current) return;
    const now = await toggleStar(current.id);
    setState((s) => ({ ...s, starred: now ? [...s.starred, current.id] : s.starred.filter((id) => id !== current.id) }));
  };

  const title = mode === "starred" ? "Starred" : slugs.length ? slugs.map(categoryLabel).join(" · ") : "All use cases";

  return (
    <View style={styles.screen}>
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => navigation.goBack()} hitSlop={10} accessibilityRole="button" accessibilityLabel="Back">
          <ArrowLeft size={20} color={colors.textMain} />
        </TouchableOpacity>
        <Text style={styles.topTitle} numberOfLines={1}>{title}</Text>
        <Text style={styles.counter}>{all ? `${deck.length} left` : ""}</Text>
      </View>

      {!all ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 60 }} />
      ) : !current ? (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>{mode === "starred" ? "Nothing starred yet" : "You've been through the deck"}</Text>
          <Text style={styles.emptyText}>
            {mode === "starred"
              ? "Star a use case from any card and it will collect here."
              : `${state.dismissed.length} dismissed on this device. They aren't deleted -- they're still in Use Cases and Audit.`}
          </Text>
          {mode !== "starred" && state.dismissed.length > 0 && (
            <TouchableOpacity
              style={styles.secondaryBtn}
              onPress={async () => { await clearDismissed(); setState((s) => ({ ...s, dismissed: [] })); }}
            >
              <RotateCcw size={14} color={colors.primary} />
              <Text style={styles.secondaryBtnText}>Bring dismissed back</Text>
            </TouchableOpacity>
          )}
        </View>
      ) : (
        <View style={styles.stage}>
          {next && (
            <View style={[styles.under, { width: cardW, height: cardH }]}>
              <UseCaseCard useCase={next} width={cardW} height={cardH} />
            </View>
          )}
          <Animated.View
            {...responder.panHandlers}
            style={[styles.top, { width: cardW, height: cardH, transform: [{ translateX: pan.x }, { translateY: pan.y }, { rotate }] }]}
          >
            <UseCaseCard useCase={current} width={cardW} height={cardH} starred={state.starred.includes(current.id)} onToggleStar={onStar} />
            <Animated.View style={[styles.hint, styles.hintDismiss, { opacity: dismissHint }]} pointerEvents="none">
              <X size={16} color="#FFFFFF" /><Text style={styles.hintText}>Dismiss</Text>
            </Animated.View>
            <Animated.View style={[styles.hint, styles.hintDetail, { opacity: detailHint }]} pointerEvents="none">
              <Search size={16} color="#FFFFFF" /><Text style={styles.hintText}>Details</Text>
            </Animated.View>
          </Animated.View>

          <View style={styles.legend}>
            <Text style={styles.legendText}>Swipe {SWIPE.detail} for details · swipe {SWIPE.dismiss} to dismiss</Text>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  topBar: { flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 20, paddingVertical: 12 },
  topTitle: { flex: 1, fontFamily: type.fontFamilyMedium, fontSize: 14, color: colors.textMain },
  counter: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, fontVariant: ["tabular-nums"] },
  stage: { flex: 1, alignItems: "center", justifyContent: "center" },
  under: { position: "absolute", transform: [{ scale: 0.95 }, { translateY: 14 }], opacity: 0.7 },
  top: { shadowColor: "#0B2545", shadowOpacity: 0.25, shadowRadius: 18, shadowOffset: { width: 0, height: 10 }, elevation: 8 },
  hint: { position: "absolute", top: 18, flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, backgroundColor: "rgba(0,0,0,0.45)" },
  hintDismiss: { left: 18 },
  hintDetail: { right: 18, top: 60 },
  hintText: { fontFamily: type.fontFamilyBold, fontSize: 12, color: "#FFFFFF", letterSpacing: 0.5, textTransform: "uppercase" },
  legend: { position: "absolute", bottom: 22 },
  legendText: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted },
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32, gap: 10 },
  emptyTitle: { fontFamily: type.fontFamilyBold, fontSize: 18, color: colors.textMain, textAlign: "center" },
  emptyText: { fontFamily: type.fontFamily, fontSize: 13, color: colors.textMuted, textAlign: "center", lineHeight: 19 },
  secondaryBtn: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 10, paddingHorizontal: 16, paddingVertical: 11, borderRadius: radius.button, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  secondaryBtnText: { fontFamily: type.fontFamilyMedium, fontSize: 13, color: colors.primary },
});
