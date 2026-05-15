// src/screens/home/components/HomeHeader.tsx
// Screen-local header. Presentational only — no data fetching, no
// navigation calls.

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export interface HomeHeaderProps {
  title: string;
}

export function HomeHeader({ title }: HomeHeaderProps): JSX.Element {
  return (
    <View style={styles.root} accessibilityRole="header">
      <Text style={styles.title}>{title}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#e5e5e5',
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
  },
});
