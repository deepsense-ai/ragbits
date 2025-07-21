import { describe, it, expect } from 'vitest'
import * as RagbitsReact from '../src'

describe('Package Exports', () => {
    it('should export all hooks', () => {
        expect(RagbitsReact.useRagbitsCall).toBeDefined()
        expect(typeof RagbitsReact.useRagbitsCall).toBe('function')
        expect(RagbitsReact.useRagbitsStream).toBeDefined()
        expect(typeof RagbitsReact.useRagbitsStream).toBe('function')
        expect(RagbitsReact.useRagbitsContext).toBeDefined()
        expect(typeof RagbitsReact.useRagbitsContext).toBe('function')
    })

    it('should export RagbitsProvider', () => {
        expect(RagbitsReact.RagbitsContextProvider).toBeDefined()
        expect(typeof RagbitsReact.RagbitsContextProvider).toBe('function')
    })
})
