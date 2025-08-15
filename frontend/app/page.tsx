'use client'

import { useState, useEffect, useRef } from 'react'
import { useStore } from '@/lib/zustand'
import type { Message, AppState } from '@/lib/zustand'
import { BookOpen, Loader2, DollarSign, Zap } from 'lucide-react'

export default function Home() {
  const [brief, setBrief] = useState('')
  const [styleGuide, setStyleGuide] = useState('')
  const [targetChapters, setTargetChapters] = useState(10)
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
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-blue-600" />
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              sopher.ai
            </h1>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <DollarSign className="h-4 w-4 text-green-600" />
              <span className="font-mono">${totalCost.toFixed(4)}</span>
            </div>
            
            {isGenerating && (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
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
            <div className="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-6 space-y-4">
              <h2 className="text-xl font-semibold mb-4">Book Configuration</h2>
              
              <div>
                <label className="block text-sm font-medium mb-2">
                  Book Brief
                </label>
                <textarea
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  className="w-full h-32 px-3 py-2 border rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Describe your book idea..."
                  disabled={isGenerating}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">
                  Style Guide (Optional)
                </label>
                <textarea
                  value={styleGuide}
                  onChange={(e) => setStyleGuide(e.target.value)}
                  className="w-full h-20 px-3 py-2 border rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Writing style preferences..."
                  disabled={isGenerating}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">
                  Target Chapters
                </label>
                <input
                  type="number"
                  value={targetChapters}
                  onChange={(e) => setTargetChapters(parseInt(e.target.value) || 10)}
                  min="1"
                  max="50"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isGenerating}
                />
              </div>
              
              <button
                onClick={startOutlineGeneration}
                disabled={!brief.trim() || isGenerating}
                className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Output Panel */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-6 h-[600px] flex flex-col">
              <h2 className="text-xl font-semibold mb-4">Generated Content</h2>
              
              <div className="flex-1 overflow-y-auto space-y-4 px-2">
                {messages.map((message: Message) => (
                  <div
                    key={message.id}
                    className={`${
                      message.role === 'user'
                        ? 'ml-auto bg-blue-50 dark:bg-blue-900/20'
                        : message.role === 'assistant'
                        ? 'mr-auto bg-gray-50 dark:bg-gray-900/20'
                        : 'mx-auto bg-yellow-50 dark:bg-yellow-900/20'
                    } rounded-lg p-4 max-w-[90%]`}
                  >
                    <div className="text-xs text-gray-500 mb-1">
                      {message.role === 'user' ? 'You' : message.role === 'assistant' ? 'AI' : 'System'}
                    </div>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      {message.content || streamedContent}
                    </div>
                  </div>
                ))}
                
                {isGenerating && streamedContent && (
                  <div className="mr-auto bg-gray-50 dark:bg-gray-900/20 rounded-lg p-4 max-w-[90%]">
                    <div className="text-xs text-gray-500 mb-1">AI</div>
                    <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                      {streamedContent}
                      <span className="inline-block w-2 h-4 ml-1 bg-blue-600 animate-pulse" />
                    </div>
                  </div>
                )}
                
                <div ref={scrollRef} />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}