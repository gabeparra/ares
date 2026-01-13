import React, { useState, useEffect } from 'react'

function DevLoginButton({ onLogin }) {
  const [devEnabled, setDevEnabled] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [email, setEmail] = useState('admin@test.local')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState(null)
  const [loggingIn, setLoggingIn] = useState(false)

  useEffect(() => {
    // Check if dev admin is enabled
    fetch('/api/v1/auth/dev-admin/config')
      .then(res => res.json())
      .then(data => {
        setDevEnabled(data.enabled)
        setLoading(false)
      })
      .catch(() => {
        setDevEnabled(false)
        setLoading(false)
      })
  }, [])

  const handleLogin = async (e) => {
    e.preventDefault()
    setError(null)
    setLoggingIn(true)

    try {
      const response = await fetch('/api/v1/auth/dev-admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Login failed')
      }

      // Store the token and user info
      localStorage.setItem('dev_admin_token', data.token)
      localStorage.setItem('dev_admin_user', JSON.stringify(data.user))
      
      // Call the onLogin callback
      if (onLogin) {
        onLogin(data.token, data.user)
      }

      // Reload the page to apply the new auth state
      window.location.reload()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoggingIn(false)
    }
  }

  if (loading || !devEnabled) {
    return null
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowForm(!showForm)}
        className="group relative overflow-hidden px-4 py-1.5 border border-amber-500/40 rounded-lg cursor-pointer text-xs font-semibold transition-all duration-300 tracking-wide bg-gradient-to-br from-amber-500/20 to-orange-500/20 text-amber-300 shadow-[0_4px_16px_rgba(245,158,11,0.2)] hover:from-amber-500/30 hover:to-orange-500/30 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(245,158,11,0.3)] active:scale-95"
      >
        <span className="relative z-10 flex items-center gap-1.5">
          <span className="text-sm">🔧</span>
          <span>Dev Login</span>
        </span>
      </button>

      {showForm && (
        <div className="absolute top-full right-0 mt-2 w-72 p-5 bg-[rgba(26,26,31,0.98)] border border-white/15 rounded-xl shadow-[0_20px_60px_rgba(0,0,0,0.5)] backdrop-blur-xl z-50 animate-[fadeIn_0.2s_ease]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold text-sm flex items-center gap-2">
              <span className="text-amber-400">🔧</span>
              Dev Admin Login
            </h3>
            <button
              onClick={() => setShowForm(false)}
              className="w-6 h-6 rounded-md bg-white/10 text-white/60 hover:bg-white/20 hover:text-white flex items-center justify-center text-sm transition-all"
            >
              ×
            </button>
          </div>
          
          <div className="mb-3 p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <p className="text-amber-300 text-xs">
              ⚠️ Dev mode only - not for production
            </p>
          </div>

          <form onSubmit={handleLogin} className="flex flex-col gap-3">
            <div>
              <label className="block text-white/60 text-xs mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 bg-white/6 border border-white/12 rounded-lg text-white text-sm outline-none transition-all focus:border-amber-500/50 focus:bg-white/8"
              />
            </div>
            
            <div>
              <label className="block text-white/60 text-xs mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 bg-white/6 border border-white/12 rounded-lg text-white text-sm outline-none transition-all focus:border-amber-500/50 focus:bg-white/8"
              />
            </div>

            {error && (
              <div className="p-2 bg-red-500/15 border border-red-500/30 rounded-lg">
                <p className="text-red-400 text-xs">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loggingIn}
              className="w-full py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold rounded-lg transition-all duration-200 hover:from-amber-400 hover:to-orange-400 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loggingIn ? 'Logging in...' : 'Login as Dev Admin'}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

export default DevLoginButton
