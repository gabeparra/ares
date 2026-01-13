import React, { useState, useEffect, useCallback } from 'react'
import { apiGet, apiPost, apiDelete } from '../../services/api'

function UserManagerPanel() {
  const [activeView, setActiveView] = useState('users') // 'users' | 'telegram' | 'nicknames' | 'account-links'
  const [users, setUsers] = useState([])
  const [telegramUsers, setTelegramUsers] = useState([])
  const [nicknames, setNicknames] = useState([])
  const [accountLinks, setAccountLinks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [selectedTelegramUser, setSelectedTelegramUser] = useState(null)
  const [showLinkModal, setShowLinkModal] = useState(false)
  const [showNicknameModal, setShowNicknameModal] = useState(false)
  const [showAccountLinkModal, setShowAccountLinkModal] = useState(false)
  const [newNickname, setNewNickname] = useState('')
  const [newLocalUserId, setNewLocalUserId] = useState('')
  const [newAuth0UserId, setNewAuth0UserId] = useState('')
  const [newLinkNotes, setNewLinkNotes] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  // Fetch Auth0 users
  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const params = new URLSearchParams()
      if (searchQuery) params.set('search', searchQuery)
      
      const response = await apiGet(`/api/v1/users?${params}`)
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to fetch users')
      }
      const data = await response.json()
      setUsers(data.users || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [searchQuery])

  // Fetch Telegram users
  const fetchTelegramUsers = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiGet('/api/v1/users/telegram')
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to fetch Telegram users')
      }
      const data = await response.json()
      setTelegramUsers(data.telegram_users || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch nicknames
  const fetchNicknames = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiGet('/api/v1/users/telegram/nicknames')
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to fetch nicknames')
      }
      const data = await response.json()
      setNicknames(data.nicknames || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch account links
  const fetchAccountLinks = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiGet('/api/v1/account-links')
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to fetch account links')
      }
      const data = await response.json()
      setAccountLinks(data.links || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Load data based on active view
  useEffect(() => {
    if (activeView === 'users') {
      fetchUsers()
    } else if (activeView === 'telegram') {
      fetchTelegramUsers()
    } else if (activeView === 'nicknames') {
      fetchNicknames()
    } else if (activeView === 'account-links') {
      fetchAccountLinks()
    }
  }, [activeView, fetchUsers, fetchTelegramUsers, fetchNicknames, fetchAccountLinks])

  // Link Telegram to Auth0 user
  const handleLinkTelegram = async (telegramChatId, userId) => {
    try {
      setActionLoading(true)
      const response = await apiPost('/api/v1/users/telegram/link', {
        telegram_chat_id: telegramChatId,
        user_id: userId,
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to link accounts')
      }
      
      // Refresh data
      await Promise.all([fetchUsers(), fetchTelegramUsers()])
      setShowLinkModal(false)
      setSelectedTelegramUser(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(false)
    }
  }

  // Unlink Telegram from Auth0 user
  const handleUnlinkTelegram = async (telegramChatId) => {
    if (!window.confirm('Are you sure you want to unlink this Telegram account?')) {
      return
    }
    
    try {
      setActionLoading(true)
      const response = await apiPost('/api/v1/users/telegram/unlink', {
        telegram_chat_id: telegramChatId,
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to unlink account')
      }
      
      // Refresh data
      await Promise.all([fetchUsers(), fetchTelegramUsers()])
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(false)
    }
  }

  // Add nickname for Telegram user
  const handleAddNickname = async (telegramChatId, nickname) => {
    try {
      setActionLoading(true)
      const response = await apiPost('/api/v1/users/telegram/nickname', {
        telegram_chat_id: telegramChatId,
        nickname: nickname,
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to add nickname')
      }
      
      setShowNicknameModal(false)
      setNewNickname('')
      setSelectedTelegramUser(null)
      await fetchNicknames()
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(false)
    }
  }

  // Delete nickname
  const handleDeleteNickname = async (nickname) => {
    if (!window.confirm(`Delete nickname "${nickname}"?`)) {
      return
    }
    
    try {
      setActionLoading(true)
      const response = await apiDelete(`/api/v1/users/telegram/nickname/${encodeURIComponent(nickname)}`)
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to delete nickname')
      }
      
      await fetchNicknames()
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(false)
    }
  }

  // Create account link
  const handleCreateAccountLink = async () => {
    if (!newLocalUserId.trim()) {
      setError('Local user ID is required')
      return
    }
    
    try {
      setActionLoading(true)
      const payload = {
        local_user_id: newLocalUserId.trim(),
        notes: newLinkNotes.trim(),
        auto_verify: true,
      }
      
      // If a specific Auth0 user ID is provided, include it
      if (newAuth0UserId.trim()) {
        payload.auth0_user_id = newAuth0UserId.trim()
      }
      
      const response = await apiPost('/api/v1/account-links/create', payload)
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to create account link')
      }
      
      setShowAccountLinkModal(false)
      setNewLocalUserId('')
      setNewAuth0UserId('')
      setNewLinkNotes('')
      await fetchAccountLinks()
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(false)
    }
  }

  // Delete account link
  const handleDeleteAccountLink = async (linkId) => {
    if (!window.confirm('Are you sure you want to delete this account link?')) {
      return
    }
    
    try {
      setActionLoading(true)
      const response = await apiPost('/api/v1/account-links/delete', { link_id: linkId })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to delete account link')
      }
      
      await fetchAccountLinks()
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(false)
    }
  }

  // Verify account link
  const handleVerifyAccountLink = async (linkId) => {
    try {
      setActionLoading(true)
      const response = await apiPost('/api/v1/account-links/verify', { link_id: linkId })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to verify account link')
      }
      
      await fetchAccountLinks()
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(false)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never'
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getProviderIcon = (provider) => {
    switch (provider) {
      case 'google-oauth2':
        return '🔵'
      case 'auth0':
        return '🔐'
      case 'github':
        return '⚫'
      default:
        return '🔑'
    }
  }

  return (
    <div className="panel flex flex-col h-full overflow-hidden p-5">
      <div className="panel-header flex-shrink-0 text-white-opacity-92 border-b border-white-opacity-8 pb-2 mb-3 text-lg leading-tight font-semibold flex justify-between items-center flex-wrap gap-3">
        <h2 className="m-0 text-1.3em font-600 bg-gradient-to-br from-white to-red-accent bg-clip-text text-transparent">User Manager</h2>
        <div className="flex gap-2 mb-5 border-b border-white-opacity-10 pb-2">
          <button
            className={`px-4 py-2 bg-transparent border-none rounded-lg transition-all duration-200 text-0.9em font-500 cursor-pointer ${
              activeView === 'users'
                ? 'text-white bg-red-bg-5 border-b-2 border-red-border-4'
                : 'text-white-opacity-60 hover:bg-white-opacity-5 hover:text-white-opacity-90'
            }`}
            onClick={() => setActiveView('users')}
          >
            Auth0 Users
          </button>
          <button
            className={`px-4 py-2 bg-transparent border-none rounded-lg transition-all duration-200 text-0.9em font-500 cursor-pointer ${
              activeView === 'telegram'
                ? 'text-white bg-red-bg-5 border-b-2 border-red-border-4'
                : 'text-white-opacity-60 hover:bg-white-opacity-5 hover:text-white-opacity-90'
            }`}
            onClick={() => setActiveView('telegram')}
          >
            Telegram Users
          </button>
          <button
            className={`px-4 py-2 bg-transparent border-none rounded-lg transition-all duration-200 text-0.9em font-500 cursor-pointer ${
              activeView === 'nicknames'
                ? 'text-white bg-red-bg-5 border-b-2 border-red-border-4'
                : 'text-white-opacity-60 hover:bg-white-opacity-5 hover:text-white-opacity-90'
            }`}
            onClick={() => setActiveView('nicknames')}
          >
            Nicknames
          </button>
          <button
            className={`px-4 py-2 bg-transparent border-none rounded-lg transition-all duration-200 text-0.9em font-500 cursor-pointer ${
              activeView === 'account-links'
                ? 'text-white bg-red-bg-5 border-b-2 border-red-border-4'
                : 'text-white-opacity-60 hover:bg-white-opacity-5 hover:text-white-opacity-90'
            }`}
            onClick={() => setActiveView('account-links')}
          >
            Account Links
          </button>
        </div>
      </div>

      {error && (
        <div className="flex justify-between items-center p-3 mb-4 bg-[rgba(255,100,100,0.2)] border border-[rgba(255,100,100,0.4)] rounded-lg text-white text-0.9em">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="bg-transparent border-none text-white cursor-pointer text-1.2em p-0 w-6 h-6 flex items-center justify-center hover:bg-white-opacity-10 rounded">✕</button>
        </div>
      )}

      {activeView === 'users' && (
        <div className="flex-1 overflow-y-auto overflow-x-hidden py-4 min-h-0">
          <div className="flex gap-2 mb-5">
            <input
              type="text"
              placeholder="Search users by name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchUsers()}
              className="flex-1 px-3.5 py-2.5 bg-white-opacity-5 border border-white-opacity-10 rounded-lg text-white text-0.9em outline-none focus:border-red-border-4 focus:bg-white-opacity-8"
            />
            <button 
              onClick={fetchUsers} 
              disabled={loading}
              className="px-4 py-2.5 bg-red-bg-5 border border-red-border-3 rounded-lg text-white cursor-pointer transition-all duration-200 hover:bg-red-bg-6 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '...' : '🔍'}
            </button>
          </div>

          {loading ? (
            <div className="text-center py-10 text-white-opacity-60 text-0.9em">Loading users...</div>
          ) : (
            <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-4">
              {users.map((user) => (
                <div
                  key={user.user_id}
                  className={`flex items-center gap-4 p-4 bg-white-opacity-3 border border-white-opacity-8 rounded-2xl transition-all duration-200 cursor-pointer hover:bg-white-opacity-5 hover:border-white-opacity-12 ${
                    selectedUser?.user_id === user.user_id ? 'bg-red-bg-3 border-red-border-3' : ''
                  }`}
                  onClick={() => setSelectedUser(selectedUser?.user_id === user.user_id ? null : user)}
                >
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-red-bg-6 to-red-bg-5 flex items-center justify-center text-1.2em flex-shrink-0">
                    {user.picture ? (
                      <img src={user.picture} alt="" className="w-full h-full rounded-full object-cover" />
                    ) : (
                      <div className="text-white font-600">{user.name?.[0] || user.email?.[0] || '?'}</div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-600 text-white mb-1">{user.name || 'No name'}</div>
                    <div className="text-0.85em text-white-opacity-50 font-mono overflow-hidden text-ellipsis whitespace-nowrap">{user.email}</div>
                    <div className="flex gap-3 mt-2 text-0.8em text-white-opacity-60">
                      <span className="flex gap-1">
                        {user.providers?.map((p, i) => (
                          <span key={i} title={p}>{getProviderIcon(p)}</span>
                        ))}
                      </span>
                      <span>{user.logins_count} logins</span>
                    </div>
                    {user.telegram_chat_ids?.length > 0 && (
                      <div className="flex gap-1.5 mt-2 flex-wrap">
                        {user.telegram_chat_ids.map((chatId) => (
                          <span key={chatId} className="text-0.75em px-2 py-1 bg-[rgba(0,136,204,0.2)] border border-[rgba(0,136,204,0.4)] rounded text-white-opacity-90" title={`Telegram: ${chatId}`}>
                            📱 {chatId}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  {selectedUser?.user_id === user.user_id && (
                    <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-white-opacity-10 w-full">
                      <div className="flex justify-between gap-3 text-0.85em text-white-opacity-70 mb-1.5">
                        <span className="font-600 text-white-opacity-90">Created:</span>
                        <span>{formatDate(user.created_at)}</span>
                      </div>
                      <div className="flex justify-between gap-3 text-0.85em text-white-opacity-70 mb-1.5">
                        <span className="font-600 text-white-opacity-90">Last Login:</span>
                        <span>{formatDate(user.last_login)}</span>
                      </div>
                      <div className="flex justify-between gap-3 text-0.85em text-white-opacity-70 mb-1.5">
                        <span className="font-600 text-white-opacity-90">User ID:</span>
                        <code className="font-mono text-0.8em bg-black bg-opacity-30 px-1.5 py-0.5 rounded break-all">{user.user_id}</code>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {users.length === 0 && !loading && (
                <div className="text-center py-10 text-white-opacity-50 text-0.9em">No users found</div>
              )}
            </div>
          )}
        </div>
      )}

      {activeView === 'telegram' && (
        <div className="flex-1 overflow-y-auto overflow-x-hidden py-4 min-h-0">
          <div className="flex gap-2 mb-4 flex-wrap">
            <button 
              onClick={fetchTelegramUsers} 
              disabled={loading} 
              className="px-3.5 py-2 bg-white-opacity-5 border border-white-opacity-10 rounded-lg text-white cursor-pointer text-0.85em transition-all duration-200 hover:bg-white-opacity-10 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : '🔄 Refresh'}
            </button>
          </div>

          {loading ? (
            <div className="text-center py-10 text-white-opacity-60 text-0.9em">Loading Telegram users...</div>
          ) : (
            <div className="flex flex-col gap-3">
              {telegramUsers.map((tgUser) => (
                <div
                  key={tgUser.chat_id}
                  className={`flex items-center gap-4 p-4 bg-white-opacity-3 border border-white-opacity-8 rounded-2xl transition-all duration-200 ${
                    tgUser.is_linked 
                      ? 'border-[rgba(0,255,0,0.3)] bg-[rgba(0,255,0,0.05)]' 
                      : 'border-[rgba(255,255,0,0.3)] bg-[rgba(255,255,0,0.05)]'
                  }`}
                >
                  <div className="text-2em flex-shrink-0">📱</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-600 text-white mb-1">{tgUser.title}</div>
                    <div className="text-0.85em text-white-opacity-60 font-mono mb-1.5">Chat ID: {tgUser.chat_id}</div>
                    <div className="flex gap-3 flex-wrap text-0.8em text-white-opacity-60">
                      {tgUser.is_linked ? (
                        <span className="text-[rgba(0,255,0,0.8)]">
                          ✓ Linked to: <code className="font-mono">{tgUser.linked_user_id}</code>
                        </span>
                      ) : (
                        <span className="text-[rgba(255,255,0,0.8)]">○ Not linked</span>
                      )}
                      <span>Last active: {formatDate(tgUser.last_active)}</span>
                    </div>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    {tgUser.is_linked ? (
                      <button
                        className="px-3.5 py-2 border-none rounded-lg cursor-pointer text-0.85em font-500 transition-all duration-200 bg-[rgba(255,100,100,0.2)] text-white border border-[rgba(255,100,100,0.4)] hover:bg-[rgba(255,100,100,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => handleUnlinkTelegram(tgUser.chat_id)}
                        disabled={actionLoading}
                      >
                        Unlink
                      </button>
                    ) : (
                      <button
                        className="px-3.5 py-2 border-none rounded-lg cursor-pointer text-0.85em font-500 transition-all duration-200 bg-[rgba(0,136,204,0.2)] text-white border border-[rgba(0,136,204,0.4)] hover:bg-[rgba(0,136,204,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => {
                          setSelectedTelegramUser(tgUser)
                          setShowLinkModal(true)
                        }}
                        disabled={actionLoading}
                      >
                        Link to User
                      </button>
                    )}
                    <button
                      className="px-3.5 py-2 border-none rounded-lg cursor-pointer text-0.85em font-500 transition-all duration-200 bg-[rgba(255,200,0,0.2)] text-white border border-[rgba(255,200,0,0.4)] hover:bg-[rgba(255,200,0,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
                      onClick={() => {
                        setSelectedTelegramUser(tgUser)
                        setShowNicknameModal(true)
                      }}
                      disabled={actionLoading}
                    >
                      Add Nickname
                    </button>
                  </div>
                </div>
              ))}
              {telegramUsers.length === 0 && !loading && (
                <div className="text-center py-10 text-white-opacity-50 text-0.9em">
                  No Telegram users found. Users will appear here after they message the bot.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeView === 'nicknames' && (
        <div className="flex-1 overflow-y-auto overflow-x-hidden py-4 min-h-0">
          <div className="flex gap-2 mb-4 flex-wrap">
            <button 
              onClick={fetchNicknames} 
              disabled={loading} 
              className="px-3.5 py-2 bg-white-opacity-5 border border-white-opacity-10 rounded-lg text-white cursor-pointer text-0.85em transition-all duration-200 hover:bg-white-opacity-10 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : '🔄 Refresh'}
            </button>
          </div>

          <div className="bg-white-opacity-3 border border-white-opacity-8 rounded-xl p-4 mb-5 text-0.9em text-white-opacity-80">
            <p>
              Nicknames allow ARES to send Telegram messages using friendly names.
              For example, setting nickname "gabu" for a chat ID allows commands like
              <code className="bg-black bg-opacity-30 px-1.5 py-0.5 rounded font-mono text-0.9em text-red-accent">[TELEGRAM_SEND:gabu:Hello!]</code>
            </p>
          </div>

          {loading ? (
            <div className="text-center py-10 text-white-opacity-60 text-0.9em">Loading nicknames...</div>
          ) : (
            <div className="flex flex-col gap-3">
              {nicknames.map((nick) => (
                <div key={nick.nickname} className="flex items-center gap-3 px-4 py-3 bg-white-opacity-3 border border-white-opacity-8 rounded-xl">
                  <div className="font-600 text-white min-w-[100px]">{nick.nickname}</div>
                  <div className="text-white-opacity-40">→</div>
                  <div className="flex-1 font-mono text-white-opacity-70 text-0.9em">{nick.chat_id}</div>
                  <button
                    className="px-2 py-1 bg-[rgba(255,100,100,0.2)] border border-[rgba(255,100,100,0.4)] rounded text-white cursor-pointer text-0.9em transition-all duration-200 hover:bg-[rgba(255,100,100,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={() => handleDeleteNickname(nick.nickname)}
                    disabled={actionLoading}
                    title="Delete nickname"
                  >
                    ✕
                  </button>
                </div>
              ))}
              {nicknames.length === 0 && !loading && (
                <div className="text-center py-10 text-white-opacity-50 text-0.9em">
                  No nicknames configured. Add nicknames from the Telegram Users tab.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeView === 'account-links' && (
        <div className="flex-1 overflow-y-auto overflow-x-hidden py-4 min-h-0">
          <div className="flex gap-2 mb-4 flex-wrap">
            <button 
              onClick={fetchAccountLinks} 
              disabled={loading} 
              className="px-3.5 py-2 bg-white-opacity-5 border border-white-opacity-10 rounded-lg text-white cursor-pointer text-0.85em transition-all duration-200 hover:bg-white-opacity-10 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : '🔄 Refresh'}
            </button>
            <button 
              onClick={() => setShowAccountLinkModal(true)} 
              className="px-3.5 py-2 border-none rounded-lg cursor-pointer text-0.85em font-500 transition-all duration-200 bg-[rgba(0,136,204,0.2)] text-white border border-[rgba(0,136,204,0.4)] hover:bg-[rgba(0,136,204,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={actionLoading}
            >
              + Create Link
            </button>
          </div>

          <div className="bg-white-opacity-3 border border-white-opacity-8 rounded-xl p-4 mb-5 text-0.9em text-white-opacity-80">
            <p>
              Account links connect local user IDs (e.g., Telegram users, manually created IDs) 
              to Auth0 accounts. This enables data merging across linked accounts.
            </p>
          </div>

          {loading ? (
            <div className="text-center py-10 text-white-opacity-60 text-0.9em">Loading account links...</div>
          ) : (
            <div className="flex flex-col gap-3">
              {accountLinks.map((link) => (
                <div 
                  key={link.id} 
                  className={`flex items-center gap-4 p-4 bg-white-opacity-3 border border-white-opacity-8 rounded-2xl transition-all duration-200 ${
                    link.verified 
                      ? 'border-[rgba(0,255,0,0.3)] bg-[rgba(0,255,0,0.05)]' 
                      : 'border-[rgba(255,255,0,0.3)] bg-[rgba(255,255,0,0.05)]'
                  }`}
                >
                  <div className="text-1.5em flex-shrink-0">🔗</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="font-mono text-0.85em text-white-opacity-90" title="Local User ID">
                        📋 {link.local_user_id}
                      </span>
                      <span className="text-white-opacity-40">→</span>
                      <span className="font-mono text-0.85em text-white-opacity-90" title="Auth0 User ID">
                        🔐 {link.auth0_user_id}
                      </span>
                    </div>
                    <div className="flex gap-3 flex-wrap text-0.8em text-white-opacity-60">
                      <span className={link.verified ? 'text-[rgba(0,255,0,0.8)]' : 'text-[rgba(255,255,0,0.8)]'}>
                        {link.verified ? '✓ Verified' : '○ Unverified'}
                      </span>
                      <span>Created: {formatDate(link.created_at)}</span>
                      {link.notes && <span className="text-white-opacity-50 italic" title={link.notes}>📝 {link.notes.substring(0, 30)}{link.notes.length > 30 ? '...' : ''}</span>}
                    </div>
                    <div className="mt-1.5 text-0.75em text-white-opacity-40">
                      <small>Linked by: {link.linked_by}</small>
                    </div>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    {!link.verified && (
                      <button
                        className="px-3.5 py-2 border-none rounded-lg cursor-pointer text-0.85em font-500 transition-all duration-200 bg-[rgba(0,255,0,0.2)] text-white border border-[rgba(0,255,0,0.4)] hover:bg-[rgba(0,255,0,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => handleVerifyAccountLink(link.id)}
                        disabled={actionLoading}
                        title="Verify this link"
                      >
                        ✓ Verify
                      </button>
                    )}
                    <button
                      className="px-3.5 py-2 border-none rounded-lg cursor-pointer text-0.85em font-500 transition-all duration-200 bg-[rgba(255,100,100,0.2)] text-white border border-[rgba(255,100,100,0.4)] hover:bg-[rgba(255,100,100,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
                      onClick={() => handleDeleteAccountLink(link.id)}
                      disabled={actionLoading}
                      title="Delete this link"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
              {accountLinks.length === 0 && !loading && (
                <div className="text-center py-10 text-white-opacity-50 text-0.9em">
                  No account links found. Create a link to connect local user IDs to Auth0 accounts.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Account Link Modal */}
      {showAccountLinkModal && (
        <div className="fixed top-0 left-0 right-0 bottom-0 bg-black bg-opacity-70 flex items-center justify-center z-[1000] backdrop-blur-sm" onClick={() => setShowAccountLinkModal(false)}>
          <div className="bg-[rgba(20,20,25,0.98)] border border-white-opacity-10 rounded-2xl p-6 max-w-[600px] w-[90%] max-h-[90vh] overflow-y-auto shadow-[0_8px_32px_rgba(0,0,0,0.5)]" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-5">
              <h3 className="m-0 text-white text-1.2em">Create Account Link</h3>
              <button className="bg-transparent border-none text-white-opacity-60 cursor-pointer text-1.5em p-0 w-8 h-8 flex items-center justify-center rounded transition-all duration-200 hover:bg-white-opacity-10 hover:text-white" onClick={() => setShowAccountLinkModal(false)}>✕</button>
            </div>
            <div className="text-white-opacity-90">
              <p className="mb-4 leading-relaxed">
                Link a local user ID to an Auth0 account. This allows data from both accounts
                to be merged and accessed together.
              </p>
              
              <div className="mb-4">
                <label htmlFor="local-user-id" className="block mb-1.5 text-white font-500 text-0.9em">Local User ID *</label>
                <input
                  id="local-user-id"
                  type="text"
                  className="w-full px-3.5 py-2.5 bg-white-opacity-5 border border-white-opacity-10 rounded-lg text-white text-0.9em box-border outline-none focus:border-red-border-4 focus:bg-white-opacity-8"
                  placeholder="e.g., telegram_user_123456789, local_user_abc"
                  value={newLocalUserId}
                  onChange={(e) => setNewLocalUserId(e.target.value)}
                  autoFocus
                />
                <small className="block mt-1 text-0.8em text-white-opacity-50">The local user ID to link (required)</small>
              </div>
              
              <div className="mb-4">
                <label htmlFor="auth0-user-id" className="block mb-1.5 text-white font-500 text-0.9em">Auth0 User ID (optional)</label>
                <input
                  id="auth0-user-id"
                  type="text"
                  className="w-full px-3.5 py-2.5 bg-white-opacity-5 border border-white-opacity-10 rounded-lg text-white text-0.9em box-border outline-none focus:border-red-border-4 focus:bg-white-opacity-8"
                  placeholder="e.g., google-oauth2|123456789"
                  value={newAuth0UserId}
                  onChange={(e) => setNewAuth0UserId(e.target.value)}
                />
                <small className="block mt-1 text-0.8em text-white-opacity-50">Leave empty to link to your own Auth0 account</small>
              </div>
              
              <div className="mb-4">
                <label htmlFor="link-notes" className="block mb-1.5 text-white font-500 text-0.9em">Notes (optional)</label>
                <input
                  id="link-notes"
                  type="text"
                  className="w-full px-3.5 py-2.5 bg-white-opacity-5 border border-white-opacity-10 rounded-lg text-white text-0.9em box-border outline-none focus:border-red-border-4 focus:bg-white-opacity-8"
                  placeholder="e.g., Linked from Telegram"
                  value={newLinkNotes}
                  onChange={(e) => setNewLinkNotes(e.target.value)}
                />
              </div>
              
              <div className="flex gap-3 justify-end mt-6">
                <button
                  className="px-5 py-2.5 border-none rounded-lg cursor-pointer text-0.9em font-500 transition-all duration-200 bg-white-opacity-5 text-white border border-white-opacity-10 hover:bg-white-opacity-10"
                  onClick={() => {
                    setShowAccountLinkModal(false)
                    setNewLocalUserId('')
                    setNewAuth0UserId('')
                    setNewLinkNotes('')
                  }}
                >
                  Cancel
                </button>
                <button
                  className="px-5 py-2.5 border-none rounded-lg cursor-pointer text-0.9em font-500 transition-all duration-200 bg-red-bg-6 text-white border border-red-border-4 hover:bg-red-bg-5 disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={handleCreateAccountLink}
                  disabled={!newLocalUserId.trim() || actionLoading}
                >
                  {actionLoading ? 'Creating...' : 'Create Link'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Link Modal */}
      {showLinkModal && selectedTelegramUser && (
        <div className="fixed top-0 left-0 right-0 bottom-0 bg-black bg-opacity-70 flex items-center justify-center z-1000 backdrop-blur-sm" onClick={() => setShowLinkModal(false)}>
          <div className="bg-[rgba(20,20,25,0.98)] border border-white-opacity-10 rounded-2xl p-6 max-w-600px w-90% max-h-[90vh] overflow-y-auto shadow-[0_8px_32px_rgba(0,0,0,0.5)]" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-5">
              <h3 className="m-0 text-white text-1.2em">Link Telegram Account</h3>
              <button className="bg-transparent border-none text-white-opacity-60 cursor-pointer text-1.5em p-0 w-8 h-8 flex items-center justify-center rounded transition-all duration-200 hover:bg-white-opacity-10 hover:text-white" onClick={() => setShowLinkModal(false)}>✕</button>
            </div>
            <div className="text-white-opacity-90">
              <p className="mb-4 leading-relaxed">
                Link <strong>{selectedTelegramUser.title}</strong> (Chat ID: {selectedTelegramUser.chat_id})
                to an Auth0 user. This will share memories between their web and Telegram sessions.
              </p>
              <div className="flex flex-col gap-2 max-h-400px overflow-y-auto mt-4">
                {users.map((user) => (
                  <div
                    key={user.user_id}
                    className="flex items-center gap-3 px-3 py-3 bg-white-opacity-3 border border-white-opacity-8 rounded-lg cursor-pointer transition-all duration-200 hover:bg-white-opacity-8 hover:border-red-border-3"
                    onClick={() => handleLinkTelegram(selectedTelegramUser.chat_id, user.user_id)}
                  >
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-red-bg-6 to-red-bg-5 flex items-center justify-center text-1em flex-shrink-0">
                      {user.picture ? (
                        <img src={user.picture} alt="" className="w-full h-full rounded-full object-cover" />
                      ) : (
                        <div className="text-white font-600">{user.name?.[0] || '?'}</div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-600 text-white mb-0.5">{user.name || user.email}</div>
                      <div className="text-0.85em text-white-opacity-60 font-mono">{user.email}</div>
                    </div>
                    {user.telegram_chat_ids?.length > 0 && (
                      <span className="text-0.75em px-2 py-1 bg-[rgba(0,255,0,0.2)] border border-[rgba(0,255,0,0.4)] rounded text-[rgba(0,255,0,0.9)]">
                        {user.telegram_chat_ids.length} linked
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Nickname Modal */}
      {showNicknameModal && selectedTelegramUser && (
        <div className="fixed top-0 left-0 right-0 bottom-0 bg-black bg-opacity-70 flex items-center justify-center z-[1000] backdrop-blur-sm" onClick={() => setShowNicknameModal(false)}>
          <div className="bg-[rgba(20,20,25,0.98)] border border-white-opacity-10 rounded-2xl p-6 max-w-[600px] w-[90%] max-h-[90vh] overflow-y-auto shadow-[0_8px_32px_rgba(0,0,0,0.5)]" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-5">
              <h3 className="m-0 text-white text-1.2em">Add Nickname</h3>
              <button className="bg-transparent border-none text-white-opacity-60 cursor-pointer text-1.5em p-0 w-8 h-8 flex items-center justify-center rounded transition-all duration-200 hover:bg-white-opacity-10 hover:text-white" onClick={() => setShowNicknameModal(false)}>✕</button>
            </div>
            <div className="text-white-opacity-90">
              <p className="mb-4 leading-relaxed">
                Add a nickname for <strong>{selectedTelegramUser.title}</strong> (Chat ID: {selectedTelegramUser.chat_id})
              </p>
              <input
                type="text"
                className="w-full px-3.5 py-2.5 bg-white-opacity-5 border border-white-opacity-10 rounded-lg text-white text-0.9em box-border mt-3 outline-none focus:border-red-border-4 focus:bg-white-opacity-8"
                placeholder="Enter nickname (e.g., gabu)"
                value={newNickname}
                onChange={(e) => setNewNickname(e.target.value.toLowerCase().replace(/\s/g, ''))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && newNickname) {
                    handleAddNickname(selectedTelegramUser.chat_id, newNickname)
                  }
                }}
                autoFocus
              />
              <div className="flex gap-3 justify-end mt-6">
                <button
                  className="px-5 py-2.5 border-none rounded-lg cursor-pointer text-0.9em font-500 transition-all duration-200 bg-white-opacity-5 text-white border border-white-opacity-10 hover:bg-white-opacity-10"
                  onClick={() => setShowNicknameModal(false)}
                >
                  Cancel
                </button>
                <button
                  className="px-5 py-2.5 border-none rounded-lg cursor-pointer text-0.9em font-500 transition-all duration-200 bg-red-bg-6 text-white border border-red-border-4 hover:bg-red-bg-5 disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={() => handleAddNickname(selectedTelegramUser.chat_id, newNickname)}
                  disabled={!newNickname || actionLoading}
                >
                  {actionLoading ? 'Adding...' : 'Add Nickname'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default UserManagerPanel

