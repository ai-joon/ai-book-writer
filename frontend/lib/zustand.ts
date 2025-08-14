import { create } from 'zustand'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

export interface AppState {
  messages: Message[]
  addMessage: (message: Message) => void
  isGenerating: boolean
  setGenerating: (value: boolean) => void
  progress: number
  setProgress: (value: number) => void
  totalCost: number
  incrementCost: (amount: number) => void
}

export const useStore = create<AppState>((set) => ({
  messages: [],
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  isGenerating: false,
  setGenerating: (value) => set({ isGenerating: value }),
  progress: 0,
  setProgress: (value) => set({ progress: value }),
  totalCost: 0,
  incrementCost: (amount) => set((state) => ({ totalCost: state.totalCost + amount })),
}))

