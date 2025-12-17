import React from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import LoginButton from './LoginButton'

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth0()

  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '50vh',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div>Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '50vh',
        flexDirection: 'column',
        gap: '20px',
        padding: '20px',
        textAlign: 'center'
      }}>
        <h2>Authentication Required</h2>
        <p>Please log in to access ARES</p>
        <LoginButton />
      </div>
    )
  }

  return children
}

export default ProtectedRoute

