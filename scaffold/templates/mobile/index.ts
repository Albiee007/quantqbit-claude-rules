// index.ts — app entry. registerRootComponent registers App as the "main"
// component and sets up the environment the same way in Expo Go and in
// native builds.

import { registerRootComponent } from 'expo';

import App from './App';

registerRootComponent(App);
