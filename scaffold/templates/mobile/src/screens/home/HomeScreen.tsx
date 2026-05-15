// src/screens/home/HomeScreen.tsx
// Navigator-registered Home screen. Composes the screen-local pieces from
// components/, hooks/, services/, types/. No business logic lives here.

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { HomeHeader } from './components/HomeHeader';
import { useHomeData } from './hooks/useHomeData';

export function HomeScreen(): JSX.Element {
  const { data, isLoading, isError } = useHomeData();

  return (
    <SafeAreaView style={styles.root} edges={['top']}>
      <HomeHeader title="Home" />
      <View style={styles.body}>
        {isLoading ? (
          <Text>Loading...</Text>
        ) : isError ? (
          <Text>Unable to load home data.</Text>
        ) : (
          <Text>{data?.message ?? 'No data.'}</Text>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  body: {
    flex: 1,
    padding: 16,
  },
});
