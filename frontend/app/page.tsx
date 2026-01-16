'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    // Verifica se o usuário está autenticado
    const checkAuth = async () => {
      try {
        const res = await fetch('/api/auth/me', {
          credentials: 'include',
        })

        if (res.ok) {
          // Usuário autenticado - mostra dashboard (ou redireciona para dashboard quando implementar)
          setChecking(false)
          // Por enquanto, apenas não redireciona - a dashboard será implementada depois
          return
        } else {
          // Não autenticado - redireciona para login
          router.push('/login')
        }
      } catch (error) {
        // Erro na verificação - assume não autenticado e redireciona
        router.push('/login')
      } finally {
        setChecking(false)
      }
    }

    checkAuth()
  }, [router])

  if (checking) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">Turna</h1>
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </main>
    )
  }

  // Dashboard - será implementado depois
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Turna</h1>
        <p className="mt-4 text-gray-600">Dashboard - Em desenvolvimento</p>
      </div>
    </main>
  )
}
