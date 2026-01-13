/**
 * API service with authentication support
 *
 * SECURITY: Uses secure in-memory token storage instead of window object
 */

import { getAuthToken, refreshAuthToken } from './auth.js';

/**
 * Trigger re-login by dispatching a custom event
 * This allows App.jsx to listen for auth failures and trigger loginWithRedirect
 */
function triggerReLogin() {
  // Dispatch a custom event that App.jsx can listen to
  window.dispatchEvent(new CustomEvent('ares:auth-required', {
    detail: { reason: 'Token refresh failed' }
  }));
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
      // Trigger re-login event before throwing error
      triggerReLogin()
      // If refresh fails, throw authentication error
      throw new Error('Authentication required - please log in again')
    }
  }
  
  if (response.status === 401) {
    // Trigger re-login event for 401 errors
    triggerReLogin()
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

/**
 * Safely parse a response as JSON, handling HTML error pages gracefully
 * @param {Response} response - The fetch Response object
 * @returns {Promise<{data: any, error: string|null}>} - Parsed data or error message
 */
export async function safeJsonParse(response) {
  try {
    const contentType = response.headers.get('content-type') || ''
    
    // Check if response is HTML (error page)
    if (contentType.includes('text/html')) {
      const htmlText = await response.text()
      // Extract a meaningful error message from HTML if possible
      const titleMatch = htmlText.match(/<title>([^<]+)<\/title>/i)
      const title = titleMatch ? titleMatch[1].trim() : null
      
      // Common HTML error patterns
      if (htmlText.includes('502 Bad Gateway') || htmlText.includes('502')) {
        return { data: null, error: 'Backend service unavailable (502 Bad Gateway)' }
      }
      if (htmlText.includes('503 Service Unavailable') || htmlText.includes('503')) {
        return { data: null, error: 'Service temporarily unavailable (503)' }
      }
      if (htmlText.includes('504 Gateway Timeout') || htmlText.includes('504')) {
        return { data: null, error: 'Request timeout - server took too long to respond (504)' }
      }
      if (htmlText.includes('500 Internal Server Error') || htmlText.includes('500')) {
        return { data: null, error: 'Server error (500)' }
      }
      
      return { 
        data: null, 
        error: title || `Server returned HTML instead of JSON (HTTP ${response.status})` 
      }
    }
    
    // Try to parse as JSON
    const text = await response.text()
    if (!text || text.trim() === '') {
      return { data: null, error: null }
    }
    
    try {
      const data = JSON.parse(text)
      return { data, error: null }
    } catch (parseError) {
      // JSON parsing failed - check if it looks like HTML
      if (text.trim().startsWith('<')) {
        return { 
          data: null, 
          error: `Server returned HTML instead of JSON (HTTP ${response.status})` 
        }
      }
      return { 
        data: null, 
        error: `Invalid response format: ${text.substring(0, 100)}...` 
      }
    }
  } catch (err) {
    return { data: null, error: `Failed to read response: ${err.message}` }
  }
}

