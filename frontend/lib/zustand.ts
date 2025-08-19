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
  monthly_budget_usd: number
}

export interface Usage {
  total_usd: number
  month_usd: number
  monthly_budget_usd: number
  remaining_budget_usd: number
  by_agent: Record<string, number>
  by_model: Record<string, number>
}

export interface BookEstimate {
  estimated_usd: number
  total_prompt_tokens: number
  total_completion_tokens: number
  breakdown: Record<string, number>
  model: string
  chapters: number
}

export interface AppState {
  // User state
  user: User | null
  setUser: (user: User | null) => void
  isAuthenticated: boolean
  
  // Usage tracking
  usage: Usage | null
  setUsage: (usage: Usage | null) => void
  bookEstimate: BookEstimate | null
  setBookEstimate: (estimate: BookEstimate | null) => void
  
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
  
  // Usage tracking
  usage: null,
  setUsage: (usage) => set({ usage }),
  bookEstimate: null,
  setBookEstimate: (estimate) => set({ bookEstimate: estimate }),
  
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

