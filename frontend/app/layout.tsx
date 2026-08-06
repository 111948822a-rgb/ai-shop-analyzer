import type { Metadata } from 'next'
import './globals.css'
import { I18nProvider } from '@/lib/i18n/context'

export const metadata: Metadata = {
  title: 'AI Shop Analyzer',
  description: 'Cross-border e-commerce shop analytics & influencer evaluation platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <I18nProvider>
          {children}
        </I18nProvider>
      </body>
    </html>
  )
}
