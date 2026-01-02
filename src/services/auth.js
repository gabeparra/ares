/**
 * Secure authentication token storage
 *
 * SECURITY: Stores tokens in memory only, not in window object or localStorage.
 * This prevents XSS attacks from accessing tokens via window.authToken.
 */

// Private variables (not accessible from window object or browser console)
let authToken = null;
let refreshTokenCallback = null;

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
  return authToken;
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
