// babel.config.js
// Expo + React Native default preset. Kept intentionally minimal so plugin
// drift between Expo SDKs doesn't bite. Add module-resolver / reanimated
// plugins here when you need them.

module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
  };
};
