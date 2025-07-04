import { describe, it, expect } from 'vitest'
import * as RagbitsApiClient from '../src'

describe('Package Exports', () => {
    it('should export RagbitsClient class', () => {
        expect(RagbitsApiClient.RagbitsClient).toBeDefined()
        expect(typeof RagbitsApiClient.RagbitsClient).toBe('function')
    })

    it('should export MessageRole enum with correct values', () => {
        expect(RagbitsApiClient.MessageRole).toBeDefined()
        expect(RagbitsApiClient.MessageRole.USER).toBe('user')
        expect(RagbitsApiClient.MessageRole.ASSISTANT).toBe('assistant')
        expect(RagbitsApiClient.MessageRole.SYSTEM).toBe('system')
    })

    it('should export ChatResponseType enum with correct values', () => {
        expect(RagbitsApiClient.ChatResponseType).toBeDefined()
        expect(RagbitsApiClient.ChatResponseType.TEXT).toBe('text')
        expect(RagbitsApiClient.ChatResponseType.REFERENCE).toBe('reference')
        expect(RagbitsApiClient.ChatResponseType.STATE_UPDATE).toBe(
            'state_update'
        )
        expect(RagbitsApiClient.ChatResponseType.MESSAGE_ID).toBe('message_id')
        expect(RagbitsApiClient.ChatResponseType.CONVERSATION_ID).toBe(
            'conversation_id'
        )
    })

    it('should export FeedbackType enum with correct values', () => {
        expect(RagbitsApiClient.FeedbackType).toBeDefined()
        expect(RagbitsApiClient.FeedbackType.LIKE).toBe('like')
        expect(RagbitsApiClient.FeedbackType.DISLIKE).toBe('dislike')
    })
})
