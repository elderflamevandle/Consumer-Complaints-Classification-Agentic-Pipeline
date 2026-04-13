import type { Metadata } from 'next'
import { Instrument_Serif, DM_Sans, DM_Mono } from 'next/font/google'
import './globals.css'

/* ── Typefaces ───────────────────────────────────────────────────────────── */
const serif = Instrument_Serif({
  weight:   ['400'],
  style:    ['normal', 'italic'],
  subsets:  ['latin'],
  variable: '--font-serif',
  display:  'swap',
})

const sans = DM_Sans({
  subsets:  ['latin'],
  variable: '--font-sans',
  display:  'swap',
})

const mono = DM_Mono({
  weight:   ['400', '500'],
  subsets:  ['latin'],
  variable: '--font-mono',
  display:  'swap',
})

/* ── Metadata ────────────────────────────────────────────────────────────── */
export const metadata: Metadata = {
  title:       'FinComplaint AI',
  description: 'AI-powered financial complaint triage and remediation platform',
  themeColor:  '#07071A',
}

/* ── Root layout ─────────────────────────────────────────────────────────── */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`h-full dark ${serif.variable} ${sans.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      <body className="h-full bg-background text-foreground font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
