import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Compass, Radar, Database, Scale, Telescope, Rocket } from "lucide-react-native";

import { colors, type } from "../theme";
import AppHeader from "../components/AppHeader";
import DashboardScreen from "../screens/DashboardScreen";
import KnowledgeBaseScreen from "../screens/KnowledgeBaseScreen";
import ImpactDiffScreen from "../screens/ImpactDiffScreen";
import HorizonScreen from "../screens/HorizonScreen";
import GitOpsConsoleScreen from "../screens/GitOpsConsoleScreen";
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
      {/* Tab names/labels match Base44's generated app (Radar / Use Cases /
          Audit / Horizon / Dispatch) so the two front ends read as the same
          product -- component names stay as-is to avoid unrelated churn. */}
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
        name="Dashboard"
        component={DashboardScreen}
        options={{
          title: "LegalGuard",
          tabBarLabel: "Radar",
          tabBarIcon: ({ color, size }) => <Radar color={color} size={size} />,
        }}
      />
      <Tab.Screen
        name="KnowledgeBase"
        component={KnowledgeBaseScreen}
        options={{
          title: "Use Case Knowledge Base",
          tabBarLabel: "Use Cases",
          tabBarIcon: ({ color, size }) => <Database color={color} size={size} />,
        }}
      />
      <Tab.Screen
        name="ImpactDiff"
        component={ImpactDiffScreen}
        options={{
          title: "Legislative Audit",
          tabBarLabel: "Audit",
          tabBarIcon: ({ color, size }) => <Scale color={color} size={size} />,
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
      <Tab.Screen
        name="GitOpsConsole"
        component={GitOpsConsoleScreen}
        options={{
          title: "GitOps Dispatch Console",
          tabBarLabel: "Dispatch",
          tabBarIcon: ({ color, size }) => <Rocket color={color} size={size} />,
        }}
      />
    </Tab.Navigator>
  );
}
