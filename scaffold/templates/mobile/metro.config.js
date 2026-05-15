// metro.config.js
// Default Expo Metro config. Customise here if you need to add SVG transform,
// monorepo workspace roots, etc.

const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

module.exports = config;
