// Auth management module

// Configuration
const API_BASE_URL = 'http://localhost:8000';
const TOKEN_REFRESH_BUFFER = 5 * 60 * 1000; // 5 minutes in milliseconds

// Initialize our refresh timeout
let tokenRefreshTimeout = null;

console.log('📋 Auth module initialized with API base URL:', API_BASE_URL);
console.log('⏱️ Token refresh buffer set to:', TOKEN_REFRESH_BUFFER / 1000, 'seconds');

/**
 * Check if user is authenticated
 * @returns {boolean} True if user has a valid authentication token
 */
export function isAuthenticated() {
  console.log('🔍 Checking authentication status...');
  
  const token = localStorage.getItem('soot_auth_token');
  const expiry = localStorage.getItem('soot_token_expiry');
  
  if (!token) {
    console.log('⚠️ No auth token found in localStorage');
    return false;
  }
  
  if (!expiry) {
    console.log('⚠️ No token expiry found in localStorage');
    return false;
  }
  
  // Check if token is still valid
  const now = new Date().getTime();
  const expiryTime = parseInt(expiry, 10);
  const timeRemaining = expiryTime - now;
  
  const isValid = now < expiryTime;
  
  if (isValid) {
    console.log(`✅ Token is valid, expires in ${Math.round(timeRemaining/1000)} seconds`);
  } else {
    console.log(`❌ Token has expired ${Math.round(Math.abs(timeRemaining)/1000)} seconds ago`);
  }
  
  return isValid;
}

/**
 * Get the current authentication token
 * @returns {string|null} The current auth token or null if not authenticated
 */
export function getAuthToken() {
  console.log('🔑 Getting auth token...');
  
  if (!isAuthenticated()) {
    console.log('❌ Cannot get token: not authenticated');
    return null;
  }
  
  const token = localStorage.getItem('soot_auth_token');
  console.log('✅ Retrieved auth token:', token ? `${token.substring(0, 10)}...` : 'null');
  return token;
}

/**
 * Redirect to login page if not authenticated
 */
export function requireAuth() {
  console.log('🛡️ Requiring authentication...');
  
  if (!isAuthenticated()) {
    console.log('🔒 Authentication required, redirecting to login');
    window.location.href = 'login.html';
    return false;
  }
  
  console.log('✅ User is authenticated');
  
  // Set up token refresh
  console.log('🔄 Setting up token refresh mechanism');
  setupTokenRefresh();
  return true;
}

/**
 * Log out the current user
 */
export function logout() {
  console.log('🚪 Logging out user...');
  
  // Clear all auth data
  localStorage.removeItem('soot_auth_token');
  localStorage.removeItem('soot_token_expiry');
  localStorage.removeItem('soot_refresh_token');
  
  console.log('🗑️ Cleared all authentication data from localStorage');
  
  // Clear any refresh timeout
  if (tokenRefreshTimeout) {
    clearTimeout(tokenRefreshTimeout);
    tokenRefreshTimeout = null;
    console.log('⏱️ Cleared token refresh timeout');
  }
  
  console.log('🔄 Redirecting to login page');
  // Redirect to login page
  window.location.href = 'login.html';
}

/**
 * Set up automatic token refresh
 */
function setupTokenRefresh() {
  console.log('⚙️ Setting up token refresh...');
  
  // Clear any existing timeout
  if (tokenRefreshTimeout) {
    clearTimeout(tokenRefreshTimeout);
    console.log('⏱️ Cleared existing token refresh timeout');
  }
  
  const expiry = localStorage.getItem('soot_token_expiry');
  if (!expiry) {
    console.log('⚠️ No token expiry found, cannot setup refresh');
    return;
  }
  
  const expiryTime = parseInt(expiry, 10);
  const now = new Date().getTime();
  
  // Calculate time until refresh (expiry time minus buffer)
  let refreshIn = expiryTime - now - TOKEN_REFRESH_BUFFER;
  
  // If token is already expired or will expire soon, refresh immediately
  if (refreshIn < 0) {
    console.log('⚠️ Token will expire soon or has already expired, scheduling immediate refresh');
    refreshIn = 0;
  }
  
  const refreshDate = new Date(now + refreshIn);
  console.log(`🔄 Token refresh scheduled at: ${refreshDate.toLocaleTimeString()}`);
  console.log(`🔄 Token refresh scheduled in ${Math.round(refreshIn/1000)} seconds`);
  
  // Set timeout to refresh token
  tokenRefreshTimeout = setTimeout(() => {
    console.log('⏰ Token refresh timeout triggered');
    refreshToken();
  }, refreshIn);
  
  console.log('✅ Token refresh setup complete');
}

/**
 * Refresh the authentication token
 * @returns {Promise<boolean>} True if refresh was successful
 */
async function refreshToken() {
  console.log('🔄 Starting token refresh process...');
  
  const refreshToken = localStorage.getItem('soot_refresh_token');
  
  if (!refreshToken) {
    console.log('❌ No refresh token available in localStorage');
    console.log('🚪 Forcing logout due to missing refresh token');
    logout();
    return false;
  }
  
  try {
    console.log('🔄 Refreshing authentication token...');
    console.log(`📡 Sending refresh request to: ${API_BASE_URL}/api/auth/refresh`);
    
    const requestStartTime = new Date().getTime();
    
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        refresh_token: refreshToken
      })
    });
    
    const requestDuration = new Date().getTime() - requestStartTime;
    console.log(`⏱️ Refresh request took ${requestDuration}ms`);
    
    console.log('📥 Received response with status:', response.status);
    
    if (!response.ok) {
      console.error(`❌ HTTP error during token refresh: ${response.status} ${response.statusText}`);
      throw new Error(`HTTP error ${response.status}`);
    }
    
    const data = await response.json();
    console.log('📦 Parsed response data:', { 
      has_access_token: !!data.access_token,
      has_refresh_token: !!data.refresh_token,
      expires_in: data.expires_in
    });
    
    if (data.access_token) {
      // Update token in localStorage
      localStorage.setItem('soot_auth_token', data.access_token);
      console.log('💾 Saved new access token to localStorage');
      
      // Store new refresh token if provided
      if (data.refresh_token) {
        localStorage.setItem('soot_refresh_token', data.refresh_token);
        console.log('💾 Saved new refresh token to localStorage');
      }
      
      // Calculate and store expiry time
      const expiresInMs = data.expires_in * 1000;
      const expiryTime = new Date().getTime() + expiresInMs;
      localStorage.setItem('soot_token_expiry', expiryTime);
      
      const expiryDate = new Date(expiryTime);
      console.log(`⏱️ New token expires at: ${expiryDate.toLocaleString()}`);
      console.log(`⏱️ New token valid for: ${Math.round(expiresInMs/1000)} seconds`);
      
      console.log('✅ Token refresh successful');
      
      // Set up next refresh
      console.log('🔄 Setting up next token refresh');
      setupTokenRefresh();
      return true;
    } else {
      console.error('❌ No access token in refresh response');
      throw new Error('No access token in response');
    }
  } catch (error) {
    console.error('❌ Failed to refresh token:', error);
    console.log('🔍 Error details:', error.message);
    
    // If refresh fails, clear token and redirect to login
    console.log('🚪 Logging out due to token refresh failure');
    logout();
    return false;
  }
}

/**
 * Add auth headers to fetch requests
 * @param {RequestInfo} input - The resource URL
 * @param {RequestInit} [init] - Custom settings for the request
 * @returns {Promise<Response>} Fetch response
 */
export async function authenticatedFetch(input, init = {}) {
  console.log(`📡 Authenticated fetch request to: ${input}`);
  
  // Ensure we have valid auth
  if (!requireAuth()) {
    console.error('❌ Authenticated fetch failed: not authenticated');
    throw new Error('Not authenticated');
  }
  
  // Get the current auth token
  const token = getAuthToken();
  console.log('🔑 Using auth token:', token ? `${token.substring(0, 10)}...` : 'null');
  
  // Create headers object if it doesn't exist
  const headers = init.headers || {};
  console.log('📋 Original request headers:', headers);
  
  // Add authorization header
  const authHeaders = {
    ...headers,
    'Authorization': `Bearer ${token}`
  };
  
  console.log('📋 Enhanced headers with auth token');
  
  // Make the request with auth header
  console.log('📤 Sending authenticated request...');
  const requestStartTime = new Date().getTime();
  
  const response = await fetch(input, {
    ...init,
    headers: authHeaders
  });
  
  const requestDuration = new Date().getTime() - requestStartTime;
  console.log(`⏱️ Request took ${requestDuration}ms`);
  
  console.log(`📥 Received response with status: ${response.status} ${response.statusText}`);
  
  // Check if token was rejected
  if (response.status === 401) {
    console.log('🔒 Received 401 Unauthorized, token might be invalid or expired');
    
    // Try to refresh token
    console.log('🔄 Attempting to refresh token and retry request');
    const refreshed = await refreshToken();
    
    if (refreshed) {
      // Retry the request with new token
      console.log('🔄 Token refreshed successfully, retrying original request');
      
      const newToken = getAuthToken();
      console.log('🔑 Using new auth token:', newToken ? `${newToken.substring(0, 10)}...` : 'null');
      
      const newHeaders = {
        ...headers,
        'Authorization': `Bearer ${newToken}`
      };
      
      console.log('📤 Retrying authenticated request with new token...');
      const retryStartTime = new Date().getTime();
      
      const retryResponse = await fetch(input, {
        ...init,
        headers: newHeaders
      });
      
      const retryDuration = new Date().getTime() - retryStartTime;
      console.log(`⏱️ Retry request took ${retryDuration}ms`);
      console.log(`📥 Retry response status: ${retryResponse.status} ${retryResponse.statusText}`);
      
      return retryResponse;
    } else {
      // If refresh failed, redirect to login
      console.log('❌ Token refresh failed, cannot retry request');
      console.log('🚪 Logging out due to authentication failure');
      logout();
      throw new Error('Authentication failed');
    }
  }
  
  console.log('✅ Authenticated request completed successfully');
  return response;
}

/**
 * Log the current authentication state
 */
export function logAuthState() {
  console.log('📊 ----- AUTH STATE REPORT -----');
  
  const token = localStorage.getItem('soot_auth_token');
  const expiry = localStorage.getItem('soot_token_expiry');
  const refreshToken = localStorage.getItem('soot_refresh_token');
  
  console.log('🔑 Has auth token:', !!token);
  console.log('⏱️ Has expiry time:', !!expiry);
  console.log('🔁 Has refresh token:', !!refreshToken);
  
  if (token && expiry) {
    const now = new Date().getTime();
    const expiryTime = parseInt(expiry, 10);
    const timeRemaining = expiryTime - now;
    
    const expiryDate = new Date(expiryTime);
    console.log(`⏱️ Token expires at: ${expiryDate.toLocaleString()}`);
    console.log(`⏱️ Time remaining: ${Math.round(timeRemaining/1000)} seconds`);
    console.log(`🔒 Authentication status: ${isAuthenticated() ? 'Authenticated' : 'Not authenticated'}`);
  } else {
    console.log('🔒 Authentication status: Not authenticated');
  }
  
  console.log('📊 ----- END AUTH STATE REPORT -----');
}

// Initialize auth check when this module is imported
if (typeof window !== 'undefined') {
  // Only run in browser environment
  console.log('🔄 Auth module running in browser environment, checking initial auth state...');
  
  if (isAuthenticated()) {
    console.log('✅ User is authenticated on module load, setting up token refresh');
    setupTokenRefresh();
  } else {
    console.log('ℹ️ User is not authenticated on module load');
  }
  
  // Log detailed auth state on load
  logAuthState();
}