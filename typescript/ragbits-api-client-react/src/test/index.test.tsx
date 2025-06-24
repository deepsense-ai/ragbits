import { describe, it, expect } from 'vitest'
import * as RagbitsReact from '../index'

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
        expect(RagbitsReact.RagbitsProvider).toBeDefined()
        expect(typeof RagbitsReact.RagbitsProvider).toBe('function')
    })
})
