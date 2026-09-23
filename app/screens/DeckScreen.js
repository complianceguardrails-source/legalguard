// The deck: one use case at a time as a swipe card. Swipe one way to open
// its detail, the other way to move on to the next; star it from the card.
// No gesture on this screen ever deploys anything -- deployment stays a
// deliberate action on the Audit screen, behind the detail view.
//
// Built on React Native's own PanResponder + Animated rather than
// gesture-handler/reanimated: a fling-off card doesn't need them, and
// skipping them means no babel plugin and no new native modules.

import React, { useEffect, useMemo, useRef, useState } from "react";
import { View, Text, StyleSheet, Animated, PanResponder, TouchableOpacity, useWindowDimensions, ActivityIndicator } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { ArrowLeft, RotateCcw, Search, ChevronRight } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchUseCases } from "../lib/api";
import { categoryLabel } from "../lib/categories";
import { getDiscoverState, toggleStar, clearDismissed } from "../lib/discoverState";
import UseCaseCard from "../components/UseCaseCard";

// The one place the mapping lives. As specified: left digs deeper, right
// moves on to the next card. Nothing on this screen dismisses; that is a
// deliberate button on the detail screen. Flip these if that ever changes.
const SWIPE = { detail: "left", next: "right" };
const THRESHOLD = 110; // px of travel that commits a swipe
const FLING_MS = 220;

export default function DeckScreen({ route, navigation }) {
  const { slugs = [], mode = "explore" } = route.params || {};
  const { width, height } = useWindowDimensions();
  const cardW = Math.min(width - 40, 420);
  const cardH = Math.min(cardW * 1.38, height * 0.62);

  const [all, setAll] = useState(null);
  const [state, setState] = useState({ starred: [], dismissed: [] });
  // Where you are in the deck. Down/up move it; dismiss removes the card
  // under it so the next one slides into place. Session-only.
  const [index, setIndex] = useState(0);
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
    const pool =
      mode === "starred"
        ? all.filter((uc) => starred.has(uc.id))
        : all.filter(
            (uc) => !dismissed.has(uc.id) && (slugs.length === 0 || (uc.categories || []).some((s) => slugs.includes(s)))
          );
    return pool;
  }, [all, state, slugs, mode]);

  // Dismissing the last card, or the pool shrinking under a stale cursor,
  // must never leave the cursor past the end.
  const at = Math.min(index, Math.max(deck.length - 1, 0));
  const current = deck[at];
  // Past the last card the deck wraps to the first, so browsing never
  // dead-ends; the hint says so before you let go.
  const nextAt = at + 1 < deck.length ? at + 1 : 0;
  const next = deck.length > 1 ? deck[nextAt] : undefined;
  const wraps = deck.length > 1 && at + 1 >= deck.length;

  // Arriving back from the detail's "Next card" button.
  useEffect(() => {
    if (route.params?.advance) setIndex((i) => (i + 1 < deck.length ? i + 1 : 0));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route.params?.advance]);

  const rotate = pan.x.interpolate({ inputRange: [-width, 0, width], outputRange: ["-12deg", "0deg", "12deg"] });
  const hintFor = (dir) =>
    pan.x.interpolate({ inputRange: dir === "right" ? [0, THRESHOLD] : [-THRESHOLD, 0], outputRange: dir === "right" ? [0, 1] : [1, 0], extrapolate: "clamp" });
  const detailHint = hintFor(SWIPE.detail);
  const nextHint = hintFor(SWIPE.next);

  const settle = () => Animated.spring(pan, { toValue: { x: 0, y: 0 }, useNativeDriver: false, friction: 6 }).start();
  const OFF = { right: { x: width * 1.2, y: 0 }, left: { x: -width * 1.2, y: 0 } };
  const fling = (dir, then) =>
    Animated.timing(pan, { toValue: OFF[dir], duration: FLING_MS, useNativeDriver: false }).start(() => {
      pan.setValue({ x: 0, y: 0 });
      then();
    });

  const onDetail = () => {
    if (!current) return;
    // Opening detail is a look, not a decision: the card stays where it is.
    settle();
    navigation.navigate("UseCaseDetail", { useCase: current, fromDeck: true, preferred: slugs });
  };
  const onNext = () => (deck.length > 1 ? fling(SWIPE.next, () => setIndex(nextAt)) : settle());

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
          if (dir === SWIPE.detail) onDetail();
          else if (dir === SWIPE.next) onNext();
          else settle();
        },
        onPanResponderTerminate: settle,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [current?.id, mode, at, deck.length]
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
        <Text style={styles.counter}>{all && current ? `${at + 1} of ${deck.length}` : ""}</Text>
      </View>

      {!all ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 60 }} />
      ) : !current ? (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>{mode === "starred" ? "Nothing starred yet" : "You've been through the deck"}</Text>
          <Text style={styles.emptyText}>
            {mode === "starred"
              ? "Star a use case from any card and it will collect here."
              : `${state.dismissed.length} dismissed on this device from their detail pages. They aren't deleted -- they're still in Use Cases and Audit.`}
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
              <UseCaseCard useCase={next} width={cardW} height={cardH} preferred={slugs} />
            </View>
          )}
          <Animated.View
            {...responder.panHandlers}
            style={[styles.top, { width: cardW, height: cardH, transform: [{ translateX: pan.x }, { translateY: pan.y }, { rotate }] }]}
          >
            <UseCaseCard useCase={current} width={cardW} height={cardH} starred={state.starred.includes(current.id)} onToggleStar={onStar} preferred={slugs} />
            <Animated.View style={[styles.hint, styles.hintNext, { opacity: nextHint }]} pointerEvents="none">
              <ChevronRight size={16} color="#FFFFFF" /><Text style={styles.hintText}>{wraps ? "Back to first" : "Next"}</Text>
            </Animated.View>
            <Animated.View style={[styles.hint, styles.hintDetail, { opacity: detailHint }]} pointerEvents="none">
              <Search size={16} color="#FFFFFF" /><Text style={styles.hintText}>Details</Text>
            </Animated.View>
          </Animated.View>

          <View style={styles.legend}>
            <Text style={styles.legendText}>Swipe {SWIPE.detail} for details · swipe {SWIPE.next} for the next card</Text>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  topBar: { flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 20, paddingVertical: 12 },
  topTitle: { flex: 1, fontFamily: type.fontFamilyMedium, fontSize: 15.5, color: colors.textMain },
  counter: { fontFamily: type.fontFamily, fontSize: 13.5, color: colors.textMuted, fontVariant: ["tabular-nums"] },
  stage: { flex: 1, alignItems: "center", justifyContent: "center" },
  under: { position: "absolute", transform: [{ scale: 0.95 }, { translateY: 14 }], opacity: 0.7 },
  top: { shadowColor: "#0B2545", shadowOpacity: 0.25, shadowRadius: 18, shadowOffset: { width: 0, height: 10 }, elevation: 8 },
  hint: { position: "absolute", top: 18, flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, backgroundColor: "rgba(0,0,0,0.45)" },
  hintNext: { left: 18 },
  hintDetail: { right: 18 },
  hintText: { fontFamily: type.fontFamilyBold, fontSize: 13.5, color: "#FFFFFF", letterSpacing: 0.5, textTransform: "uppercase" },
  legend: { position: "absolute", bottom: 22 },
  legendText: { fontFamily: type.fontFamily, fontSize: 13.5, color: colors.textMuted },
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32, gap: 10 },
  emptyTitle: { fontFamily: type.fontFamilyBold, fontSize: 18, color: colors.textMain, textAlign: "center" },
  emptyText: { fontFamily: type.fontFamily, fontSize: 14.5, color: colors.textMuted, textAlign: "center", lineHeight: 21 },
  secondaryBtn: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 10, paddingHorizontal: 16, paddingVertical: 11, borderRadius: radius.button, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  secondaryBtnText: { fontFamily: type.fontFamilyMedium, fontSize: 14.5, color: colors.primary },
});
