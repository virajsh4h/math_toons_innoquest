/** @type {import('next').NextConfig} */
const nextConfig = {
    // This allows the use of environment variables at runtime in the browser.
    env: {
      // Default to the local backend URL as requested by the user
      NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000',
    },
};

export default nextConfig;
