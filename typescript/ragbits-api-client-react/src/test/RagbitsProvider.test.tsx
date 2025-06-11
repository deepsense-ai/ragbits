import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RagbitsProvider, useRagbitsContext } from '../RagbitsProvider'

function TestComponent() {
    const { client } = useRagbitsContext()
    return (
        <div data-testid="client-available">
            {client ? 'Client available' : 'No client'}
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
            <RagbitsProvider>
                <TestComponent />
            </RagbitsProvider>
        )

        expect(screen.getByTestId('client-available')).toHaveTextContent(
            'Client available'
        )
    })

    it('should provide client with custom baseUrl', () => {
        render(
            <RagbitsProvider baseUrl="https://api.example.com">
                <TestComponent />
            </RagbitsProvider>
        )

        expect(screen.getByTestId('client-available')).toHaveTextContent(
            'Client available'
        )
    })

    it('should throw error when useRagbitsContext is used outside provider', () => {
        render(<TestComponentOutsideProvider />)

        expect(screen.getByTestId('error')).toHaveTextContent(
            'useRagbitsContext must be used within a RagbitsProvider'
        )
    })

    it('should recreate client when config changes', () => {
        const { rerender } = render(
            <RagbitsProvider baseUrl="https://api1.example.com">
                <TestComponent />
            </RagbitsProvider>
        )

        expect(screen.getByTestId('client-available')).toHaveTextContent(
            'Client available'
        )

        rerender(
            <RagbitsProvider baseUrl="https://api2.example.com">
                <TestComponent />
            </RagbitsProvider>
        )

        expect(screen.getByTestId('client-available')).toHaveTextContent(
            'Client available'
        )
    })
})
