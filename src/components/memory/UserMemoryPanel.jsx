import React, { useState, useEffect, useCallback } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { apiGet, apiPost, apiDelete } from '../../services/api'

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
  const [showingDefaultUser, setShowingDefaultUser] = useState(false)
  const [linkedUserIds, setLinkedUserIds] = useState([])
  const [showAddFact, setShowAddFact] = useState(false)
  const [showAddPref, setShowAddPref] = useState(false)
  const [stats, setStats] = useState(null)
  const [spotStatusFilter, setSpotStatusFilter] = useState('')
  const [spotTypeFilter, setSpotTypeFilter] = useState('')
  const [loadingSpots, setLoadingSpots] = useState(false)
  const [extractingSpots, setExtractingSpots] = useState(false)
  const [revisingMemories, setRevisingMemories] = useState(false)
  const [orchestratorStatus, setOrchestratorStatus] = useState(null)
  const [showOrchestrator, setShowOrchestrator] = useState(false)
  const [activeMainTab, setActiveMainTab] = useState('user-memory') // 'user-memory' or 'extracted-spots'
  const [activeMemoryTab, setActiveMemoryTab] = useState('to-review') // 'to-review', 'accepted', or 'rejected'
  
  // Auto-refresh memory spots when switching to extracted-spots tab
  useEffect(() => {
    if (activeMainTab === 'extracted-spots' && userId) {
      loadMemorySpots()
    }
    // Clear error when switching tabs
    if (activeMainTab !== 'extracted-spots') {
      setError(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeMainTab])
  
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
      setFacts([])
      setPreferences([])
      return
    }
    
    try {
      setLoading(true)
      setError(null)
      
      // Get all user IDs to query (current user + linked accounts)
      const userIdsToQuery = linkedUserIds.length > 0 ? linkedUserIds : [userId]
      
      // Aggregate memories from all linked accounts
      let allFacts = []
      let allPreferences = []
      
      for (const uid of userIdsToQuery) {
        let url = `/api/v1/user-memory?user_id=${encodeURIComponent(uid)}`
        if (selectedType) {
          url += `&type=${selectedType}`
        }
        
        const response = await apiGet(url)
        
        if (response.ok) {
          const data = await response.json()
          // Add user_id to each fact/preference so we know which account it came from
          const facts = (data.facts || []).map(f => ({ ...f, source_user_id: uid }))
          const prefs = (data.preferences || []).map(p => ({ ...p, source_user_id: uid }))
          allFacts.push(...facts)
          allPreferences.push(...prefs)
        }
      }
      
      // If no data found and we haven't tried default yet, try default as fallback
      if (allFacts.length === 0 && allPreferences.length === 0 && userId !== 'default' && !userIdsToQuery.includes('default')) {
        const defaultResponse = await apiGet(`/api/v1/user-memory?user_id=default${selectedType ? `&type=${selectedType}` : ''}`)
        if (defaultResponse.ok) {
          const defaultData = await defaultResponse.json()
          if ((defaultData.facts?.length || 0) > 0 || (defaultData.preferences?.length || 0) > 0) {
            allFacts = (defaultData.facts || []).map(f => ({ ...f, source_user_id: 'default' }))
            allPreferences = (defaultData.preferences || []).map(p => ({ ...p, source_user_id: 'default' }))
            setShowingDefaultUser(true)
          }
        }
      } else {
        setShowingDefaultUser(false)
      }
      
      setFacts(allFacts)
      setPreferences(allPreferences)
    } catch (err) {
      console.error('Error loading memory:', err)
      setError(err.message || 'Failed to load user memory')
      setFacts([])
      setPreferences([])
    } finally {
      setLoading(false)
    }
  }, [userId, selectedType, linkedUserIds])

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
    // Don't load if userId is not set (wait for Auth0 to initialize)
    if (!userId) {
      setMemorySpots([])
      setLoadingSpots(false)
      return
    }
    
    try {
      setLoadingSpots(true)
      // Don't set error to null here - preserve other errors
      
      // Get all user IDs to query (current user + linked accounts)
      const userIdsToQuery = linkedUserIds.length > 0 ? linkedUserIds : [userId]
      
      // Aggregate memory spots from all linked accounts
      let allSpots = []
      
      for (const uid of userIdsToQuery) {
        let url = `/api/v1/memory/spots?limit=200&user_id=${encodeURIComponent(uid)}`
        
        const response = await apiGet(url)
        if (response.ok) {
          const data = await response.json()
          // Add source_user_id to each spot so we know which account it came from
          const spots = (data.memory_spots || []).map(s => ({ ...s, source_user_id: uid }))
          allSpots.push(...spots)
        }
      }
      
      // If no spots found and we haven't tried default yet, try default as fallback
      if (allSpots.length === 0 && userId !== 'default' && !userIdsToQuery.includes('default')) {
        const defaultResponse = await apiGet(`/api/v1/memory/spots?limit=200&user_id=default`)
        if (defaultResponse.ok) {
          const defaultData = await defaultResponse.json()
          if ((defaultData.memory_spots?.length || 0) > 0) {
            allSpots = (defaultData.memory_spots || []).map(s => ({ ...s, source_user_id: 'default' }))
          }
        }
      }
      
      // Sort by extracted_at descending (most recent first)
      allSpots.sort((a, b) => {
        const dateA = new Date(a.extracted_at || 0)
        const dateB = new Date(b.extracted_at || 0)
        return dateB - dateA
      })
      
      // Limit to 200 total
      allSpots = allSpots.slice(0, 200)
      
      setMemorySpots(allSpots)
    } catch (err) {
      console.error('Failed to load memory spots:', err)
      // Only set error if we're on the extracted-spots tab
      if (activeMainTab === 'extracted-spots') {
        setError(`Failed to load memory spots: ${err.message}`)
      }
      setMemorySpots([])
    } finally {
      setLoadingSpots(false)
    }
  }, [userId, activeMainTab, linkedUserIds])

  const loadOrchestratorStatus = useCallback(async () => {
    try {
      const response = await apiGet('/api/v1/debug/status')
      if (response.ok) {
        const data = await response.json()
        setOrchestratorStatus(data)
      }
    } catch (err) {
      console.error('Failed to load orchestrator status:', err)
    }
  }, [])

  const loadLinkedAccounts = useCallback(async () => {
    if (!userId || userId === 'default') {
      setLinkedUserIds([])
      return
    }
    
    try {
      const response = await apiGet(`/api/v1/account-links/linked?user_id=${encodeURIComponent(userId)}`)
      if (response.ok) {
        const data = await response.json()
        // Get all linked user IDs (the API returns linked_user_ids which includes the current user)
        const linkedIds = data.linked_user_ids || [userId]
        setLinkedUserIds(linkedIds)
      } else {
        setLinkedUserIds([userId]) // Fallback to just current user
      }
    } catch (err) {
      console.error('Failed to load linked accounts:', err)
      setLinkedUserIds([userId]) // Fallback to just current user
    }
  }, [userId])

  useEffect(() => {
    // Only load data if userId is set (wait for Auth0 to initialize)
    // This prevents loading with empty userId and then reloading when userId is set
    if (!userId) {
      return
    }
    
    // Load linked accounts first, then load memory (which will use linked accounts)
    loadLinkedAccounts()
    loadMemory()
    loadStats()
    loadMemorySpots()
    loadOrchestratorStatus()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, selectedType])

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
      // Reload data to show the new fact
      await Promise.all([
        loadMemory(),
        loadStats(),
        loadMemorySpots()
      ])
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
      // Reload data to show the new preference
      await Promise.all([
        loadMemory(),
        loadStats(),
        loadMemorySpots()
      ])
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
      // Reload data after deletion
      await Promise.all([
        loadMemory(),
        loadStats(),
        loadMemorySpots()
      ])
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
      // Reload data after deletion
      await Promise.all([
        loadMemory(),
        loadStats(),
        loadMemorySpots()
      ])
    } catch (err) {
      setError(err.message)
    }
  }

  const handleApplySpot = async (spotId) => {
    if (!spotId) {
      setError('Invalid spot ID')
      return
    }
    
    try {
      setError(null)
      const response = await apiPost(`/api/v1/memory/spots/${spotId}/apply`, {})
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }))
        throw new Error(errorData.error || 'Failed to apply memory spot')
      }
      // Reload data to reflect changes
      await Promise.all([
        loadMemorySpots(),
        loadMemory(),
        loadStats()
      ])
    } catch (err) {
      console.error('Error applying memory spot:', err)
      setError(err.message || 'Failed to apply memory spot')
    }
  }

  const handleRejectSpot = async (spotId) => {
    if (!spotId) {
      setError('Invalid spot ID')
      return
    }
    
    if (!window.confirm('Reject this memory spot?')) {
      return
    }
    
    try {
      setError(null)
      const response = await apiPost(`/api/v1/memory/spots/${spotId}/reject`, {})
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }))
        throw new Error(errorData.error || 'Failed to reject memory spot')
      }
      await loadMemorySpots()
    } catch (err) {
      console.error('Error rejecting memory spot:', err)
      setError(err.message || 'Failed to reject memory spot')
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
        limit: 50,
        min_messages: 5,
      })
      
      if (!response.ok) {
        // Check if response is JSON before trying to parse
        const contentType = response.headers.get('content-type')
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json()
          throw new Error(errorData.error || `Failed to extract memories (${response.status})`)
        } else {
          // Response is not JSON (likely HTML error page)
          const text = await response.text()
          throw new Error(`Server error (${response.status}): ${text.substring(0, 100)}`)
        }
      }
      
      const data = await response.json()
      
      // The extraction now runs in the background, so we get an immediate response
      if (data.status === 'processing') {
        alert(`Started processing ${data.sessions_queued || 0} sessions in the background. Memories will be extracted asynchronously.`)
        
        // Reload spots after a short delay to show any immediate results
        setTimeout(() => {
          loadMemorySpots().catch(err => {
            console.error('Error reloading memory spots:', err)
          })
        }, 2000)
      } else {
        // Legacy response format (shouldn't happen, but handle it)
        alert(`Extracted ${data.total_extracted || 0} memory spots from ${data.processed_sessions || 0} sessions.`)
        loadMemorySpots()
      }
    } catch (err) {
      console.error('Memory extraction error:', err)
      setError(err.message)
    } finally {
      setExtractingSpots(false)
    }
  }

  const handleReviseMemories = async () => {
    if (!window.confirm('Revise memories? This will re-analyze conversations to see what stayed, what changed, and what\'s new. This may take a while.')) {
      return
    }
    
    try {
      setRevisingMemories(true)
      setError(null)
      
      const response = await apiPost('/api/v1/memory/revise', {
        limit: 20,
        days_back: null,
      })
      
      if (!response.ok) {
        const contentType = response.headers.get('content-type')
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json()
          throw new Error(errorData.error || `Failed to revise memories (${response.status})`)
        } else {
          const text = await response.text()
          throw new Error(`Server error (${response.status}): ${text.substring(0, 100)}`)
        }
      }
      
      const data = await response.json()
      
      if (data.success) {
        const stats = data.stats || {}
        alert(`Memory revision complete!\n\nSessions processed: ${stats.sessions_processed || 0}\nMemories extracted: ${stats.total_extracted || 0}\nSessions skipped: ${stats.sessions_skipped || 0}\n\nCheck the "Extracted Memory Spots" tab to review what changed.`)
        // Reload all data after revision
        await Promise.all([
          loadMemorySpots(),
          loadMemory(),
          loadStats()
        ])
      } else {
        throw new Error(data.error || 'Revision failed')
      }
    } catch (err) {
      console.error('Memory revision error:', err)
      setError(err.message)
    } finally {
      setRevisingMemories(false)
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
      <div className="memory-header" style={{ flexShrink: 0 }}>
        <div className="memory-title">
          <h2>Memory</h2>
        </div>
        <div className="memory-actions">
          {activeMainTab === 'user-memory' && (
            <>
              <div className="user-selector">
                <label>User ID:</label>
                <input
                  type="text"
                  value={userId}
                  onChange={(e) => {
                    setUserId(e.target.value)
                    setShowingDefaultUser(false)
                  }}
                  placeholder={isAuthenticated && user?.sub ? user.sub : "default"}
                  title={isAuthenticated && user?.sub && userId === user.sub ? "Your authenticated user ID" : "Change user ID to view another user's memory (admin only)"}
                />
                {isAuthenticated && user?.sub && userId === user.sub && (
                  <span className="user-id-badge" title="Authenticated user">✓</span>
                )}
                {showingDefaultUser && (
                  <span style={{ 
                    padding: '4px 8px', 
                    background: 'rgba(245, 158, 11, 0.2)', 
                    borderRadius: '4px',
                    fontSize: '0.75em',
                    color: '#fbbf24'
                  }} title="Showing default user data">
                    Showing: default
                  </span>
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
            </>
          )}
          <div className="memory-action-buttons">
            <button
              className="extract-memories-button"
              onClick={handleExtractMemories}
              disabled={extractingSpots}
              title="Extract memories from conversations"
            >
              {extractingSpots ? 'Extracting...' : '🔍 Extract Memories'}
            </button>
            <button
              className="revise-memories-button"
              onClick={handleReviseMemories}
              disabled={revisingMemories}
              title="Revise memories to see what stayed, what changed, and what's new"
            >
              {revisingMemories ? 'Revising...' : '🔄 Revise Memories'}
            </button>
            <button
              className="orchestrator-button"
              onClick={() => setShowOrchestrator(!showOrchestrator)}
              title="View orchestrator status"
            >
              {showOrchestrator ? 'Hide' : '⚙️'} Orchestrator
            </button>
          </div>
        </div>
      </div>

      {/* Main Tabs */}
      <div className="main-memory-tabs" style={{ flexShrink: 0 }}>
        <button
          className={`main-memory-tab ${activeMainTab === 'user-memory' ? 'active' : ''}`}
          onClick={() => setActiveMainTab('user-memory')}
        >
          <span className="tab-icon">👤</span>
          <span className="tab-label">User Memory</span>
          <span className="tab-count">
            ({facts.length + preferences.length})
          </span>
        </button>
        <button
          className={`main-memory-tab ${activeMainTab === 'extracted-spots' ? 'active' : ''}`}
          onClick={() => setActiveMainTab('extracted-spots')}
        >
          <span className="tab-icon">📋</span>
          <span className="tab-label">Extracted Memory Spots</span>
          <span className="tab-count">
            ({memorySpots.length})
          </span>
        </button>
      </div>

      <div style={{ flexShrink: 0 }}>
        {error && (
          <div className="memory-error">
            {error}
            <button onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        {(showingDefaultUser || (linkedUserIds.length > 1)) && (
        <div style={{
          padding: '12px 16px',
          background: linkedUserIds.length > 1 
            ? 'rgba(34, 197, 94, 0.15)' 
            : 'rgba(245, 158, 11, 0.15)',
          border: `1px solid ${linkedUserIds.length > 1 
            ? 'rgba(34, 197, 94, 0.3)' 
            : 'rgba(245, 158, 11, 0.3)'}`,
          borderRadius: '10px',
          color: linkedUserIds.length > 1 ? '#4ade80' : '#fbbf24',
          fontSize: '0.9em',
          marginBottom: '16px'
        }}>
          {linkedUserIds.length > 1 ? (
            <div>
              <strong>🔗 Linked Accounts:</strong> Showing memories from {linkedUserIds.length} linked account{linkedUserIds.length > 1 ? 's' : ''}:
              <div style={{ marginTop: '8px', fontSize: '0.85em', opacity: 0.9 }}>
                {linkedUserIds.map((uid, idx) => (
                  <span key={uid} style={{ 
                    display: 'inline-block',
                    marginRight: '8px',
                    padding: '4px 8px',
                    background: 'rgba(0, 0, 0, 0.2)',
                    borderRadius: '4px',
                    fontFamily: 'monospace',
                    fontSize: '0.8em'
                  }}>
                    {uid === userId ? '✓ ' : ''}{uid.substring(0, 20)}{uid.length > 20 ? '...' : ''}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <strong>Note:</strong> No memories found for your user ID ({userId}). Showing memories from "default" user instead.
              <br />
              <small style={{ opacity: 0.8 }}>To see your own memories, make sure data is stored with your Auth0 user ID.</small>
            </div>
          )}
        </div>
        )}

        {showOrchestrator && orchestratorStatus && (
        <div className="orchestrator-status-panel">
          <div className="orchestrator-header">
            <h3>Orchestrator Status</h3>
            <button onClick={() => setShowOrchestrator(false)}>×</button>
          </div>
          <div className="orchestrator-content">
            <div className="orchestrator-section">
              <h4>Models</h4>
              <div className="orchestrator-info">
                <div className="info-row">
                  <span className="info-label">Local (Ollama):</span>
                  <span className={`info-value ${orchestratorStatus.models?.local?.available ? 'available' : 'unavailable'}`}>
                    {orchestratorStatus.models?.local?.available ? '✓ Available' : '✗ Unavailable'}
                  </span>
                </div>
                <div className="info-row">
                  <span className="info-label">Cloud (OpenRouter):</span>
                  <span className={`info-value ${orchestratorStatus.models?.cloud?.available ? 'available' : 'unavailable'}`}>
                    {orchestratorStatus.models?.cloud?.available ? '✓ Available' : '✗ Unavailable'}
                  </span>
                </div>
              </div>
            </div>
            <div className="orchestrator-section">
              <h4>Routing</h4>
              <div className="orchestrator-info">
                <div className="info-row">
                  <span className="info-label">Provider Preference:</span>
                  <span className="info-value">{orchestratorStatus.routing?.provider_preference || 'local'}</span>
                </div>
              </div>
            </div>
            <div className="orchestrator-section">
              <h4>Memory</h4>
              <div className="orchestrator-info">
                <div className="info-row">
                  <span className="info-label">Store Enabled:</span>
                  <span className={`info-value ${orchestratorStatus.memory?.store_enabled ? 'available' : 'unavailable'}`}>
                    {orchestratorStatus.memory?.store_enabled ? '✓ Enabled' : '✗ Disabled'}
                  </span>
                </div>
                <div className="info-row">
                  <span className="info-label">Layers:</span>
                  <span className="info-value">
                    {orchestratorStatus.memory?.layers?.join(', ') || 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        )}
      </div>

      {activeMainTab === 'user-memory' && (
        <>
          <div style={{ flexShrink: 0 }}>
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
          </div>

          {loading ? (
            <div className="memory-loading">Loading user memory...</div>
          ) : (
            <div className="memory-content">
              {/* Facts Section */}
              <div className="memory-section">
                <h3>Facts</h3>
                {facts.length === 0 ? (
                  <div className="memory-empty">
                    <div>No facts stored for this user.</div>
                    {userId && (
                      <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.5)' }}>
                        User ID: {userId}
                        <br />
                        Click "+ Fact" to add your first fact.
                      </div>
                    )}
                  </div>
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
                              currentUserId={userId}
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
                  <div className="memory-empty">
                    <div>No preferences stored for this user.</div>
                    {userId && (
                      <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.5)' }}>
                        Click "+ Preference" to add your first preference.
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="pref-list">
                    {preferences.map(pref => {
                      const isFromLinkedAccount = pref.source_user_id && pref.source_user_id !== userId
                      return (
                        <div key={pref.id} className="pref-card">
                          <div className="pref-header">
                            <span className="pref-key">
                              {pref.preference_key}
                              {isFromLinkedAccount && (
                                <span 
                                  style={{ 
                                    marginLeft: '6px',
                                    fontSize: '0.7em', 
                                    padding: '2px 6px', 
                                    background: 'rgba(34, 197, 94, 0.2)', 
                                    borderRadius: '4px',
                                    color: '#4ade80',
                                    fontFamily: 'monospace'
                                  }}
                                  title={`From linked account: ${pref.source_user_id}`}
                                >
                                  🔗
                                </span>
                              )}
                            </span>
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
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {activeMainTab === 'extracted-spots' && (
        <div className="memory-content">
          <div className="memory-section">
            <div className="memory-section-header">
              <h3>Extracted Memory Spots</h3>
              {activeMemoryTab === 'to-review' && (
                <div className="spot-filters">
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
              )}
            </div>
            
            {/* Memory Tabs */}
            <div className="memory-tabs">
              <button
                className={`memory-tab ${activeMemoryTab === 'to-review' ? 'active' : ''}`}
                onClick={() => {
                  setActiveMemoryTab('to-review')
                  setSpotStatusFilter('')
                  setSpotTypeFilter('')
                }}
              >
                <span className="tab-icon">📋</span>
                <span className="tab-label">To Review</span>
                <span className="tab-count">
                  ({memorySpots.filter(s => s.status === 'extracted').length})
                </span>
              </button>
              <button
                className={`memory-tab ${activeMemoryTab === 'accepted' ? 'active' : ''}`}
                onClick={() => {
                  setActiveMemoryTab('accepted')
                  setSpotStatusFilter('')
                  setSpotTypeFilter('')
                }}
              >
                <span className="tab-icon">✓</span>
                <span className="tab-label">Accepted</span>
                <span className="tab-count">
                  ({memorySpots.filter(s => s.status === 'reviewed' || s.status === 'applied').length})
                </span>
              </button>
              <button
                className={`memory-tab ${activeMemoryTab === 'rejected' ? 'active' : ''}`}
                onClick={() => {
                  setActiveMemoryTab('rejected')
                  setSpotStatusFilter('')
                  setSpotTypeFilter('')
                }}
              >
                <span className="tab-icon">×</span>
                <span className="tab-label">Rejected</span>
                <span className="tab-count">
                  ({memorySpots.filter(s => s.status === 'rejected').length})
                </span>
              </button>
            </div>
            
            {loadingSpots ? (
              <div className="memory-empty">Loading memory spots...</div>
            ) : (() => {
              // Filter memories based on active tab
              let filteredSpots = memorySpots
              
              if (activeMemoryTab === 'to-review') {
                // Show only extracted (not yet reviewed/applied/rejected)
                filteredSpots = memorySpots.filter(spot => spot.status === 'extracted')
              } else if (activeMemoryTab === 'accepted') {
                // Show reviewed and applied (accepted) memory spots
                filteredSpots = memorySpots.filter(spot => 
                  spot.status === 'reviewed' || spot.status === 'applied'
                )
              } else if (activeMemoryTab === 'rejected') {
                // Show rejected memory spots
                filteredSpots = memorySpots.filter(spot => spot.status === 'rejected')
              }
              
              // Apply type filter if active tab is to-review
              if (activeMemoryTab === 'to-review' && spotTypeFilter) {
                filteredSpots = filteredSpots.filter(spot => spot.memory_type === spotTypeFilter)
              }
              
              if (filteredSpots.length === 0) {
                return (
                  <div className="memory-empty">
                    <div>
                      {activeMemoryTab === 'to-review' 
                        ? 'No memories to review.' 
                        : activeMemoryTab === 'accepted'
                        ? 'No accepted memories.'
                        : 'No rejected memories.'}
                    </div>
                    <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted, #71717a)' }}>
                      {activeMemoryTab === 'to-review'
                        ? 'Click "Extract Memories" to extract memories from your conversations.'
                        : activeMemoryTab === 'accepted'
                        ? 'This tab shows all reviewed and applied (accepted) memory spots.'
                        : 'This tab shows all rejected memory spots.'}
                    </div>
                  </div>
                )
              }
              
              return (
                <div className="memory-spots-list">
                  {filteredSpots.map(spot => (
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
              )
            })()}
          </div>
        </div>
      )}
    </div>
  )
}

function FactCard({ fact, onDelete, formatDate, currentUserId }) {
  const isFromLinkedAccount = fact.source_user_id && fact.source_user_id !== currentUserId
  
  return (
    <div className="fact-card">
      <div className="fact-header">
        <span className="fact-key">{fact.fact_key}</span>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {isFromLinkedAccount && (
            <span 
              style={{ 
                fontSize: '0.7em', 
                padding: '2px 6px', 
                background: 'rgba(34, 197, 94, 0.2)', 
                borderRadius: '4px',
                color: '#4ade80',
                fontFamily: 'monospace'
              }}
              title={`From linked account: ${fact.source_user_id}`}
            >
              🔗
            </span>
          )}
          <span className="fact-source" title={`Source: ${fact.source}`}>
            {fact.source === 'conversation' ? '💬' : fact.source === 'telegram' ? '📱' : '🔧'}
          </span>
        </div>
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
  // Parse metadata if it's a string, otherwise use as-is
  let metadata = spot.metadata || {}
  if (typeof metadata === 'string') {
    try {
      metadata = JSON.parse(metadata)
    } catch (e) {
      metadata = {}
    }
  }
  
  // Try to parse content if it's a JSON string
  let parsedContent = spot.content
  if (typeof spot.content === 'string' && spot.content.trim().startsWith('{')) {
    try {
      parsedContent = JSON.parse(spot.content)
    } catch (e) {
      // Not JSON, use as-is
    }
  }
  
  // Format memory content based on type
  const formatMemoryContent = () => {
    // Use metadata if it has keys, otherwise try parsed content, otherwise empty object
    const hasMetadata = metadata && typeof metadata === 'object' && Object.keys(metadata).length > 0
    const hasParsedContent = typeof parsedContent === 'object' && parsedContent !== null && !Array.isArray(parsedContent)
    const data = hasMetadata ? metadata : (hasParsedContent ? parsedContent : {})
    
    switch (spot.memory_type) {
      case 'ai_self_memory':
        // For AI self memories: key is the insight, value is the description
        if (data.key && data.value) {
          return (
            <>
              <div className="spot-memory-key">{data.key}</div>
              <div className="spot-memory-value">{data.value}</div>
            </>
          )
        } else if (data.key) {
          return <div className="spot-memory-key">{data.key}</div>
        } else if (data.value) {
          return <div className="spot-memory-value">{data.value}</div>
        }
        break
        
      case 'user_fact':
        // For user facts: key is the fact name, value is the fact value
        if (data.key && data.value) {
          return (
            <>
              <div className="spot-memory-key">{data.key}</div>
              <div className="spot-memory-value">{data.value}</div>
            </>
          )
        } else if (data.value) {
          return <div className="spot-memory-value">{data.value}</div>
        }
        break
        
      case 'user_preference':
        // For preferences: key is preference name, value is preference value
        if (data.key && data.value) {
          return (
            <>
              <div className="spot-memory-key">{data.key}</div>
              <div className="spot-memory-value">{data.value}</div>
            </>
          )
        } else if (data.value) {
          return <div className="spot-memory-value">{data.value}</div>
        }
        break
        
      case 'capability':
        // For capabilities: name, description, domain
        if (data.name) {
          return (
            <>
              <div className="spot-memory-key">{data.name}</div>
              {data.description && (
                <div className="spot-memory-value">{data.description}</div>
              )}
              {data.domain && (
                <div className="spot-memory-domain">Domain: {data.domain}</div>
              )}
            </>
          )
        }
        break
        
      case 'general':
        // For general memories: just show content
        if (data.content) {
          return <div className="spot-memory-value">{data.content}</div>
        }
        break
    }
    
    // Fallback: show content as-is if no formatting matched
    if (typeof parsedContent === 'string') {
      return <div className="spot-memory-value">{parsedContent}</div>
    } else if (typeof spot.content === 'string') {
      return <div className="spot-memory-value">{spot.content}</div>
    }
    
    return <div className="spot-memory-value">No content available</div>
  }
  
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
        {formatMemoryContent()}
      </div>
      
      <div className="spot-metrics">
        <div className="spot-metric">
          <span className="metric-label">Confidence:</span>
          <span className="metric-value" style={{ color: (spot.confidence || 0) >= 0.8 ? '#10b981' : (spot.confidence || 0) >= 0.6 ? '#f59e0b' : '#ef4444' }}>
            {((spot.confidence || 0) * 100).toFixed(0)}%
          </span>
        </div>
        <div className="spot-metric">
          <span className="metric-label">Importance:</span>
          <span className="metric-value">{spot.importance != null ? spot.importance : 'N/A'}/10</span>
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

