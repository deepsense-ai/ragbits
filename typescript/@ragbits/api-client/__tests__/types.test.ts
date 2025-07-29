import { describe, it, expect } from 'vitest'
import * as RagbitsApiClient from '../src'

describe('Package Exports', () => {
    it('should export RagbitsClient class', () => {
        expect(RagbitsApiClient.RagbitsClient).toBeDefined()
        expect(typeof RagbitsApiClient.RagbitsClient).toBe('function')
    })
})
