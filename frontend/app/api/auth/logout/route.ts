import { NextResponse } from 'next/server'

/**
 * Handler Next.js para logout
 *
 * Remove cookie de autenticação.
 */
export async function POST() {
    const response = NextResponse.json({ success: true })

    // Remover cookie
    response.cookies.delete('access_token')

    return response
}
