import { describe, it, expect } from 'vitest'
import * as RagbitsReact from '../index'
import {
    RagbitsClient,
    MessageRole,
    ChatResponseType,
    FormFieldType,
    FeedbackType,
    type RagbitsCallResult,
    type RagbitsStreamResult,
    type RagbitsContextValue,
    type ChatRequest,
    type FeedbackRequest,
    type ConfigResponse,
} from '../index'

describe('Package Exports', () => {
    it('should export all hooks', () => {
        expect(RagbitsReact.useRagbitsCall).toBeDefined()
        expect(RagbitsReact.useRagbitsStream).toBeDefined()
        expect(RagbitsReact.useRagbitsContext).toBeDefined()
    })

    it('should export RagbitsProvider', () => {
        expect(RagbitsReact.RagbitsProvider).toBeDefined()
    })

    it('should export RagbitsClient', () => {
        expect(RagbitsClient).toBeDefined()
        expect(typeof RagbitsClient).toBe('function')
    })

    it('should export enums', () => {
        expect(MessageRole).toBeDefined()
        expect(MessageRole.USER).toBe('user')
        expect(MessageRole.ASSISTANT).toBe('assistant')
        expect(MessageRole.SYSTEM).toBe('system')

        expect(ChatResponseType).toBeDefined()
        expect(ChatResponseType.TEXT).toBe('text')
        expect(ChatResponseType.MESSAGE).toBe('message')

        expect(FormFieldType).toBeDefined()
        expect(FormFieldType.TEXT).toBe('text')
        expect(FormFieldType.SELECT).toBe('select')

        expect(FeedbackType).toBeDefined()
        expect(FeedbackType.LIKE).toBe('like')
        expect(FeedbackType.DISLIKE).toBe('dislike')
    })
})

describe('Type Definitions', () => {
    it('should define RagbitsCallResult interface correctly', () => {
        const mockResult: RagbitsCallResult<string> = {
            data: 'test',
            error: null,
            isLoading: false,
            call: async () => 'test',
            reset: () => {},
            abort: () => {},
        }

        expect(mockResult).toBeDefined()
        expect(mockResult.data).toBe('test')
        expect(typeof mockResult.call).toBe('function')
        expect(typeof mockResult.reset).toBe('function')
        expect(typeof mockResult.abort).toBe('function')
    })

    it('should define RagbitsStreamResult interface correctly', () => {
        const mockStreamResult: RagbitsStreamResult = {
            isStreaming: false,
            error: null,
            stream: () => () => {},
            cancel: () => {},
        }

        expect(mockStreamResult).toBeDefined()
        expect(typeof mockStreamResult.stream).toBe('function')
        expect(typeof mockStreamResult.cancel).toBe('function')
    })

    it('should define RagbitsContextValue interface correctly', () => {
        const client = new RagbitsClient()
        const contextValue: RagbitsContextValue = {
            client,
        }

        expect(contextValue).toBeDefined()
        expect(contextValue.client).toBeInstanceOf(RagbitsClient)
    })

    it('should define API request types correctly', () => {
        const chatRequest: ChatRequest = {
            message: 'Hello',
            history: [],
        }

        const feedbackRequest: FeedbackRequest = {
            feedback: FeedbackType.LIKE,
            message_id: 'msg-123',
            payload: null,
        }

        expect(chatRequest).toBeDefined()
        expect(chatRequest.message).toBe('Hello')
        expect(feedbackRequest).toBeDefined()
        expect(feedbackRequest.feedback).toBe('like')
    })

    it('should define response types correctly', () => {
        const configResponse: ConfigResponse = {
            feedback: {
                like: {
                    enabled: true,
                    form: {
                        title: 'Test Form',
                        fields: [],
                    },
                },
                dislike: {
                    enabled: false,
                    form: null,
                },
            },
        }

        expect(configResponse).toBeDefined()
        expect(configResponse.feedback.like.enabled).toBe(true)
        expect(configResponse.feedback.like.form?.title).toBe('Test Form')
    })
})
