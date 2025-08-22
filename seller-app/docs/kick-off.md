Выполни следующие шаги в папке `seller-app`:

1. Инициализируй Expo проект:
   ```bash
   npx create-expo-app@latest . --template
Установи Tamagui и зависимости:


npm install tamagui @tamagui/core @tamagui/config @tamagui/themed react-native-safe-area-context react-native-web
Установи компилятор Tamagui:


npm install --save-dev @tamagui/static
Настрой файл tamagui.config.ts в корне:


import { createTamagui } from 'tamagui'
import { config } from '@tamagui/config'

const tamaguiConfig = createTamagui(config)

type Conf = typeof tamaguiConfig
declare module 'tamagui' {
  interface TamaguiCustomConfig extends Conf {}
}

export default tamaguiConfig
Обнови app/_layout.tsx или App.tsx:


import { TamaguiProvider, Text, YStack } from 'tamagui'
import config from './tamagui.config'

export default function App() {
  return (
    <TamaguiProvider config={config}>
      <YStack f={1} ai="center" jc="center">
        <Text>Hello from Tamagui 👋</Text>
      </YStack>
    </TamaguiProvider>
  )
}
Создай src/screens/HelloZeya888Screen.tsx:


import { YStack, Text } from 'tamagui'

export const HelloWorldScreen = () => (
  <YStack f={1} ai="center" jc="center">
    <Text fontSize="$8">Hello Zeya888 🎉</Text>
  </YStack>
)
Создай тест src/__tests__/HelloZeya888Screen.test.tsx:


import { render } from '@testing-library/react-native'
import { HelloWorldScreen } from '../screens/HelloZeya888Screen'

test('renders hello screen', () => {
  const { getByText } = render(<HelloWorldScreen />)
  expect(getByText(/Hello World/i)).toBeTruthy()
})
Добавь в package.json:


"scripts": {
  "test": "jest",
  "web": "expo start --web"
},
"jest": {
  "preset": "jest-expo"
}
Документация (docs/README.md):


# Seller App – React Native + Tamagui Setup

## 🚀 Запуск
- Web: `npm run web`
- Android: `npx expo run:android`
- iOS: `npx expo run:ios`

## ✅ Тесты
- Запуск тестов: `npm test`

## 🧱 Структура
- `src/screens/HelloZeya888Screen.tsx` – первый экран
- `tamagui.config.ts` – настройки UI
Убедись, что всё работает:

запусти npm run web и опиши как проверить HelloZeya888 Screen

выполни npm test и проверь юнит-тест