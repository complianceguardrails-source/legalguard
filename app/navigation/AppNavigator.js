import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Radar, Database, Scale, Telescope, Rocket } from "lucide-react-native";

import { colors, type } from "../theme";
import AppHeader from "../components/AppHeader";
import DashboardScreen from "../screens/DashboardScreen";
import KnowledgeBaseScreen from "../screens/KnowledgeBaseScreen";
import ImpactDiffScreen from "../screens/ImpactDiffScreen";
import HorizonScreen from "../screens/HorizonScreen";
import GitOpsConsoleScreen from "../screens/GitOpsConsoleScreen";

const Tab = createBottomTabNavigator();

export default function AppNavigator() {
  return (
    <Tab.Navigator
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
