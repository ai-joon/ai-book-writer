import { create } from 'zustand'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

export interface User {
  id: string
  email: string
  name?: string
  picture?: string
  role: string
}

export interface AppState {
  // User state
  user: User | null
  setUser: (user: User | null) => void
  isAuthenticated: boolean
  
  // Message state
  messages: Message[]
  addMessage: (message: Message) => void
  
  // Generation state
  isGenerating: boolean
  setGenerating: (value: boolean) => void
  progress: number
  setProgress: (value: number) => void
  
  // Cost tracking
  totalCost: number
  incrementCost: (amount: number) => void
}

export const useStore = create<AppState>((set) => ({
  // User state
  user: null,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  isAuthenticated: false,
  
  // Message state
  messages: [],
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  
  // Generation state
  isGenerating: false,
  setGenerating: (value) => set({ isGenerating: value }),
  progress: 0,
  setProgress: (value) => set({ progress: value }),
  
  // Cost tracking
  totalCost: 0,
  incrementCost: (amount) => set((state) => ({ totalCost: state.totalCost + amount })),
}))

