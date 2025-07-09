import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RagbitsContextProvider, useRagbitsContext } from '../src'

function TestComponent() {
    const { client } = useRagbitsContext()
    return (
        <div data-testid="client-available">
            {client
                ? `Client available with baseUrl: ${client.getBaseUrl()}`
                : 'No client'}
        </div>
    )
}

function TestComponentOutsideProvider() {
    try {
        useRagbitsContext()
        return <div>No error</div>
    } catch (error) {
        return <div data-testid="error">{(error as Error).message}</div>
    }
}

describe('RagbitsProvider', () => {
    it('should provide client context to children', () => {
        render(
            <RagbitsContextProvider baseUrl="http://127.0.0.1:8000">
                <TestComponent />
            </RagbitsContextProvider>
        )

        expect(screen.getByTestId('client-available')).toHaveTextContent(
            'Client available with baseUrl: http://127.0.0.1:8000'
        )
    })

    it('should provide client with custom baseUrl', () => {
        render(
            <RagbitsContextProvider baseUrl="https://api.example.com">
                <TestComponent />
            </RagbitsContextProvider>
        )

        expect(screen.getByTestId('client-available')).toHaveTextContent(
            'Client available with baseUrl: https://api.example.com'
        )
    })

    it('should throw error when useRagbitsContext is used outside provider', () => {
        render(<TestComponentOutsideProvider />)

        expect(screen.getByTestId('error')).toHaveTextContent(
            'useRagbitsContext must be used within a RagbitsProvider'
        )
    })
})
