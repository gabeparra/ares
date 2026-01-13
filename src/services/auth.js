/**
 * Secure authentication token storage
 *
 * SECURITY: Stores tokens in memory only, not in window object or localStorage.
 * This prevents XSS attacks from accessing tokens via window.authToken.
 * 
 * DEV MODE: Also supports dev admin tokens stored in localStorage for testing.
 */

// Private variables (not accessible from window object or browser console)
let authToken = null;
let refreshTokenCallback = null;
let isDevAdmin = false;

/**
 * Check if dev admin token exists and is valid
 */
export const checkDevAdminToken = () => {
  const token = localStorage.getItem('dev_admin_token');
  if (token) {
    try {
      // Decode JWT to check expiration (without verification - backend will verify)
      const parts = token.split('.');
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]));
        if (payload.exp && payload.exp > Date.now() / 1000) {
          return { token, user: JSON.parse(localStorage.getItem('dev_admin_user') || '{}') };
        }
      }
    } catch (e) {
      console.warn('Invalid dev admin token:', e);
    }
    // Clear invalid token
    localStorage.removeItem('dev_admin_token');
    localStorage.removeItem('dev_admin_user');
  }
  return null;
};

/**
 * Set the authentication token
 * @param {string} token - The JWT token
 */
export const setAuthToken = (token) => {
  authToken = token;
};

/**
 * Get the current authentication token
 * @returns {string|null} The current token or null
 */
export const getAuthToken = () => {
  // First check for dev admin token
  const devAuth = checkDevAdminToken();
  if (devAuth) {
    return devAuth.token;
  }
  return authToken;
};

/**
 * Check if currently using dev admin authentication
 */
export const isDevAdminAuth = () => {
  return checkDevAdminToken() !== null;
};

/**
 * Clear dev admin authentication
 */
export const clearDevAdminAuth = () => {
  localStorage.removeItem('dev_admin_token');
  localStorage.removeItem('dev_admin_user');
};

/**
 * Clear the authentication token
 */
export const clearAuthToken = () => {
  authToken = null;
};

/**
 * Set the refresh token callback function
 * @param {Function} callback - Function to call when token needs refresh
 */
export const setRefreshTokenCallback = (callback) => {
  refreshTokenCallback = callback;
};

/**
 * Refresh the authentication token
 * @returns {Promise<string>} The refreshed token
 */
export const refreshAuthToken = async () => {
  if (!refreshTokenCallback) {
    throw new Error('Refresh token callback not set');
  }

  try {
    const newToken = await refreshTokenCallback();
    setAuthToken(newToken);
    return newToken;
  } catch (error) {
    clearAuthToken();
    throw error;
  }
};

/**
 * Initialize auth module (for cleanup)
 */
export const clearAuthModule = () => {
  authToken = null;
  refreshTokenCallback = null;
};
