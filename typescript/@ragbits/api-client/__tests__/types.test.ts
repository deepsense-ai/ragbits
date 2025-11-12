import { describe, it, expect } from 'vitest'
import * as RagbitsApiClient from '../src'

describe('Package Exports', () => {
    it('should export RagbitsClient class', () => {
        expect(RagbitsApiClient.RagbitsClient).toBeDefined()
        expect(typeof RagbitsApiClient.RagbitsClient).toBe('function')
    })

    it('should export FeedbackType enum', () => {
        expect(RagbitsApiClient.FeedbackType).toBeDefined()
        expect(typeof RagbitsApiClient.FeedbackType).toBe('object')
        expect(RagbitsApiClient.FeedbackType.Like).toBe('like')
        expect(RagbitsApiClient.FeedbackType.Dislike).toBe('dislike')
    })

    it('should export MessageRole enum', () => {
        expect(RagbitsApiClient.MessageRole).toBeDefined()
        expect(typeof RagbitsApiClient.MessageRole).toBe('object')
        expect(RagbitsApiClient.MessageRole.User).toBe('user')
        expect(RagbitsApiClient.MessageRole.Assistant).toBe('assistant')
        expect(RagbitsApiClient.MessageRole.System).toBe('system')
    })

    it('should export LiveUpdateType enum', () => {
        expect(RagbitsApiClient.LiveUpdateType).toBeDefined()
        expect(typeof RagbitsApiClient.LiveUpdateType).toBe('object')
        expect(RagbitsApiClient.LiveUpdateType.Start).toBe('START')
        expect(RagbitsApiClient.LiveUpdateType.Finish).toBe('FINISH')
    })
})
