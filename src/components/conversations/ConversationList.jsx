import React, { useState, useEffect } from 'react'
import { getAuthToken } from '../../services/auth'

function ConversationList({ onSelectSession, selectedSessionId }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    setLoading(true)
    try {
      const headers = {}
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const response = await fetch('/api/v1/sessions?limit=200', { headers })
      if (response.ok) {
        const data = await response.json()
        setSessions(data.sessions || [])
      }
    } catch (err) {
      console.error('Failed to load sessions:', err)
    } finally {
      setLoading(false)
    }
  }

  const updateSession = async (sessionId, patch) => {
    try {
      const headers = { 'Content-Type': 'application/json' }
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const response = await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify(patch),
      })
      if (response.ok) {
        await loadSessions()
      }
    } catch (err) {
      console.error('Failed to update session:', err)
    }
  }

  const deleteSession = async (sessionId) => {
    const ok = window.confirm('Delete this session and all its messages?')
    if (!ok) return
    try {
      const headers = {}
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const response = await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'DELETE',
        headers,
      })
      if (response.ok) {
        await loadSessions()
      }
    } catch (err) {
      console.error('Failed to delete session:', err)
    }
  }

  const exportSession = async (sessionId, format) => {
    try {
      const headers = {}
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const response = await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}/export?format=${format}`, { headers })
      if (!response.ok) return
      const data = await response.json()
      const blob = new Blob([data.content || JSON.stringify(data, null, 2)], {
        type: format === 'md' ? 'text/markdown' : 'application/json',
      })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `${sessionId}.${format === 'md' ? 'md' : 'json'}`
      document.body.appendChild(a)
      a.click()
      a.remove()
    } catch (err) {
      console.error('Failed to export session:', err)
    }
  }

  const filteredSessions = sessions.filter(session => {
    const hay = `${session.session_id} ${session.title || ''}`.toLowerCase()
    return hay.includes(searchQuery.toLowerCase())
  })

  const formatSessionDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="flex flex-col h-full p-5 gap-4">
      {/* Header */}
      <div className="flex justify-between items-center pb-4 border-b border-white/10">
        <h3 className="m-0 text-lg font-semibold bg-gradient-to-r from-white to-red-200/90 bg-clip-text text-transparent">
          Conversation Sessions
        </h3>
        <button 
          className="w-9 h-9 rounded-lg bg-white/6 border border-white/12 cursor-pointer text-base transition-all duration-200 hover:bg-white/10 hover:border-white/20 hover:scale-105 active:scale-95 flex items-center justify-center" 
          onClick={loadSessions} 
          title="Refresh"
        >
          🔄
        </button>
      </div>

      {/* Search */}
      <div className="flex-shrink-0">
        <input
          type="text"
          placeholder="Search sessions..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-4 py-3 bg-white/6 border border-white/12 rounded-xl text-white placeholder-white/40 text-sm outline-none transition-all duration-200 focus:border-red-500/50 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(255,0,0,0.1)]"
        />
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-2">
        {loading ? (
          <div className="text-center py-12 text-white/50">Loading sessions...</div>
        ) : filteredSessions.length === 0 ? (
          <div className="empty-state">
            {searchQuery ? 'No sessions found' : 'No conversation history yet'}
          </div>
        ) : (
          filteredSessions.map((session) => {
            const sessionId = session.session_id
            const isSelected = selectedSessionId === sessionId
            return (
              <div
                key={sessionId}
                className={`group flex justify-between items-center p-4 rounded-xl cursor-pointer transition-all duration-200 ${
                  isSelected 
                    ? 'bg-gradient-to-r from-red-500/20 to-red-500/10 border border-red-500/30 shadow-[0_4px_20px_rgba(255,0,0,0.15)]' 
                    : 'bg-white/3 border border-white/8 hover:bg-white/6 hover:border-white/12 hover:translate-x-0.5'
                }`}
                onClick={() => onSelectSession && onSelectSession(sessionId)}
              >
                <div className="flex-1 min-w-0 pr-3">
                  <div className={`font-medium truncate ${isSelected ? 'text-white' : 'text-white/90'}`}>
                    {session.pinned && <span className="mr-1.5">📌</span>}
                    {session.title || (sessionId.startsWith('daily_') 
                      ? sessionId.replace('daily_', '📅 ') 
                      : sessionId.replace('session_', '').substring(0, 25))}
                  </div>
                  {session.updated_at && (
                    <div className="text-xs text-white/40 mt-1 font-mono">
                      {formatSessionDate(session.updated_at)}
                    </div>
                  )}
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                  <button
                    className="w-7 h-7 rounded-md bg-white/8 border-none cursor-pointer text-sm transition-all duration-200 hover:bg-white/15 hover:scale-110 flex items-center justify-center"
                    onClick={(e) => { e.stopPropagation(); updateSession(sessionId, { pinned: !session.pinned }) }}
                    title={session.pinned ? 'Unpin' : 'Pin'}
                  >
                    {session.pinned ? '📌' : '📍'}
                  </button>
                  <button
                    className="w-7 h-7 rounded-md bg-white/8 border-none cursor-pointer text-sm transition-all duration-200 hover:bg-white/15 hover:scale-110 flex items-center justify-center"
                    onClick={(e) => {
                      e.stopPropagation()
                      const title = window.prompt('Session title:', session.title || '')
                      if (title !== null) updateSession(sessionId, { title })
                    }}
                    title="Rename"
                  >
                    ✏️
                  </button>
                  <button 
                    className="w-7 h-7 rounded-md bg-white/8 border-none cursor-pointer text-sm transition-all duration-200 hover:bg-white/15 hover:scale-110 flex items-center justify-center" 
                    onClick={(e) => { e.stopPropagation(); exportSession(sessionId, 'md') }} 
                    title="Export Markdown"
                  >
                    ⬇️
                  </button>
                  <button 
                    className="w-7 h-7 rounded-md bg-red-500/20 border-none cursor-pointer text-sm transition-all duration-200 hover:bg-red-500/30 hover:scale-110 flex items-center justify-center" 
                    onClick={(e) => { e.stopPropagation(); deleteSession(sessionId) }} 
                    title="Delete session"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

export default ConversationList

