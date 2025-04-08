// CORS Anywhere is a proxy that adds CORS headers to a request
const CORS_PROXY = 'https://corsproxy.io/?';

// Function to create a proxied URL
export function createProxiedUrl(url: string): string {
  return `${CORS_PROXY}${encodeURIComponent(url)}`;
}