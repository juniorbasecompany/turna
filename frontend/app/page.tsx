'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // Redireciona para a página de login
    router.push('/login')
  }, [router])

  // Mostra um loading enquanto redireciona
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Turna</h1>
        <p className="mt-4 text-gray-600">Redirecionando...</p>
      </div>
    </main>
  )
}
