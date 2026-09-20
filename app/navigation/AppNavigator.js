import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Compass, Radar, Telescope, Newspaper } from "lucide-react-native";

import { colors, type } from "../theme";
import AppHeader from "../components/AppHeader";
import DashboardScreen from "../screens/DashboardScreen";
import HorizonScreen from "../screens/HorizonScreen";
import TrendingRisksScreen from "../screens/TrendingRisksScreen";
import DiscoverScreen from "../screens/DiscoverScreen";
import DeckScreen from "../screens/DeckScreen";
import UseCaseDetailScreen from "../screens/UseCaseDetailScreen";

const Tab = createBottomTabNavigator();
const DiscoverStack = createNativeStackNavigator();

// Discover is the landing flow: category cloud -> swipe deck -> use-case
// detail. Its screens carry their own back controls, so the stack draws no
// header of its own; the tab's AppHeader stays on top throughout.
function DiscoverFlow() {
  return (
    <DiscoverStack.Navigator screenOptions={{ headerShown: false }}>
      <DiscoverStack.Screen name="Discover" component={DiscoverScreen} />
      {/* The deck's right-swipe is "next card"; the stack's own swipe-back
          gesture would otherwise claim the same drag and pop to Discover. */}
      <DiscoverStack.Screen name="Deck" component={DeckScreen} options={{ gestureEnabled: false }} />
      <DiscoverStack.Screen name="UseCaseDetail" component={UseCaseDetailScreen} />
    </DiscoverStack.Navigator>
  );
}

export default function AppNavigator() {
  return (
    <Tab.Navigator
      initialRouteName="DiscoverFlow"
      screenOptions={{
        header: () => <AppHeader />,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontFamily: type.fontFamilyMedium, fontSize: 11 },
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
      }}
    >
      {/* Four tabs: Discover (use cases and their risks), Trending (today's
          stories on those risks), Radar (the numbers), Horizon (forecasts).
          The Use Cases / Audit / Dispatch tabs -- the opa/Rego generation and
          GitHub push flow -- were removed when guardrails became "existing
          open-source controls per risk" rather than generated policy. */}
      <Tab.Screen
        name="DiscoverFlow"
        component={DiscoverFlow}
        options={{
          title: "Discover",
          tabBarLabel: "Discover",
          tabBarIcon: ({ color, size }) => <Compass color={color} size={size} />,
        }}
      />
      <Tab.Screen
        name="Trending"
        component={TrendingRisksScreen}
        options={{
          title: "Trending Risks",
          tabBarLabel: "Trending",
          tabBarIcon: ({ color, size }) => <Newspaper color={color} size={size} />,
        }}
      />
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          title: "LegalGuard",
          tabBarLabel: "Radar",
          tabBarIcon: ({ color, size }) => <Radar color={color} size={size} />,
        }}
      />
      <Tab.Screen
        name="Horizon"
        component={HorizonScreen}
        options={{
          title: "Regulatory Horizon",
          tabBarLabel: "Horizon",
          tabBarIcon: ({ color, size }) => <Telescope color={color} size={size} />,
        }}
      />
    </Tab.Navigator>
  );
}
