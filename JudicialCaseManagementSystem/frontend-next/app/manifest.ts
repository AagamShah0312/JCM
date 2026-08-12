import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'JCM — Judicial Case Management',
    short_name: 'JCM',
    description: 'Enterprise judicial case management platform',
    start_url: '/',
    display: 'standalone',
    background_color: '#f1f5f9',
    theme_color: '#1f43f0',
    icons: [
      {
        src: '/icon.svg',
        sizes: 'any',
        type: 'image/svg+xml',
      },
    ],
  };
}
