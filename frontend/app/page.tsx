'use client'

import { useState, useEffect, useRef } from 'react'
import { useStore } from '@/lib/zustand'
import type { Message, AppState } from '@/lib/zustand'
import { BookOpen, Loader2, DollarSign, Zap } from 'lucide-react'

export default function Home() {
  const [brief, setBrief] = useState('')
  const [styleGuide, setStyleGuide] = useState('')
  const [targetChapters, setTargetChapters] = useState(10)
  const [model, setModel] = useState('gpt-5')
  const [streamedContent, setStreamedContent] = useState('')
  
  const messages = useStore((state: AppState) => state.messages)
  const addMessage = useStore((state: AppState) => state.addMessage)
  const isGenerating = useStore((state: AppState) => state.isGenerating)
  const setGenerating = useStore((state: AppState) => state.setGenerating)
  const progress = useStore((state: AppState) => state.progress)
  const setProgress = useStore((state: AppState) => state.setProgress)
  const totalCost = useStore((state: AppState) => state.totalCost)
  const incrementCost = useStore((state: AppState) => state.incrementCost)
  
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamedContent, messages])

  const startOutlineGeneration = async () => {
    if (!brief.trim() || isGenerating) return
    
    setGenerating(true)
    setProgress(0)
    setStreamedContent('')
    
    // Add user message
    addMessage({
      id: Date.now().toString(),
      role: 'user',
      content: `Generate outline for:\n${brief}`,
      timestamp: new Date(),
    })
    
    // Add assistant message placeholder
    const assistantMessageId = Date.now().toString()
    addMessage({
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    })
    
    try {
      // Get demo token (in production, use real auth)
      const tokenResponse = await fetch('/api/backend/auth/demo-token', {
        method: 'POST',
      })
      const { access_token } = await tokenResponse.json()
      
      // Create project (using demo project ID for now)
      const projectId = '00000000-0000-0000-0000-000000000000'
      
      // Start SSE connection
      const eventSource = new EventSource(
        `/api/backend/v1/projects/${projectId}/outline/stream?` +
        new URLSearchParams({
          access_token,
          brief: brief.trim(),
          style_guide: styleGuide || '',
          target_chapters: targetChapters.toString(),
          model,
        }),
        {
          withCredentials: true,
        }
      )
      
      let fullContent = ''
      
      eventSource.addEventListener('token', (event) => {
        const token = event.data
        fullContent += token
        setStreamedContent(fullContent)
      })
      
      eventSource.addEventListener('checkpoint', (event) => {
        try {
          const checkpoint = JSON.parse(event.data)
          if (checkpoint.progress) {
            setProgress(checkpoint.progress * 100)
          }
          if (checkpoint.tokens) {
            // Estimate cost (example rates)
            const estimatedCost = checkpoint.tokens * 0.000015
            incrementCost(estimatedCost)
          }
        } catch (e) {
          console.error('Error parsing checkpoint:', e)
        }
      })
      
      eventSource.addEventListener('complete', (event) => {
        try {
          const completion = JSON.parse(event.data)
          console.log('Generation complete:', completion)
        } catch (e) {
          console.error('Error parsing completion:', e)
        }
        eventSource.close()
        setGenerating(false)
        setProgress(100)
      })
      
      eventSource.addEventListener('error', (event) => {
        console.error('SSE error:', event)
        eventSource.close()
        setGenerating(false)
        
        // Add error message
        addMessage({
          id: Date.now().toString(),
          role: 'system',
          content: 'Error: Failed to generate outline. Please try again.',
          timestamp: new Date(),
        })
      })
      
      eventSource.onerror = () => {
        eventSource.close()
        setGenerating(false)
      }
      
    } catch (error) {
      console.error('Error starting generation:', error)
      setGenerating(false)
      
      addMessage({
        id: Date.now().toString(),
        role: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
      })
    }
  }

  return (
    <div className="min-h-screen bg-parchment dark:bg-indigo">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-slate bg-indigo text-snow">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-gold" />
            <h1 className="text-2xl font-serif font-bold">sopher.ai</h1>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <DollarSign className="h-4 w-4 text-gold" />
              <span className="font-mono">${totalCost.toFixed(4)}</span>
            </div>

            {isGenerating && (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-teal" />
                <span className="text-sm">{Math.round(progress)}%</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Input Panel */}
          <div className="lg:col-span-1">
            <div className="bg-snow rounded-xl shadow-[0_6px_20px_rgba(27,37,89,0.08)] p-6 space-y-4">
              <h2 className="font-serif text-xl mb-4">Book Configuration</h2>
              
              <div>
                <label className="block text-sm font-medium mb-2 text-slate">
                  Book Brief
                </label>
                <textarea
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  className="w-full h-32 px-3 py-2 border border-slate rounded-lg resize-none bg-parchment focus:ring-2 focus:ring-teal focus:border-transparent"
                  placeholder="Describe your book idea..."
                  disabled={isGenerating}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2 text-slate">
                  Style Guide (Optional)
                </label>
                <textarea
                  value={styleGuide}
                  onChange={(e) => setStyleGuide(e.target.value)}
                  className="w-full h-20 px-3 py-2 border border-slate rounded-lg resize-none bg-parchment focus:ring-2 focus:ring-teal focus:border-transparent"
                  placeholder="Writing style preferences..."
                  disabled={isGenerating}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-slate">
                  Model
                </label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full px-3 py-2 border border-slate rounded-lg bg-parchment focus:ring-2 focus:ring-teal focus:border-transparent"
                  disabled={isGenerating}
                >
                  <option value="gpt-5">GPT-5 (Default)</option>
                  <option value="claude-sonnet-4-20250514">Claude Sonnet 4</option>
                  <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-slate">
                  Target Chapters
                </label>
                <input
                  type="number"
                  value={targetChapters}
                  onChange={(e) => setTargetChapters(parseInt(e.target.value) || 10)}
                  min="1"
                  max="50"
                  className="w-full px-3 py-2 border border-slate rounded-lg bg-parchment focus:ring-2 focus:ring-teal focus:border-transparent"
                  disabled={isGenerating}
                />
              </div>

              <button
                onClick={startOutlineGeneration}
                disabled={!brief.trim() || isGenerating}
                className="w-full py-3 px-4 text-snow rounded-[14px] font-medium bg-gradient-to-r from-indigo to-teal hover:from-indigo/90 hover:to-teal/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Zap className="h-5 w-5" />
                    Generate Outline
                  </>
                )}
              </button>

              {progress > 0 && progress < 100 && (
                <div className="w-full bg-slate/20 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-indigo to-teal h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Output Panel */}
          <div className="lg:col-span-2">
            <div className="bg-snow rounded-xl shadow-[0_6px_20px_rgba(27,37,89,0.08)] p-6 h-[600px] flex flex-col">
              <h2 className="font-serif text-xl mb-4">Generated Content</h2>
              
              <div className="flex-1 overflow-y-auto space-y-4 px-2">
                {messages.map((message: Message) => (
                  <div
                    key={message.id}
                    className={`${
                      message.role === 'user'
                        ? 'ml-auto bg-teal/10 dark:bg-teal/20'
                        : message.role === 'assistant'
                        ? 'mr-auto bg-snow dark:bg-slate'
                        : 'mx-auto bg-gold/20 dark:bg-gold/30'
                    } rounded-lg p-4 max-w-[90%]`}
                  >
                    <div className="text-xs text-slate mb-1">
                      {message.role === 'user' ? 'You' : message.role === 'assistant' ? 'AI' : 'System'}
                    </div>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      {message.content || streamedContent}
                    </div>
                  </div>
                ))}

                {isGenerating && streamedContent && (
                  <div className="mr-auto bg-snow rounded-lg p-4 max-w-[90%]">
                    <div className="text-xs text-slate mb-1">AI</div>
                    <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                      {streamedContent}
                      <span className="inline-block w-2 h-4 ml-1 bg-teal animate-pulse" />
                    </div>
                  </div>
                )}
                
                <div ref={scrollRef} />
              </div>
            </div>
          </div>
        </div>
      </main>
      <footer className="bg-indigo text-snow text-center text-sm py-4">
        © 2025 sopher.ai •{' '}
        <a
          href="https://github.com/cheesejaguar/sopher.ai/blob/main/LICENSE"
          className="underline"
        >
          MIT License
        </a>{' '}
        •{' '}
        <a
          href="https://github.com/cheesejaguar/sopher.ai"
          className="underline"
        >
          GitHub Repository
        </a>
      </footer>
    </div>
  )
}