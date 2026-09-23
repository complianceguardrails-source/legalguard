// Shares the "new since you last looked" counts between the tab bar (which
// draws the badges) and the screens (which clear them when opened).

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { AppState } from "react-native";

import { fetchNewCounts, markSeen } from "./whatsNew";

const EMPTY = { useCases: 0, regulations: 0, stories: 0 };
const WhatsNewContext = createContext({ counts: EMPTY, refresh: async () => {}, clear: async () => {} });

export function WhatsNewProvider({ children }) {
  const [counts, setCounts] = useState(EMPTY);

  const refresh = useCallback(async () => {
    try {
      setCounts(await fetchNewCounts());
    } catch {
      // Badges are a convenience; never let them break a screen.
    }
  }, []);

  const clear = useCallback(
    async (section) => {
      setCounts((c) => ({ ...c, [section]: 0 }));
      await markSeen(section);
    },
    []
  );

  useEffect(() => {
    refresh();
    // Coming back to the app is the moment to check again -- it is also
    // the only moment we can, with no server pushing to us.
    const sub = AppState.addEventListener("change", (state) => {
      if (state === "active") refresh();
    });
    return () => sub.remove();
  }, [refresh]);

  return <WhatsNewContext.Provider value={{ counts, refresh, clear }}>{children}</WhatsNewContext.Provider>;
}

export function useWhatsNew() {
  return useContext(WhatsNewContext);
}

/** Clears a section's badge whenever its screen is focused. */
export function useSeen(section) {
  const { clear } = useWhatsNew();
  return React.useCallback(() => {
    clear(section);
  }, [clear, section]);
}

/**
 * How many arrived since the last visit, captured the moment the count is
 * known and held for this visit, then the badge is cleared. Returning the
 * live count instead would show nothing: the first render happens before
 * the fetch returns, and clearing sets it to zero straight after.
 */
export function useArrived(section) {
  const { counts, clear } = useWhatsNew();
  const [arrived, setArrived] = useState(0);
  const n = counts[section] || 0;
  const onFocus = React.useCallback(() => {
    if (n > 0) {
      setArrived(n);
      clear(section);
    }
  }, [n, clear, section]);
  return [arrived, onFocus];
}
