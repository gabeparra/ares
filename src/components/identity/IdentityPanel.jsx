import React, { useState, useEffect, useCallback } from 'react'
import { apiGet, apiPost, apiDelete } from '../../services/api'
import './IdentityPanel.css'

const CATEGORIES = [
  { id: 'identity', label: 'Identity', icon: '🤖', description: 'Core facts about ARES' },
  { id: 'milestone', label: 'Milestones', icon: '🏁', description: 'Important events in history' },
  { id: 'observation', label: 'Observations', icon: '👁', description: 'Self-noted tendencies' },
  { id: 'preference', label: 'Preferences', icon: '⭐', description: 'Emergent likes/dislikes' },
  { id: 'relationship', label: 'Relationships', icon: '🤝', description: 'User relationship facts' },
]

function IdentityPanel() {
  const [memories, setMemories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [formData, setFormData] = useState({
    category: 'observation',
    key: '',
    value: '',
    importance: 5,
  })
  const [submitting, setSubmitting] = useState(false)

  const loadMemories = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      
      let url = '/api/v1/self-memory'
      if (selectedCategory) {
        url += `?category=${selectedCategory}`
      }
      
      const response = await apiGet(url)
      if (!response.ok) {
        throw new Error('Failed to load memories')
      }
      
      const data = await response.json()
      setMemories(data.memories || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [selectedCategory])

  useEffect(() => {
    loadMemories()
  }, [loadMemories])

  const handleAddMemory = async (e) => {
    e.preventDefault()
    
    if (!formData.key.trim() || !formData.value.trim()) {
      return
    }
    
    try {
      setSubmitting(true)
      
      const response = await apiPost('/api/v1/self-memory', formData)
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to add memory')
      }
      
      setShowAddForm(false)
      setFormData({ category: 'observation', key: '', value: '', importance: 5 })
      loadMemories()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteMemory = async (memoryId) => {
    if (!window.confirm('Delete this memory?')) {
      return
    }
    
    try {
      const response = await apiDelete(`/api/v1/self-memory/${memoryId}`)
      if (!response.ok) {
        throw new Error('Failed to delete memory')
      }
      loadMemories()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleRecordMilestone = async () => {
    const event = prompt('Milestone event key (e.g., "first_tool_use"):')
    if (!event) return
    
    const description = prompt('Milestone description:')
    if (!description) return
    
    try {
      const response = await apiPost('/api/v1/self-memory/milestone', {
        event,
        description,
        importance: 7,
      })
      
      if (!response.ok) {
        throw new Error('Failed to record milestone')
      }
      
      loadMemories()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleUpdateMemory = async (memoryId, category, key, value, importance) => {
    try {
      const response = await apiPost('/api/v1/self-memory', {
        category,
        key,
        value,
        importance,
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to update memory')
      }
      
      loadMemories()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  // Group memories by category
  const groupedMemories = memories.reduce((acc, mem) => {
    if (!acc[mem.category]) {
      acc[mem.category] = []
    }
    acc[mem.category].push(mem)
    return acc
  }, {})

  const getCategoryInfo = (categoryId) => {
    return CATEGORIES.find(c => c.id === categoryId) || { label: categoryId, icon: '📝' }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="panel identity-panel">
      <div className="identity-header">
        <div className="identity-title">
          <h2>ARES Identity</h2>
          <span className="memory-count">{memories.length} memories</span>
        </div>
        <div className="identity-actions">
          <button 
            className="milestone-button"
            onClick={handleRecordMilestone}
            title="Record a milestone"
          >
            + Milestone
          </button>
          <button 
            className="add-memory-button"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            {showAddForm ? 'Cancel' : '+ Add Memory'}
          </button>
        </div>
      </div>

      {error && (
        <div className="identity-error">
          {error}
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <div className="category-filter">
        <button
          className={`category-chip ${selectedCategory === null ? 'active' : ''}`}
          onClick={() => setSelectedCategory(null)}
        >
          All
        </button>
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            className={`category-chip ${selectedCategory === cat.id ? 'active' : ''}`}
            onClick={() => setSelectedCategory(cat.id)}
          >
            {cat.icon} {cat.label}
          </button>
        ))}
      </div>

      {showAddForm && (
        <form className="add-memory-form" onSubmit={handleAddMemory}>
          <div className="form-row">
            <select
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            >
              {CATEGORIES.map(cat => (
                <option key={cat.id} value={cat.id}>
                  {cat.icon} {cat.label}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Key (e.g., favorite_topic)"
              value={formData.key}
              onChange={(e) => setFormData({ ...formData, key: e.target.value })}
              required
            />
          </div>
          <div className="form-row">
            <textarea
              placeholder="Value (e.g., I find discussions about AI architecture fascinating)"
              value={formData.value}
              onChange={(e) => setFormData({ ...formData, value: e.target.value })}
              required
            />
          </div>
          <div className="form-row">
            <label>
              Importance: {formData.importance}
              <input
                type="range"
                min="1"
                max="10"
                value={formData.importance}
                onChange={(e) => setFormData({ ...formData, importance: parseInt(e.target.value) })}
              />
            </label>
            <button type="submit" disabled={submitting}>
              {submitting ? 'Adding...' : 'Add Memory'}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="identity-loading">Loading memories...</div>
      ) : memories.length === 0 ? (
        <div className="identity-empty">
          <p>No memories found.</p>
          <p>Run <code>python init_ares.py --init</code> to initialize ARES identity.</p>
        </div>
      ) : (
        <div className="memories-container">
          {selectedCategory ? (
            <div className="memory-category">
              <div className="category-header">
                <span className="category-icon">{getCategoryInfo(selectedCategory).icon}</span>
                <span className="category-label">{getCategoryInfo(selectedCategory).label}</span>
              </div>
              <div className="memory-list">
                {(groupedMemories[selectedCategory] || []).map(mem => (
                  <MemoryCard
                    key={mem.id}
                    memory={mem}
                    onDelete={handleDeleteMemory}
                    onUpdate={handleUpdateMemory}
                    formatDate={formatDate}
                  />
                ))}
              </div>
            </div>
          ) : (
            CATEGORIES.map(cat => {
              const catMemories = groupedMemories[cat.id] || []
              if (catMemories.length === 0) return null
              
              return (
                <div key={cat.id} className="memory-category">
                  <div className="category-header">
                    <span className="category-icon">{cat.icon}</span>
                    <span className="category-label">{cat.label}</span>
                    <span className="category-count">{catMemories.length}</span>
                  </div>
                  <div className="memory-list">
                    {catMemories.map(mem => (
                      <MemoryCard
                        key={mem.id}
                        memory={mem}
                        onDelete={handleDeleteMemory}
                        onUpdate={handleUpdateMemory}
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
  )
}

function MemoryCard({ memory, onDelete, onUpdate, formatDate }) {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(memory.memory_value)
  const [editImportance, setEditImportance] = useState(memory.importance)
  const [saving, setSaving] = useState(false)
  
  const importanceClass = memory.importance >= 8 ? 'high' : memory.importance >= 5 ? 'medium' : 'low'
  
  const handleSave = async () => {
    if (!editValue.trim()) return
    
    setSaving(true)
    try {
      await onUpdate(memory.id, memory.category, memory.memory_key, editValue, editImportance)
      setIsEditing(false)
    } catch (err) {
      console.error('Failed to update memory:', err)
    } finally {
      setSaving(false)
    }
  }
  
  const handleCancel = () => {
    setEditValue(memory.memory_value)
    setEditImportance(memory.importance)
    setIsEditing(false)
  }
  
  return (
    <div className={`memory-card importance-${importanceClass}`}>
      <div className="memory-header">
        <span className="memory-key">{memory.memory_key}</span>
        <div className="memory-header-actions">
          {!isEditing && (
            <button 
              className="memory-edit"
              onClick={() => setIsEditing(true)}
              title="Edit memory"
            >
              ✎
            </button>
          )}
          <span className="memory-importance" title={`Importance: ${memory.importance}/10`}>
            {'●'.repeat(Math.ceil(memory.importance / 2))}
          </span>
        </div>
      </div>
      
      {isEditing ? (
        <div className="memory-edit-form">
          <textarea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            rows={3}
            autoFocus
          />
          <div className="memory-edit-controls">
            <label className="importance-slider">
              Importance: {editImportance}
              <input
                type="range"
                min="1"
                max="10"
                value={editImportance}
                onChange={(e) => setEditImportance(parseInt(e.target.value))}
              />
            </label>
            <div className="memory-edit-buttons">
              <button 
                className="memory-save"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button 
                className="memory-cancel"
                onClick={handleCancel}
                disabled={saving}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="memory-value">{memory.memory_value}</div>
      )}
      
      <div className="memory-footer">
        <span className="memory-date">{formatDate(memory.updated_at)}</span>
        <button 
          className="memory-delete"
          onClick={() => onDelete(memory.id)}
          title="Delete memory"
        >
          ×
        </button>
      </div>
    </div>
  )
}

export default IdentityPanel

