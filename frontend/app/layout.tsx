import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'

export const metadata: Metadata = {
    title: 'Turna',
    description: 'Sistema de gestão de escalas',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="pt-BR">
            <head>
                {/* Otimizações de DNS e conexão para o Google - reduz latência no carregamento do script */}
                {/* Essas tags iniciam a conexão com o Google antes mesmo do script ser solicitado */}
                <link rel="dns-prefetch" href="https://accounts.google.com" />
                <link rel="preconnect" href="https://accounts.google.com" crossOrigin="anonymous" />
            </head>
            <body>
                <Providers>{children}</Providers>
            </body>
        </html>
    )
}
