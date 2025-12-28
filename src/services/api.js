/**
 * API service with authentication support
 */

/**
 * Get the current auth token
 */
function getAuthToken() {
  return window.authToken || null
}

/**
 * Refresh the auth token
 */
async function refreshAuthToken() {
  if (window.refreshAuthToken && typeof window.refreshAuthToken === 'function') {
    try {
      return await window.refreshAuthToken()
    } catch (err) {
      console.error('Failed to refresh token:', err)
      throw new Error('Token refresh failed')
    }
  }
  throw new Error('Token refresh function not available')
}

/**
 * Make an authenticated API request with automatic token refresh on 401
 */
export async function apiRequest(url, options = {}, retryCount = 0) {
  const maxRetries = 1 // Only retry once after token refresh
  
  const token = getAuthToken()
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  })
  
  if (response.status === 401 && retryCount < maxRetries) {
    // Token might be expired, try to refresh and retry
    try {
      const newToken = await refreshAuthToken()
      if (newToken) {
        // Retry the request with the new token
        const retryHeaders = {
          ...headers,
          'Authorization': `Bearer ${newToken}`
        }
        const retryResponse = await fetch(url, {
          ...options,
          headers: retryHeaders,
        })
        
        // If retry also fails with 401, throw error
        if (retryResponse.status === 401) {
          throw new Error('Authentication required - please log in again')
        }
        
        return retryResponse
      }
    } catch (refreshError) {
      console.error('Token refresh failed:', refreshError)
      // If refresh fails, throw authentication error
      throw new Error('Authentication required - please log in again')
    }
  }
  
  if (response.status === 401) {
    throw new Error('Authentication required - please log in again')
  }
  
  return response
}

/**
 * Make a POST request with authentication
 */
export async function apiPost(url, data, options = {}) {
  return apiRequest(url, {
    method: 'POST',
    body: JSON.stringify(data),
    ...options,
  })
}

/**
 * Make a GET request with authentication
 */
export async function apiGet(url, options = {}) {
  return apiRequest(url, {
    method: 'GET',
    ...options,
  })
}

/**
 * Make a PATCH request with authentication
 */
export async function apiPatch(url, data, options = {}) {
  return apiRequest(url, {
    method: 'PATCH',
    body: JSON.stringify(data),
    ...options,
  })
}

/**
 * Make a DELETE request with authentication
 */
export async function apiDelete(url, options = {}) {
  return apiRequest(url, {
    method: 'DELETE',
    ...options,
  })
}

