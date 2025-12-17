/**
 * Auth0 service for fetching configuration and managing authentication
 */

let authConfig = null

export async function getAuthConfig() {
  if (authConfig) {
    return authConfig
  }

  try {
    const response = await fetch('/api/v1/auth/config')
    if (!response.ok) {
      throw new Error('Failed to fetch auth config')
    }
    authConfig = await response.json()
    return authConfig
  } catch (error) {
    console.error('Error fetching auth config:', error)
    return null
  }
}

export async function getUserInfo(token) {
  try {
    const response = await fetch('/api/v1/auth/user', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })
    
    if (!response.ok) {
      throw new Error('Failed to fetch user info')
    }
    
    return await response.json()
  } catch (error) {
    console.error('Error fetching user info:', error)
    return null
  }
}

