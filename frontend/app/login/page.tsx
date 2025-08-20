'use client'

import { BookOpen } from 'lucide-react'

export default function LoginPage() {

  const handleGoogleLogin = () => {
    // Use relative URL to go through frontend proxy
    // This ensures cookies are set on the correct domain
    window.location.href = '/api/backend/auth/login/google'
  }

  return (
    <div 
      className="min-h-screen flex items-center justify-center px-4"
      style={{
        backgroundImage: 'url(/login-pattern-geometric.svg)',
        backgroundRepeat: 'repeat',
        backgroundSize: '60px 60px',
        backgroundColor: '#f8fafc'
      }}
    >
      <div className="max-w-md w-full">
        <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-2xl p-8 border border-gray-200">
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              <BookOpen className="h-12 w-12 text-indigo-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">sopher.ai</h1>
            <p className="text-gray-600">AI-Powered Book Writing System</p>
          </div>

          <div className="space-y-4">
            <button
              onClick={handleGoogleLogin}
              className="w-full bg-white hover:bg-gray-100 text-gray-800 font-semibold py-3 px-4 rounded-lg shadow-lg transition-all duration-200 flex items-center justify-center space-x-3"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              <span>Sign in with Google</span>
            </button>
          </div>

          <div className="mt-6 text-center">
            <p className="text-gray-500 text-sm">
              By signing in, you agree to our Terms of Service and Privacy Policy.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}