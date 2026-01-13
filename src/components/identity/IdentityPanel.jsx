import React, { useState, useEffect, useCallback } from 'react'
import { apiGet, apiPost, apiDelete } from '../../services/api'

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
    <div className="panel p-5">
      <div className="flex justify-between items-center mb-5 pb-4 border-b border-white-opacity-10 flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h2 className="m-0 text-1.3em font-600 bg-gradient-to-br from-white to-red-accent bg-clip-text text-transparent">ARES Identity</h2>
          <span className="px-3 py-1 bg-red-bg-4 rounded-[20px] text-0.8em text-red-accent">{memories.length} memories</span>
        </div>
        <div className="flex gap-2.5">
          <button 
            className="px-4.5 py-2.5 border border-white-opacity-15 rounded-lg bg-white-opacity-6 text-white-opacity-90 text-0.85em font-500 cursor-pointer transition-all duration-250 hover:bg-white-opacity-10 hover:border-white-opacity-25 hover:-translate-y-0.5"
            onClick={handleRecordMilestone}
            title="Record a milestone"
          >
            + Milestone
          </button>
          <button 
            className="px-4.5 py-2.5 border border-red-border-3 rounded-lg bg-gradient-to-br from-red-bg-5 to-red-bg-6 text-white text-0.85em font-500 cursor-pointer transition-all duration-250 hover:from-red-bg-6 hover:to-red-bg-5 hover:border-red-border-4 hover:-translate-y-0.5"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            {showAddForm ? 'Cancel' : '+ Add Memory'}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex justify-between items-center p-3 mb-4 bg-[rgba(220,38,38,0.15)] border border-[rgba(220,38,38,0.3)] rounded-lg text-[#fca5a5] text-0.9em animate-fade-in">
          {error}
          <button onClick={() => setError(null)} className="px-3.5 py-1.5 bg-white-opacity-10 border-none rounded text-white cursor-pointer text-0.9em transition-all duration-200 hover:bg-white-opacity-15">Dismiss</button>
        </div>
      )}

      <div className="flex gap-2 mb-5 pb-4 border-b border-white-opacity-8 flex-wrap">
        <button
          className={`px-4 py-2 bg-white-opacity-4 border border-white-opacity-10 rounded-[20px] text-white-opacity-70 text-0.85em cursor-pointer transition-all duration-250 hover:bg-white-opacity-8 hover:border-white-opacity-20 ${
            selectedCategory === null ? 'bg-gradient-to-br from-red-bg-6 to-red-bg-4 border-red-border-4 text-white shadow-[0_2px_12px_rgba(255,0,0,0.2)]' : ''
          }`}
          onClick={() => setSelectedCategory(null)}
        >
          All
        </button>
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            className={`px-4 py-2 bg-white-opacity-4 border border-white-opacity-10 rounded-[20px] text-white-opacity-70 text-0.85em cursor-pointer transition-all duration-250 hover:bg-white-opacity-8 hover:border-white-opacity-20 ${
              selectedCategory === cat.id ? 'bg-gradient-to-br from-red-bg-6 to-red-bg-4 border-red-border-4 text-white shadow-[0_2px_12px_rgba(255,0,0,0.2)]' : ''
            }`}
            onClick={() => setSelectedCategory(cat.id)}
          >
            {cat.icon} {cat.label}
          </button>
        ))}
      </div>

      {showAddForm && (
        <form className="bg-white-opacity-3 border border-white-opacity-10 rounded-2xl p-5 mb-5 animate-slide-in-down" onSubmit={handleAddMemory}>
          <div className="flex gap-3 mb-3.5 flex-wrap">
            <select
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="flex-1 min-w-[150px] px-4 py-3 bg-white-opacity-6 border border-white-opacity-12 rounded-lg text-white text-0.9em outline-none transition-all duration-200 focus:border-red-border-4 focus:shadow-[0_0_0_3px_rgba(255,0,0,0.1)]"
            >
              {CATEGORIES.map(cat => (
                <option key={cat.id} value={cat.id} className="bg-[#1a1a1f]">
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
              className="flex-1 min-w-[150px] px-4 py-3 bg-white-opacity-6 border border-white-opacity-12 rounded-lg text-white text-0.9em outline-none transition-all duration-200 focus:border-red-border-4 focus:shadow-[0_0_0_3px_rgba(255,0,0,0.1)]"
            />
          </div>
          <div className="flex gap-3 mb-3.5 flex-wrap">
            <textarea
              placeholder="Value (e.g., I find discussions about AI architecture fascinating)"
              value={formData.value}
              onChange={(e) => setFormData({ ...formData, value: e.target.value })}
              required
              className="w-full min-h-[80px] px-4 py-3 bg-white-opacity-6 border border-white-opacity-12 rounded-lg text-white text-0.9em resize-y outline-none transition-all duration-200 font-inherit focus:border-red-border-4 focus:shadow-[0_0_0_3px_rgba(255,0,0,0.1)]"
            />
          </div>
          <div className="flex gap-3 items-center">
            <label className="flex flex-col gap-2 text-white-opacity-80 text-0.85em flex-1">
              Importance: {formData.importance}
              <input
                type="range"
                min="1"
                max="10"
                value={formData.importance}
                onChange={(e) => setFormData({ ...formData, importance: parseInt(e.target.value) })}
                className="w-full h-1.5 -webkit-appearance-none appearance-none bg-white-opacity-10 rounded cursor-pointer"
                style={{
                  background: `linear-gradient(to right, rgba(255, 0, 0, 0.3) 0%, rgba(255, 0, 0, 0.3) ${(formData.importance - 1) * 11.11}%, rgba(255, 255, 255, 0.1) ${(formData.importance - 1) * 11.11}%, rgba(255, 255, 255, 0.1) 100%)`
                }}
              />
            </label>
            <button 
              type="submit" 
              disabled={submitting}
              className="px-6 py-3 bg-gradient-to-br from-red-bg-6 to-red-bg-5 border-none rounded-lg text-white font-600 cursor-pointer transition-all duration-200 hover:from-red-bg-5 hover:to-red-bg-6 hover:-translate-y-0.5 hover:shadow-[0_4px_16px_rgba(255,0,0,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? 'Adding...' : 'Add Memory'}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="text-center py-12 px-6 text-white-opacity-50 text-1em">Loading memories...</div>
      ) : memories.length === 0 ? (
        <div className="text-center py-12 px-6 text-white-opacity-50 text-1em">
          <p>No memories found.</p>
          <p>Run <code className="inline-block mt-3 px-3.5 py-2 bg-red-bg-4 rounded-lg font-mono text-0.9em text-[#ff8080]">python init_ares.py --init</code> to initialize ARES identity.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6 overflow-y-auto pr-1 animate-fade-in">
          {selectedCategory ? (
            <div>
              <div className="flex items-center gap-2.5 mb-3.5 pb-2.5 border-b border-white-opacity-8">
                <span className="text-1.3em">{getCategoryInfo(selectedCategory).icon}</span>
                <span className="text-1em font-600 text-white">{getCategoryInfo(selectedCategory).label}</span>
              </div>
              <div className="grid gap-3">
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
                <div key={cat.id} className="animate-fade-in">
                  <div className="flex items-center gap-2.5 mb-3.5 pb-2.5 border-b border-white-opacity-8">
                    <span className="text-1.3em">{cat.icon}</span>
                    <span className="text-1em font-600 text-white">{cat.label}</span>
                    <span className="px-2.5 py-0.5 bg-white-opacity-10 rounded-xl text-0.75em text-white-opacity-60">{catMemories.length}</span>
                  </div>
                  <div className="grid gap-3">
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
  
  const borderColorClass = importanceClass === 'high' ? 'border-l-[rgba(255,0,0,0.6)]' : 
                          importanceClass === 'medium' ? 'border-l-[rgba(255,200,0,0.5)]' : 
                          'border-l-[rgba(100,200,255,0.4)]'
  
  return (
    <div className={`bg-white-opacity-3 border border-white-opacity-8 border-l-[3px] ${borderColorClass} rounded-2xl p-4 transition-all duration-250 hover:bg-white-opacity-5 hover:border-white-opacity-12 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(0,0,0,0.3)]`}>
      <div className="flex justify-between items-center mb-2.5">
        <span className="font-600 text-red-accent font-mono text-0.9em">{memory.memory_key}</span>
        <div className="flex items-center gap-2">
          {!isEditing && (
            <button 
              className="w-7 h-7 border-none rounded bg-white-opacity-8 text-white-opacity-60 cursor-pointer flex items-center justify-center text-0.9em transition-all duration-200 hover:bg-white-opacity-15 hover:text-white"
              onClick={() => setIsEditing(true)}
              title="Edit memory"
            >
              ✎
            </button>
          )}
          <span className="text-0.7em text-red-border-4" style={{ letterSpacing: '-2px' }} title={`Importance: ${memory.importance}/10`}>
            {'●'.repeat(Math.ceil(memory.importance / 2))}
          </span>
        </div>
      </div>
      
      {isEditing ? (
        <div className="animate-fade-in">
          <textarea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            rows={3}
            autoFocus
            className="w-full min-h-[70px] px-3 py-3 bg-white-opacity-6 border border-white-opacity-12 rounded-lg text-white text-0.9em resize-y outline-none font-inherit mb-3 transition-all duration-200 focus:border-red-border-4"
          />
          <div className="flex justify-between items-center gap-3 flex-wrap">
            <label className="flex items-center gap-2.5 text-white-opacity-70 text-0.85em">
              Importance: {editImportance}
              <input
                type="range"
                min="1"
                max="10"
                value={editImportance}
                onChange={(e) => setEditImportance(parseInt(e.target.value))}
                className="w-[100px] h-1.5 -webkit-appearance-none appearance-none bg-white-opacity-10 rounded cursor-pointer"
                style={{
                  background: `linear-gradient(to right, rgba(255, 0, 0, 0.3) 0%, rgba(255, 0, 0, 0.3) ${(editImportance - 1) * 11.11}%, rgba(255, 255, 255, 0.1) ${(editImportance - 1) * 11.11}%, rgba(255, 255, 255, 0.1) 100%)`
                }}
              />
            </label>
            <div className="flex gap-2">
              <button 
                className="px-4 py-2 border-none rounded-lg text-0.85em font-500 cursor-pointer transition-all duration-200 bg-gradient-to-br from-green-bg-2 to-green-bg-1 text-white hover:from-green-bg-1 hover:to-green-bg-2 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button 
                className="px-4 py-2 border-none rounded-lg text-0.85em font-500 cursor-pointer transition-all duration-200 bg-white-opacity-10 text-white-opacity-80 hover:bg-white-opacity-15 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleCancel}
                disabled={saving}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-white-opacity-85 text-0.95em leading-relaxed mb-3">{memory.memory_value}</div>
      )}
      
      <div className="flex justify-between items-center pt-2.5 border-t border-white-opacity-6">
        <span className="text-0.75em text-white-opacity-40 font-mono">{formatDate(memory.updated_at)}</span>
        <button 
          className="w-6 h-6 border-none rounded bg-transparent text-[rgba(255,100,100,0.6)] cursor-pointer flex items-center justify-center text-1.2em transition-all duration-200 hover:bg-red-bg-5 hover:text-[#ff6b6b]"
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

