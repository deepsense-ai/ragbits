import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { RagbitsClient } from '@ragbits/api-client'
import type { ClientConfig, RagbitsContextValue } from './index'

const RagbitsContext = createContext<RagbitsContextValue | null>(null)

export interface RagbitsContextProviderProps extends ClientConfig {
    children: ReactNode
}

export function RagbitsContextProvider({
    children,
    ...config
}: RagbitsContextProviderProps) {
    const client = useMemo(() => new RagbitsClient(config), [config])

    const contextValue = useMemo(
        () => ({
            client,
        }),
        [client]
    )

    return (
        <RagbitsContext.Provider value={contextValue}>
            {children}
        </RagbitsContext.Provider>
    )
}

export function useRagbitsContext() {
    const context = useContext(RagbitsContext)
    if (!context) {
        throw new Error(
            'useRagbitsContext must be used within a RagbitsProvider'
        )
    }
    return context
}
