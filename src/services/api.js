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
 * Make an authenticated API request
 */
export async function apiRequest(url, options = {}) {
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
  
  if (response.status === 401) {
    // Token might be expired, try to refresh
    // For now, just throw an error
    throw new Error('Authentication required')
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

