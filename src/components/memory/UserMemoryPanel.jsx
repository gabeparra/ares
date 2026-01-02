import React, { useState, useEffect, useCallback } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { apiGet, apiPost, apiDelete } from '../../services/api'
import './UserMemoryPanel.css'

const FACT_TYPES = [
  { id: 'identity', label: 'Identity', icon: '👤', description: 'Name, age, location' },
  { id: 'professional', label: 'Professional', icon: '💼', description: 'Job, company, skills' },
  { id: 'personal', label: 'Personal', icon: '🎯', description: 'Hobbies, interests' },
  { id: 'context', label: 'Context', icon: '📍', description: 'Current projects, situations' },
]

function UserMemoryPanel() {
  const { user, isAuthenticated } = useAuth0()
  const [facts, setFacts] = useState([])
  const [preferences, setPreferences] = useState([])
  const [memorySpots, setMemorySpots] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [userId, setUserId] = useState('')
  const [selectedType, setSelectedType] = useState(null)
  const [showAddFact, setShowAddFact] = useState(false)
  const [showAddPref, setShowAddPref] = useState(false)
  const [stats, setStats] = useState(null)
  const [spotStatusFilter, setSpotStatusFilter] = useState('')
  const [spotTypeFilter, setSpotTypeFilter] = useState('')
  const [loadingSpots, setLoadingSpots] = useState(false)
  const [extractingSpots, setExtractingSpots] = useState(false)
  
  const [factForm, setFactForm] = useState({
    type: 'identity',
    key: '',
    value: '',
  })
  
  const [prefForm, setPrefForm] = useState({
    key: '',
    value: '',
  })
  
  const [submitting, setSubmitting] = useState(false)

  // Set user ID from Auth0 when authenticated
  useEffect(() => {
    if (isAuthenticated && user?.sub) {
      setUserId(user.sub)
    } else if (!isAuthenticated) {
      setUserId('default')
    }
  }, [isAuthenticated, user])

  const loadMemory = useCallback(async () => {
    if (!userId) {
      setLoading(false)
      return
    }
    
    try {
      setLoading(true)
      setError(null)
      
      let url = `/api/v1/user-memory?user_id=${encodeURIComponent(userId)}`
      if (selectedType) {
        url += `&type=${selectedType}`
      }
      
      const response = await apiGet(url)
      if (!response.ok) {
        throw new Error('Failed to load user memory')
      }
      
      const data = await response.json()
      setFacts(data.facts || [])
      setPreferences(data.preferences || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [userId, selectedType])

  const loadStats = useCallback(async () => {
    try {
      const response = await apiGet('/api/v1/memory/stats')
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }, [])

  const loadMemorySpots = useCallback(async () => {
    try {
      setLoadingSpots(true)
      setError(null)
      let url = `/api/v1/memory/spots?limit=100`
      if (userId) {
        url += `&user_id=${encodeURIComponent(userId)}`
      }
      if (spotStatusFilter) {
        url += `&status=${spotStatusFilter}`
      }
      if (spotTypeFilter) {
        url += `&memory_type=${spotTypeFilter}`
      }
      
      console.log('Loading memory spots from:', url)
      const response = await apiGet(url)
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Failed to load memory spots:', response.status, errorText)
        throw new Error(`Failed to load memory spots: ${response.status}`)
      }
      
      const data = await response.json()
      console.log('Memory spots loaded:', data.count, 'spots')
      setMemorySpots(data.memory_spots || [])
    } catch (err) {
      console.error('Failed to load memory spots:', err)
      setError(`Failed to load memory spots: ${err.message}`)
    } finally {
      setLoadingSpots(false)
    }
  }, [userId, spotStatusFilter, spotTypeFilter])

  useEffect(() => {
    loadMemory()
    loadStats()
    loadMemorySpots()
  }, [loadMemory, loadStats, loadMemorySpots])

  const handleAddFact = async (e) => {
    e.preventDefault()
    
    if (!factForm.key.trim() || !factForm.value.trim()) {
      return
    }
    
    try {
      setSubmitting(true)
      
      const response = await apiPost('/api/v1/user-memory/fact', {
        user_id: userId,
        type: factForm.type,
        key: factForm.key,
        value: factForm.value,
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to add fact')
      }
      
      setShowAddFact(false)
      setFactForm({ type: 'identity', key: '', value: '' })
      loadMemory()
      loadStats()
      loadMemorySpots()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleAddPreference = async (e) => {
    e.preventDefault()
    
    if (!prefForm.key.trim() || !prefForm.value.trim()) {
      return
    }
    
    try {
      setSubmitting(true)
      
      const response = await apiPost('/api/v1/user-memory/preference', {
        user_id: userId,
        key: prefForm.key,
        value: prefForm.value,
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to add preference')
      }
      
      setShowAddPref(false)
      setPrefForm({ key: '', value: '' })
      loadMemory()
      loadStats()
      loadMemorySpots()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteFact = async (factId) => {
    if (!factId) {
      setError('Invalid fact ID')
      return
    }
    
    if (!window.confirm('Delete this fact?')) {
      return
    }
    
    try {
      const response = await apiDelete(`/api/v1/user-memory/fact/${factId}`)
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || `Failed to delete fact (${response.status})`)
      }
      loadMemory()
      loadStats()
      loadMemorySpots()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDeletePreference = async (prefId) => {
    if (!prefId) {
      setError('Invalid preference ID')
      return
    }
    
    if (!window.confirm('Delete this preference?')) {
      return
    }
    
    try {
      const response = await apiDelete(`/api/v1/user-memory/preference/${prefId}`)
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || `Failed to delete preference (${response.status})`)
      }
      loadMemory()
      loadStats()
      loadMemorySpots()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleApplySpot = async (spotId) => {
    try {
      const response = await apiPost(`/api/v1/memory/spots/${spotId}/apply`, {})
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to apply memory spot')
      }
      loadMemorySpots()
      loadMemory()
      loadStats()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleRejectSpot = async (spotId) => {
    if (!window.confirm('Reject this memory spot?')) {
      return
    }
    
    try {
      const response = await apiPost(`/api/v1/memory/spots/${spotId}/reject`, {})
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to reject memory spot')
      }
      loadMemorySpots()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleExtractMemories = async () => {
    if (!window.confirm('Extract memories from all conversations? This may take a while.')) {
      return
    }
    
    try {
      setExtractingSpots(true)
      setError(null)
      
      const response = await apiPost('/api/v1/memory/extract-all', {
        user_id: userId,
        limit: 10,
        min_messages: 2,
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to extract memories')
      }
      
      const data = await response.json()
      alert(`Extracted ${data.total_extracted || 0} memory spots from ${data.processed_sessions || 0} sessions.`)
      
      // Reload spots after extraction
      loadMemorySpots()
    } catch (err) {
      setError(err.message)
    } finally {
      setExtractingSpots(false)
    }
  }

  // Group facts by type
  const groupedFacts = facts.reduce((acc, fact) => {
    if (!acc[fact.fact_type]) {
      acc[fact.fact_type] = []
    }
    acc[fact.fact_type].push(fact)
    return acc
  }, {})

  const getTypeInfo = (typeId) => {
    return FACT_TYPES.find(t => t.id === typeId) || { label: typeId, icon: '📝' }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
    })
  }

  const formatDateTime = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getMemoryTypeLabel = (type) => {
    const labels = {
      'user_fact': 'User Fact',
      'user_preference': 'User Preference',
      'ai_self_memory': 'AI Self Memory',
      'capability': 'Capability',
      'general': 'General',
    }
    return labels[type] || type
  }

  const getMemoryTypeIcon = (type) => {
    const icons = {
      'user_fact': '👤',
      'user_preference': '⭐',
      'ai_self_memory': '🤖',
      'capability': '💪',
      'general': '📝',
    }
    return icons[type] || '📝'
  }

  const getStatusColor = (status) => {
    const colors = {
      'extracted': '#3b82f6',
      'reviewed': '#8b5cf6',
      'applied': '#10b981',
      'rejected': '#ef4444',
    }
    return colors[status] || '#71717a'
  }

  return (
    <div className="panel user-memory-panel">
      <div className="memory-header">
        <div className="memory-title">
          <h2>User Memory</h2>
          <span className="memory-count">
            {facts.length} facts, {preferences.length} preferences
          </span>
        </div>
        <div className="memory-actions">
          <div className="user-selector">
            <label>User ID:</label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder={isAuthenticated && user?.sub ? user.sub : "default"}
              title={isAuthenticated && user?.sub && userId === user.sub ? "Your authenticated user ID" : "Change user ID to view another user's memory (admin only)"}
            />
            {isAuthenticated && user?.sub && userId === user.sub && (
              <span className="user-id-badge" title="Authenticated user">✓</span>
            )}
          </div>
          <button 
            className="add-button"
            onClick={() => setShowAddFact(!showAddFact)}
          >
            {showAddFact ? 'Cancel' : '+ Fact'}
          </button>
          <button 
            className="add-button pref-button"
            onClick={() => setShowAddPref(!showAddPref)}
          >
            {showAddPref ? 'Cancel' : '+ Preference'}
          </button>
        </div>
      </div>

      {error && (
        <div className="memory-error">
          {error}
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {stats && (
        <div className="memory-stats">
          <div className="stat-item">
            <span className="stat-value">{stats.self_memory?.total || 0}</span>
            <span className="stat-label">AI Memories</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.user_facts?.total || 0}</span>
            <span className="stat-label">User Facts</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.user_preferences?.total || 0}</span>
            <span className="stat-label">Preferences</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.unique_users || 0}</span>
            <span className="stat-label">Users</span>
          </div>
        </div>
      )}

      <div className="type-filter">
        <button
          className={`type-chip ${selectedType === null ? 'active' : ''}`}
          onClick={() => setSelectedType(null)}
        >
          All Facts
        </button>
        {FACT_TYPES.map(type => (
          <button
            key={type.id}
            className={`type-chip ${selectedType === type.id ? 'active' : ''}`}
            onClick={() => setSelectedType(type.id)}
          >
            {type.icon} {type.label}
          </button>
        ))}
      </div>

      {showAddFact && (
        <form className="add-form" onSubmit={handleAddFact}>
          <div className="form-row">
            <select
              value={factForm.type}
              onChange={(e) => setFactForm({ ...factForm, type: e.target.value })}
            >
              {FACT_TYPES.map(type => (
                <option key={type.id} value={type.id}>
                  {type.icon} {type.label}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Key (e.g., name, job)"
              value={factForm.key}
              onChange={(e) => setFactForm({ ...factForm, key: e.target.value })}
              required
            />
          </div>
          <div className="form-row">
            <input
              type="text"
              placeholder="Value"
              value={factForm.value}
              onChange={(e) => setFactForm({ ...factForm, value: e.target.value })}
              required
            />
            <button type="submit" disabled={submitting}>
              {submitting ? 'Adding...' : 'Add Fact'}
            </button>
          </div>
        </form>
      )}

      {showAddPref && (
        <form className="add-form pref-form" onSubmit={handleAddPreference}>
          <div className="form-row">
            <input
              type="text"
              placeholder="Preference key (e.g., communication_style)"
              value={prefForm.key}
              onChange={(e) => setPrefForm({ ...prefForm, key: e.target.value })}
              required
            />
          </div>
          <div className="form-row">
            <input
              type="text"
              placeholder="Value (e.g., technical, casual)"
              value={prefForm.value}
              onChange={(e) => setPrefForm({ ...prefForm, value: e.target.value })}
              required
            />
            <button type="submit" disabled={submitting}>
              {submitting ? 'Adding...' : 'Add Preference'}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="memory-loading">Loading user memory...</div>
      ) : (
        <div className="memory-content">
          {/* Facts Section */}
          <div className="memory-section">
            <h3>Facts</h3>
            {facts.length === 0 ? (
              <div className="memory-empty">No facts stored for this user.</div>
            ) : (
              <div className="facts-container">
                {selectedType ? (
                  <div className="fact-group">
                    <div className="group-header">
                      <span className="group-icon">{getTypeInfo(selectedType).icon}</span>
                      <span className="group-label">{getTypeInfo(selectedType).label}</span>
                    </div>
                    <div className="fact-list">
                      {(groupedFacts[selectedType] || []).map(fact => (
                        <FactCard
                          key={fact.id}
                          fact={fact}
                          onDelete={handleDeleteFact}
                          formatDate={formatDate}
                        />
                      ))}
                    </div>
                  </div>
                ) : (
                  FACT_TYPES.map(type => {
                    const typeFacts = groupedFacts[type.id] || []
                    if (typeFacts.length === 0) return null
                    
                    return (
                      <div key={type.id} className="fact-group">
                        <div className="group-header">
                          <span className="group-icon">{type.icon}</span>
                          <span className="group-label">{type.label}</span>
                          <span className="group-count">{typeFacts.length}</span>
                        </div>
                        <div className="fact-list">
                          {typeFacts.map(fact => (
                            <FactCard
                              key={fact.id}
                              fact={fact}
                              onDelete={handleDeleteFact}
                              formatDate={formatDate}
                            />
                          ))}
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            )}
          </div>

          {/* Preferences Section */}
          <div className="memory-section">
            <h3>Preferences</h3>
            {preferences.length === 0 ? (
              <div className="memory-empty">No preferences stored for this user.</div>
            ) : (
              <div className="pref-list">
                {preferences.map(pref => (
                  <div key={pref.id} className="pref-card">
                    <div className="pref-header">
                      <span className="pref-key">{pref.preference_key}</span>
                      <button 
                        className="pref-delete"
                        onClick={() => handleDeletePreference(pref.id)}
                        title="Delete preference"
                      >
                        ×
                      </button>
                    </div>
                    <div className="pref-value">{pref.preference_value}</div>
                    <div className="pref-date">{formatDate(pref.updated_at)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Memory Spots Section */}
          <div className="memory-section">
            <div className="memory-section-header">
              <h3>Extracted Memory Spots</h3>
              <div className="spot-header-actions">
                <button
                  className="extract-memories-button"
                  onClick={handleExtractMemories}
                  disabled={extractingSpots}
                  title="Extract memories from conversations"
                >
                  {extractingSpots ? 'Extracting...' : '🔍 Extract Memories'}
                </button>
                <div className="spot-filters">
                  <select
                    value={spotStatusFilter}
                    onChange={(e) => setSpotStatusFilter(e.target.value)}
                    className="spot-filter-select"
                  >
                    <option value="">All Statuses</option>
                    <option value="extracted">Extracted</option>
                    <option value="reviewed">Reviewed</option>
                    <option value="applied">Applied</option>
                    <option value="rejected">Rejected</option>
                  </select>
                  <select
                    value={spotTypeFilter}
                    onChange={(e) => setSpotTypeFilter(e.target.value)}
                    className="spot-filter-select"
                  >
                    <option value="">All Types</option>
                    <option value="user_fact">User Fact</option>
                    <option value="user_preference">User Preference</option>
                    <option value="ai_self_memory">AI Self Memory</option>
                    <option value="capability">Capability</option>
                    <option value="general">General</option>
                  </select>
                </div>
              </div>
            </div>
            {loadingSpots ? (
              <div className="memory-empty">Loading memory spots...</div>
            ) : memorySpots.length === 0 ? (
              <div className="memory-empty">
                <div>No memory spots found.</div>
                <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted, #71717a)' }}>
                  {spotStatusFilter || spotTypeFilter 
                    ? 'Try adjusting the filters or click "Extract Memories" to extract from conversations.'
                    : 'Click "Extract Memories" to extract memories from your conversations.'}
                </div>
              </div>
            ) : (
              <div className="memory-spots-list">
                {memorySpots.map(spot => (
                  <MemorySpotCard
                    key={spot.id}
                    spot={spot}
                    onApply={handleApplySpot}
                    onReject={handleRejectSpot}
                    formatDateTime={formatDateTime}
                    getMemoryTypeLabel={getMemoryTypeLabel}
                    getMemoryTypeIcon={getMemoryTypeIcon}
                    getStatusColor={getStatusColor}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function FactCard({ fact, onDelete, formatDate }) {
  return (
    <div className="fact-card">
      <div className="fact-header">
        <span className="fact-key">{fact.fact_key}</span>
        <span className="fact-source" title={`Source: ${fact.source}`}>
          {fact.source === 'conversation' ? '💬' : fact.source === 'telegram' ? '📱' : '🔧'}
        </span>
      </div>
      <div className="fact-value">{fact.fact_value}</div>
      <div className="fact-footer">
        <span className="fact-date">{formatDate(fact.updated_at)}</span>
        <button 
          className="fact-delete"
          onClick={() => onDelete(fact.id)}
          title="Delete fact"
        >
          ×
        </button>
      </div>
    </div>
  )
}

function MemorySpotCard({ spot, onApply, onReject, formatDateTime, getMemoryTypeLabel, getMemoryTypeIcon, getStatusColor }) {
  const metadata = spot.metadata || {}
  
  return (
    <div className="memory-spot-card" style={{ borderLeftColor: getStatusColor(spot.status) }}>
      <div className="spot-header">
        <div className="spot-type-badge">
          <span className="spot-type-icon">{getMemoryTypeIcon(spot.memory_type)}</span>
          <span className="spot-type-label">{getMemoryTypeLabel(spot.memory_type)}</span>
        </div>
        <div className="spot-status-badge" style={{ backgroundColor: getStatusColor(spot.status) + '20', color: getStatusColor(spot.status) }}>
          {spot.status}
        </div>
      </div>
      
      <div className="spot-content">
        {spot.content}
      </div>
      
      {(metadata.key || metadata.value) && (
        <div className="spot-metadata">
          {metadata.key && <span className="spot-meta-key">{metadata.key}:</span>}
          {metadata.value && <span className="spot-meta-value">{metadata.value}</span>}
        </div>
      )}
      
      <div className="spot-metrics">
        <div className="spot-metric">
          <span className="metric-label">Confidence:</span>
          <span className="metric-value" style={{ color: spot.confidence >= 0.8 ? '#10b981' : spot.confidence >= 0.6 ? '#f59e0b' : '#ef4444' }}>
            {(spot.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <div className="spot-metric">
          <span className="metric-label">Importance:</span>
          <span className="metric-value">{spot.importance}/10</span>
        </div>
      </div>
      
      {spot.source_conversation && (
        <div className="spot-source">
          <div className="spot-source-label">Source:</div>
          <div className="spot-source-text">{spot.source_conversation.substring(0, 200)}{spot.source_conversation.length > 200 ? '...' : ''}</div>
        </div>
      )}
      
      <div className="spot-footer">
        <div className="spot-dates">
          <span className="spot-date">Extracted: {formatDateTime(spot.extracted_at)}</span>
          {spot.applied_at && <span className="spot-date">Applied: {formatDateTime(spot.applied_at)}</span>}
          {spot.reviewed_at && !spot.applied_at && <span className="spot-date">Reviewed: {formatDateTime(spot.reviewed_at)}</span>}
        </div>
        <div className="spot-actions">
          {spot.status === 'extracted' && (
            <>
              <button
                className="spot-action-button spot-apply"
                onClick={() => onApply(spot.id)}
                title="Apply this memory spot"
              >
                ✓ Apply
              </button>
              <button
                className="spot-action-button spot-reject"
                onClick={() => onReject(spot.id)}
                title="Reject this memory spot"
              >
                × Reject
              </button>
            </>
          )}
          {spot.status === 'applied' && (
            <span className="spot-applied-badge">✓ Applied</span>
          )}
          {spot.status === 'rejected' && (
            <span className="spot-rejected-badge">× Rejected</span>
          )}
        </div>
      </div>
    </div>
  )
}

export default UserMemoryPanel

