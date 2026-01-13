import React, { useState, useEffect } from 'react'
import { getAuthToken } from '../../services/auth'

function ProviderSelector({ currentProvider, onProviderChange }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isExpanded, setIsExpanded] = useState(false)

  const providers = [
    {
      id: 'local',
      name: 'Ollama (Local)',
      description: 'Local Ollama instance - fast and private',
      icon: '🏠',
      available: true,
    },
    {
      id: 'openrouter',
      name: 'OpenRouter',
      description: 'Cloud-based API - works when Ollama is offline',
      icon: '☁️',
      available: true,
    },
  ]

  useEffect(() => {
    fetchCurrentProvider()
  }, [])

  const fetchCurrentProvider = async () => {
    try {
      const headers = {}
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const response = await fetch('/api/v1/settings/provider', { headers })
      if (response.ok) {
        const data = await response.json()
        if (data.provider && onProviderChange) {
          onProviderChange(data.provider)
        }
      }
    } catch (err) {
      console.error('Failed to fetch current provider:', err)
    }
  }

  const handleProviderChange = async (providerId) => {
    if (providerId === currentProvider) return

    setLoading(true)
    setError(null)

    try {
      const headers = {
        'Content-Type': 'application/json',
      }
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const response = await fetch('/api/v1/settings/provider', {
        method: 'POST',
        headers,
        body: JSON.stringify({ provider: providerId }),
      })

      const data = await response.json()

      if (response.ok) {
        if (onProviderChange) {
          onProviderChange(providerId)
        }
      } else {
        const errorMessage = data.error || data.message || `Failed to change provider (${response.status})`
        setError(errorMessage)
        console.error('Provider change failed:', {
          status: response.status,
          statusText: response.statusText,
          error: data.error,
          message: data.message,
          data: data
        })
      }
    } catch (err) {
      const errorMessage = err.message || 'Failed to change provider. Please check your configuration and network connection.'
      setError(errorMessage)
      console.error('Provider change error:', {
        error: err,
        message: err.message,
        stack: err.stack
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-5 bg-white/3 border border-white/10 rounded-2xl mb-5 transition-all duration-300 hover:bg-white/4 hover:border-white/15">
      <div className="flex justify-between items-center mb-4">
        <h3 className="m-0 text-base text-white/95 font-semibold flex items-center gap-2">
          <span className="text-xl">🔌</span>
          LLM Provider
        </h3>
        <button
          className="w-8 h-8 bg-white/6 border border-white/12 rounded-lg cursor-pointer text-white/70 transition-all duration-200 flex items-center justify-center hover:bg-white/10 hover:border-white/20 hover:text-white/90"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-label={isExpanded ? 'Collapse provider options' : 'Expand provider options'}
        >
          <span className={`text-xs transition-transform duration-200 inline-block ${isExpanded ? 'rotate-180' : ''}`}>▼</span>
        </button>
      </div>
      
      {/* Current Provider Display */}
      <div className="flex items-center gap-3 px-4 py-3 bg-white/4 border border-white/8 rounded-xl">
        <span className="text-xl">{providers.find(p => p.id === currentProvider)?.icon || '❓'}</span>
        <div className="flex-1">
          <span className="text-sm text-white/50">Current:</span>
          <span className="text-white font-medium ml-2">
            {providers.find(p => p.id === currentProvider)?.name || currentProvider || 'Not set'}
          </span>
        </div>
      </div>

      {isExpanded && (
        <>
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 mt-4 text-sm">{error}</div>
          )}

          <div className="flex flex-col gap-3 mt-4">
            {providers.map(provider => (
              <button
                key={provider.id}
                className={`group flex items-center gap-4 px-4 py-4 rounded-xl cursor-pointer transition-all duration-250 border disabled:opacity-50 disabled:cursor-not-allowed ${
                  currentProvider === provider.id 
                    ? 'bg-gradient-to-r from-red-500/20 to-red-500/10 border-red-500/40 shadow-[0_4px_20px_rgba(255,0,0,0.15)]' 
                    : 'bg-white/4 border-white/10 hover:bg-white/8 hover:border-white/18 hover:translate-x-1'
                } ${loading ? 'opacity-50' : ''}`}
                onClick={() => handleProviderChange(provider.id)}
                disabled={loading || currentProvider === provider.id || !provider.available}
              >
                <div className={`text-2xl flex-shrink-0 transition-transform duration-250 ${currentProvider !== provider.id ? 'group-hover:scale-110' : ''}`}>
                  {provider.icon}
                </div>
                <div className="flex-1 text-left">
                  <div className="text-white font-semibold text-sm">{provider.name}</div>
                  <div className="text-white/50 text-xs mt-0.5">{provider.description}</div>
                </div>
                {currentProvider === provider.id && (
                  <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center">
                    <span className="text-green-400 text-sm">✓</span>
                  </div>
                )}
              </button>
            ))}
          </div>

          {loading && (
            <div className="flex items-center gap-3 justify-center px-4 py-3 mt-4 text-sm text-white/60">
              <span className="inline-block w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
              Switching provider...
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default ProviderSelector

