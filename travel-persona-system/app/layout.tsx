import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Geist_Mono, Gowun_Batang, Noto_Sans_KR } from 'next/font/google'
import './globals.css'
import { SurveyProvider } from '@/lib/survey/store'
import { AuthProvider } from '@/lib/auth/store'

const notoKr = Noto_Sans_KR({
  variable: '--font-noto-kr',
  subsets: ['latin'],
  weight: ['300', '400', '500', '700', '900'],
})
const gowun = Gowun_Batang({
  variable: '--font-gowun',
  subsets: ['latin'],
  weight: ['400', '700'],
})
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'TRAVEL ANIMAL 16 — 여행 성향 진단',
  description:
    '40문항으로 알아보는 나의 여행 동물 유형. 16가지 여행 페르소나와 4개 축으로 당신의 여행 스타일을 진단하고, 모든 문항을 직접 수정할 수 있어요.',
  generator: 'v0.app',
}

export const viewport: Viewport = {
  themeColor: '#f3ead9',
  colorScheme: 'light',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="ko"
      className={`light ${notoKr.variable} ${gowun.variable} ${geistMono.variable} bg-background`}
    >
      <body className="font-sans antialiased">
        <AuthProvider>
          <SurveyProvider>{children}</SurveyProvider>
        </AuthProvider>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
