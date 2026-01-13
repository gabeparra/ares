import { create } from 'zustand';

const useUIStore = create((set) => ({
  // Tab state
  activeTab: 'chat',
  setActiveTab: (tab) => set({ activeTab: tab }),
  
  // Session state
  selectedSessionId: null,
  setSelectedSessionId: (sessionId) => set({ selectedSessionId: sessionId }),
  
  // Model/Provider state
  currentModel: '',
  setCurrentModel: (model) => set({ currentModel: model }),
  
  currentProvider: 'local',
  setCurrentProvider: (provider) => set({ currentProvider: provider }),
  
  // Tab visibility settings
  tabVisibility: {
    sdapi: true,
  },
  setTabVisibility: (visibility) => set((state) => ({
    tabVisibility: { ...state.tabVisibility, ...visibility }
  })),
}));

export default useUIStore;

