'use client'

interface SaveButtonProps {
    /**
     * Se true, mostra o botão. Se false, o botão não é renderizado.
     */
    show: boolean
    /**
     * Função chamada ao clicar no botão.
     */
    onClick: () => void
    /**
     * Se true, desabilita o botão.
     */
    disabled?: boolean
    /**
     * Texto do botão quando não está processando.
     */
    label?: string
    /**
     * Texto do botão quando está processando.
     */
    processingLabel?: string
    /**
     * Se true, mostra o texto de processamento.
     */
    processing?: boolean
}

/**
 * Botão "Salvar" fixo no canto inferior direito da tela.
 *
 * Usado para ações de salvar/excluir que devem estar sempre acessíveis
 * enquanto o usuário rola a página.
 *
 * @example
 * ```tsx
 * <SaveButton
 *   show={selectedItems.size > 0}
 *   onClick={handleSave}
 *   disabled={saving}
 *   processing={saving}
 * />
 * ```
 */
export function SaveButton({
    show,
    onClick,
    disabled = false,
    label = 'Salvar',
    processingLabel = 'Salvando...',
    processing = false,
}: SaveButtonProps) {
    if (!show) {
        return null
    }

    return (
        <div className="fixed bottom-6 right-6 z-50">
            <button
                onClick={onClick}
                disabled={disabled}
                className="px-6 py-3 text-base font-medium text-white bg-blue-600 border border-blue-700 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-lg hover:shadow-xl"
            >
                {processing ? processingLabel : label}
            </button>
        </div>
    )
}
