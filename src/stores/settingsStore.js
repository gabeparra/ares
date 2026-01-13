import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useSettingsStore = create(
  persist(
    (set) => ({
      // User preferences can go here
      preferences: {},
      setPreference: (key, value) => set((state) => ({
        preferences: { ...state.preferences, [key]: value }
      })),
    }),
    {
      name: 'ares-settings-storage',
    }
  )
);

export default useSettingsStore;

