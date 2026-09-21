import { useSyncExternalStore } from 'react';
import { useColorScheme as useRNColorScheme } from 'react-native';

const subscribeToNothing = (): (() => void) => () => {};

/**
 * To support static rendering, this value needs to be re-calculated on the client side for web
 */
export function useColorScheme() {
  const colorScheme = useRNColorScheme();

  return useSyncExternalStore(
    subscribeToNothing,
    () => colorScheme ?? 'light',
    () => 'light',
  );
}
