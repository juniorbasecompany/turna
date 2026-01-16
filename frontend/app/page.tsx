'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

/**
 * Página raiz: redireciona para /dashboard se autenticado, ou /login se não autenticado
 */
export default function Home() {
  const router = useRouter()

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch('/api/auth/me', {
          credentials: 'include',
        })

        if (res.ok) {
          // Autenticado - redirecionar para dashboard
          router.push('/dashboard')
        } else {
          // Não autenticado - redirecionar para login
          router.push('/login')
        }
      } catch (error) {
        // Erro de rede - redirecionar para login por segurança
        router.push('/login')
      }
    }

    checkAuth()
  }, [router])

  // Mostrar loading enquanto redireciona
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Turna</h1>
        <p className="mt-4 text-gray-600">Carregando...</p>
      </div>
    </main>
  )
}
