'use client'

import { useState, useEffect, useRef } from 'react'
import { useStore } from '@/lib/zustand'
import type { Message, AppState, User, Usage, BookEstimate } from '@/lib/zustand'
import { BookOpen, Loader2, DollarSign, Zap, LogOut, User as UserIcon, CheckCircle, XCircle } from 'lucide-react'

// Safe redirect URLs - hardcoded constants to avoid security scan false positives
const LOGIN_COOKIE_ERROR_URL = '/login?error=cookie_failed'
const LOGIN_AUTH_ERROR_URL = '/login?error=auth_failed'

export default function Home() {
  const [brief, setBrief] = useState('')
  const [styleGuide, setStyleGuide] = useState('')
  const [targetChapters, setTargetChapters] = useState(10)
  const [model, setModel] = useState('gpt-5')
  const [streamedContent, setStreamedContent] = useState('')
  const [authStatus, setAuthStatus] = useState<'checking' | 'success' | 'failed' | null>(null)
  const [authMessage, setAuthMessage] = useState<string | null>(null)
  const [errorInfo, setErrorInfo] = useState<
    | null
    | {
        message: string
        hint?: string
        diagnostics?: { error_id?: string; request_id?: string; error_code?: string; timestamp: string }
      }
  >(null)
  
  const messages = useStore((state: AppState) => state.messages)
  const addMessage = useStore((state: AppState) => state.addMessage)
  const isGenerating = useStore((state: AppState) => state.isGenerating)
  const setGenerating = useStore((state: AppState) => state.setGenerating)
  const progress = useStore((state: AppState) => state.progress)
  const setProgress = useStore((state: AppState) => state.setProgress)
  const totalCost = useStore((state: AppState) => state.totalCost)
  const incrementCost = useStore((state: AppState) => state.incrementCost)
  const user = useStore((state: AppState) => state.user)
  const setUser = useStore((state: AppState) => state.setUser)
  const usage = useStore((state: AppState) => state.usage)
  const setUsage = useStore((state: AppState) => state.setUsage)
  const bookEstimate = useStore((state: AppState) => state.bookEstimate)
  const setBookEstimate = useStore((state: AppState) => state.setBookEstimate)
  
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Check if we're coming from OAuth callback
    const urlParams = new URLSearchParams(window.location.search)
    const fromOAuth = urlParams.get('oauth') === 'success'
    const fromOAuthError = urlParams.get('oauth') === 'error'
    const errorMessage = urlParams.get('error')
    
    // Debug logging
    if (process.env.NEXT_PUBLIC_DEBUG_AUTH === 'true') {
      console.log('[Page] OAuth status check:', {
        fromOAuth,
        fromOAuthError,
        errorMessage,
        cookies: document.cookie,
        referrer: document.referrer,
      })
    }
    
    // Handle OAuth error
    if (fromOAuthError) {
      setAuthStatus('failed')
      setAuthMessage(errorMessage || 'Authentication failed. Please try again.')
      // Clean up URL
      const newUrl = new URL(window.location.href)
      newUrl.searchParams.delete('oauth')
      newUrl.searchParams.delete('error')
      window.history.replaceState({}, '', newUrl.toString())
      return
    }
    
    // Fetch user profile and usage on mount
    const fetchUserData = async () => {
      try {
        // If coming from OAuth, show checking status and wait longer for cookies
        if (fromOAuth) {
          setAuthStatus('checking')
          setAuthMessage('Verifying authentication...')
          
          // Wait longer for cookies to fully propagate
          await new Promise(resolve => setTimeout(resolve, 500))
          
          // First verify cookies are set
          const verifyResponse = await fetch('/api/backend/auth/verify', {
            credentials: 'include',
          })
          
          if (verifyResponse.ok) {
            const verifyData = await verifyResponse.json()
            if (process.env.NEXT_PUBLIC_DEBUG_AUTH === 'true') {
              console.log('[Page] Cookie verification:', verifyData)
            }
            
            if (!verifyData.authenticated) {
              // Cookies not properly set, wait more and retry once
              await new Promise(resolve => setTimeout(resolve, 1000))
              const retryResponse = await fetch('/api/backend/auth/verify', {
                credentials: 'include',
              })
              if (retryResponse.ok) {
                const retryData = await retryResponse.json()
                if (!retryData.authenticated) {
                  setAuthStatus('failed')
                  setAuthMessage('Authentication failed. Cookies were not properly set. Please try logging in again.')
                  // Clean up URL and redirect to login
                  setTimeout(() => {
                      window.location.href = LOGIN_COOKIE_ERROR_URL
                  }, 2000)
                  return
                }
              }
            }
          }
        }
        
        // Fetch user profile
        const userResponse = await fetch('/api/backend/auth/me', {
          credentials: 'include',
        })
        
        if (userResponse.ok) {
          const userData = await userResponse.json()
          setUser(userData as User)
          
          // Show success message if coming from OAuth
          if (fromOAuth) {
            setAuthStatus('success')
            setAuthMessage(`Welcome back, ${userData.name || userData.email}!`)
            // Clean up URL after successful auth
            const newUrl = new URL(window.location.href)
            newUrl.searchParams.delete('oauth')
            window.history.replaceState({}, '', newUrl.toString())
            // Clear success message after 3 seconds
            setTimeout(() => {
              setAuthStatus(null)
              setAuthMessage(null)
            }, 3000)
          }
        } else if (userResponse.status === 401) {
          // Not authenticated
          if (fromOAuth) {
            setAuthStatus('failed')
            setAuthMessage('Authentication failed. Please try again.')
            setTimeout(() => {
              window.location.href = LOGIN_AUTH_ERROR_URL
            }, 2000)
          }
        }
        
        // Fetch usage data
        const usageResponse = await fetch('/api/backend/v1/users/me/usage', {
          credentials: 'include',
        })
        if (usageResponse.ok) {
          const usageData = await usageResponse.json()
          setUsage(usageData as Usage)
        }
      } catch (error) {
        console.error('Failed to fetch user data:', error)
        if (fromOAuth) {
          setAuthStatus('failed')
          setAuthMessage('Failed to verify authentication. Please try again.')
        }
      }
    }
    fetchUserData()
  }, [setUser, setUsage])
  
  // Fetch cost estimate when parameters change
  useEffect(() => {
    const fetchEstimate = async () => {
      if (!model || targetChapters < 1) return
      
      try {
        const response = await fetch('/api/backend/v1/users/me/estimate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({
            model,
            target_chapters: targetChapters,
            avg_prompt_tokens: 2000,
            avg_completion_tokens: 4000,
          }),
        })
        
        if (response.ok) {
          const estimate = await response.json()
          setBookEstimate(estimate as BookEstimate)
        }
      } catch (error) {
        console.error('Failed to fetch estimate:', error)
      }
    }
    
    fetchEstimate()
  }, [model, targetChapters, setBookEstimate])

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamedContent, messages])

  const handleLogout = async () => {
    await fetch('/api/backend/auth/logout', {
      method: 'POST',
      credentials: 'include',
    })
    window.location.href = '/login'
  }

  const startOutlineGeneration = async () => {
    if (!brief.trim() || isGenerating) return
    
    setGenerating(true)
    setProgress(0)
    setStreamedContent('')
    setErrorInfo(null)
    
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
      // Create project (using demo project ID for now)
      const projectId = '00000000-0000-0000-0000-000000000000'
      
      // Start SSE connection (cookies will be included automatically)
      const eventSource = new EventSource(
        `/api/backend/v1/projects/${projectId}/outline/stream?` +
        new URLSearchParams({
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

        if (event instanceof MessageEvent && event.data) {
          try {
            const err = JSON.parse(event.data)
            setErrorInfo({
              message: err.message,
              hint: err.hint,
              diagnostics: {
                error_id: err.error_id,
                request_id: err.request_id,
                error_code: err.error_code,
                timestamp: err.timestamp,
              },
            })
            addMessage({
              id: Date.now().toString(),
              role: 'system',
              content: `Error: ${err.message}${err.hint ? ` Hint: ${err.hint}` : ''}`,
              timestamp: new Date(),
            })
            return
          } catch (e) {
            console.error('Error parsing server error:', e)
          }
        }

        const ts = new Date().toISOString()
        setErrorInfo({
          message: 'Connection issue: outline stream',
          hint: 'Possible CORS, network, or server issue. Retry in a few seconds.',
          diagnostics: { timestamp: ts, error_code: 'CONNECTION_ERROR' },
        })
        addMessage({
          id: Date.now().toString(),
          role: 'system',
          content: 'Connection issue: outline stream. Please retry.',
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
      const ts = new Date().toISOString()
      setErrorInfo({
        message: 'Connection issue: outline stream',
        hint: 'Possible CORS, network, or server issue. Retry in a few seconds.',
        diagnostics: { timestamp: ts, error_code: 'CONNECTION_ERROR' },
      })
      addMessage({
        id: Date.now().toString(),
        role: 'system',
        content: 'Connection issue: outline stream. Please retry.',
        timestamp: new Date(),
      })
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-parchment dark:bg-indigo">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-slate bg-indigo text-snow">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-gold" />
            <h1 className="text-2xl font-serif font-bold">sopher.ai</h1>
          </div>

          <div className="flex items-center gap-4">
            {usage && (
              <div className="flex items-center gap-3 text-sm">
                <div className="flex items-center gap-1">
                  <DollarSign className="h-4 w-4 text-gold" />
                  <span className="font-mono">
                    ${usage.month_usd.toFixed(2)} / ${usage.monthly_budget_usd.toFixed(0)}
                  </span>
                </div>
                <div className="h-4 w-1 bg-gold/30" />
                <span className="text-xs text-snow/80">
                  ${usage.remaining_budget_usd.toFixed(2)} left
                </span>
              </div>
            )}

            {isGenerating && (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-teal" />
                <span className="text-sm">{Math.round(progress)}%</span>
              </div>
            )}

            {user && (
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-2 text-sm">
                  {user.picture ? (
                    <img
                      src={user.picture}
                      alt={user.name || user.email}
                      className="h-8 w-8 rounded-full border border-gold"
                    />
                  ) : (
                    <UserIcon className="h-5 w-5 text-gold" />
                  )}
                  <span className="hidden sm:inline">{user.name || user.email}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 hover:bg-indigo-700 rounded-lg transition-colors"
                  title="Logout"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto flex-1 px-4 py-8">
        {/* Authentication Status Messages */}
        {authStatus && (
          <div className={`mb-4 border p-4 rounded-lg flex items-center gap-3 ${
            authStatus === 'checking' ? 'border-blue-200 bg-blue-50 text-blue-800' :
            authStatus === 'success' ? 'border-green-200 bg-green-50 text-green-800' :
            'border-red-200 bg-red-50 text-red-800'
          }`}>
            {authStatus === 'checking' && <Loader2 className="h-5 w-5 animate-spin" />}
            {authStatus === 'success' && <CheckCircle className="h-5 w-5" />}
            {authStatus === 'failed' && <XCircle className="h-5 w-5" />}
            <span className="font-medium">{authMessage}</span>
          </div>
        )}
        
        {errorInfo && (
          <div className="mb-4 border border-red-200 bg-red-50 text-red-800 p-4 rounded">
            <p className="font-semibold">{errorInfo.message}</p>
            {errorInfo.hint && <p className="text-sm mt-1">{errorInfo.hint}</p>}
            {errorInfo.diagnostics && (
              <button
                className="mt-2 text-sm underline"
                onClick={() =>
                  navigator.clipboard.writeText(
                    JSON.stringify(errorInfo.diagnostics)
                  )
                }
              >
                Copy diagnostics
              </button>
            )}
          </div>
        )}
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
              
              {bookEstimate && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-amber-900">Estimated Cost</span>
                    <span className="text-lg font-bold text-amber-900">
                      ${bookEstimate.estimated_usd.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-xs text-amber-700 space-y-1">
                    <div>Chapters: ${bookEstimate.breakdown.chapters?.toFixed(2) || '0.00'}</div>
                    <div>Outline: ${bookEstimate.breakdown.outline?.toFixed(2) || '0.00'}</div>
                    <div>Editing: ${bookEstimate.breakdown.editing?.toFixed(2) || '0.00'}</div>
                  </div>
                </div>
              )}
              
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