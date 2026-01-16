import Script from 'next/script'

export default function LoginLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <>
            {/* Carrega o script do Google o mais cedo possível, antes da interatividade */}
            {/* Isso garante que o script comece a carregar antes mesmo da hidratação do React */}
            {/* As tags de prefetch/preconnect estão no root layout para otimizar a conexão */}
            <Script
                src="https://accounts.google.com/gsi/client"
                strategy="beforeInteractive"
            />
            {children}
        </>
    )
}
