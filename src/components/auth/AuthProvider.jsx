import React, { useEffect, useState } from 'react'
import { Auth0Provider, useAuth0 } from '@auth0/auth0-react'
import { getAuthConfig } from '../../services/auth'

function Auth0ProviderWrapper({ children }) {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAuthConfig().then((authConfig) => {
      setConfig(authConfig)
      setLoading(false)
    })
  }, [])

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div>Loading authentication...</div>
      </div>
    )
  }

  if (!config || !config.domain || !config.clientId) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '20px',
        padding: '20px',
        textAlign: 'center'
      }}>
        <h2>Auth0 Not Configured</h2>
        <p>Please configure AUTH0_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_AUDIENCE in your .env file</p>
        <p style={{ fontSize: '0.9em', color: '#666' }}>
          The application will work without authentication, but API calls may fail.
        </p>
        {children}
      </div>
    )
  }

  return (
    <Auth0Provider
      domain={config.domain}
      clientId={config.clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: config.audience,
      }}
      useRefreshTokens={true}
      cacheLocation="localstorage"
    >
      {children}
    </Auth0Provider>
  )
}

export default Auth0ProviderWrapper

