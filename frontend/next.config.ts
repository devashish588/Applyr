import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow images from external sources if needed
  images: {
    unoptimized: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
