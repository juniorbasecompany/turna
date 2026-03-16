import { NextRequest, NextResponse } from 'next/server'
import { backendFetch, errorResponse, requireToken } from '@/lib/backend-fetch'

/**
 * DELETE /api/file/demand
 *
 * Exclui demandas vinculadas a uma lista de arquivos.
 */
export async function DELETE(request: NextRequest) {
    const auth = requireToken(request)
    if (!auth.ok) {
        return auth.error
    }

    const body = await request.json().catch(() => null)
    const rawFileIdList = Array.isArray(body?.file_id_list) ? body.file_id_list : null

    if (!rawFileIdList || rawFileIdList.length === 0) {
        return errorResponse('file_id_list é obrigatório', 400)
    }

    const fileIdList = rawFileIdList
        .map((value) => Number(value))
        .filter((value) => Number.isInteger(value) && value > 0)

    if (fileIdList.length !== rawFileIdList.length) {
        return errorResponse('file_id_list deve conter apenas IDs válidos', 400)
    }

    const result = await backendFetch('/file/demand', {
        method: 'DELETE',
        token: auth.token,
        body: { file_id_list: fileIdList },
    })

    if (!result.ok) {
        return result.error
    }

    return new NextResponse(null, { status: 204 })
}
