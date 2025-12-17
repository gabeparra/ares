import React from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import './Auth.css'

function LogoutButton() {
  const { logout, isAuthenticated, user } = useAuth0()

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="auth-user-menu">
      <div className="auth-user-info">
        {user?.picture && (
          <img 
            src={user.picture} 
            alt={user.name || user.email} 
            className="auth-user-avatar"
          />
        )}
        <span className="auth-user-name">
          {user?.name || user?.email || 'User'}
        </span>
      </div>
      <button 
        className="auth-button logout-button"
        onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
      >
        Log Out
      </button>
    </div>
  )
}

export default LogoutButton

