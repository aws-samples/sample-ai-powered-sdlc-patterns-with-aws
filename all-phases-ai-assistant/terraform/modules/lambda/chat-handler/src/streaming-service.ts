import {
    BedrockRuntimeClient,
    InvokeModelWithResponseStreamCommand,
    InvokeModelWithResponseStreamCommandInput
} from '@aws-sdk/client-bedrock-runtime';
import { ChatRequest, DocumentSource, StreamingResponse } from './types';

export class StreamingService {
  private bedrockRuntime: BedrockRuntimeClient;

  constructor() {
    // AWS Lambda automatically sets AWS_REGION, but it's a reserved environment variable
    const region = process.env.AWS_DEFAULT_REGION || process.env.AWS_REGION || 'us-west-2';
    
    this.bedrockRuntime = new BedrockRuntimeClient({ 
      region 
    });
  }

  async streamChatResponse(
    request: ChatRequest,
    modelArn: string,
    retrievedSources: DocumentSource[]
  ): Promise<StreamingResponse> {
    try {
      // Build context from retrieved sources
      const context = this.buildContextFromSources(retrievedSources);
      
      // Create streaming prompt
      const prompt = this.buildStreamingPrompt(request.question, context);

      const input: InvokeModelWithResponseStreamCommandInput = {
        modelId: this.extractModelId(modelArn),
        body: JSON.stringify({
          anthropic_version: "bedrock-2023-05-31",
          max_tokens: 4000,
          messages: [
            {
              role: 'user',
              content: prompt
            }
          ],
          stream: true
        }),
        contentType: 'application/json',
        accept: 'application/json'
      };

      const command = new InvokeModelWithResponseStreamCommand(input);
      const response = await this.bedrockRuntime.send(command);

      if (!response.body) {
        throw new Error('No response body received from streaming API');
      }

      return {
        stream: response.body,
        sources: retrievedSources,
        conversationId: request.conversationId || '',
        modelUsed: this.extractModelName(modelArn)
      };

    } catch (error) {
      console.error('Error in streaming chat response:', error);
      throw error;
    }
  }

  private buildContextFromSources(sources: DocumentSource[]): string {
    if (sources.length === 0) {
      return 'No relevant context found in the knowledge base.';
    }

    let context = 'Based on the following information from the knowledge base:\n\n';
    
    sources.forEach((source, index) => {
      context += `Source ${index + 1} (${source.fileName || 'Unknown Document'}):\n`;
      context += `${source.excerpt}\n\n`;
    });

    return context;
  }

  private buildStreamingPrompt(question: string, context: string): string {
    return `
You are an AI assistant helping with software development questions. 
Please provide a comprehensive, accurate answer based on the retrieved context.

${context}

Question: ${question}

Please provide a detailed, well-structured answer based on the context above. 
If the context doesn't contain sufficient information, clearly state this.
Include specific examples and code snippets when relevant.
Cite your sources by referencing the document names.

Answer:
    `.trim();
  }

  private extractModelId(modelArn: string): string {
    // Extract model ID from ARN for streaming API
    const parts = modelArn.split('/');
    return parts[parts.length - 1];
  }

  private extractModelName(modelArn: string): string {
    if (modelArn.includes('claude-opus-4-1')) {
      return 'claude-opus-4-1';
    } else if (modelArn.includes('claude-3-7-sonnet')) {
      return 'claude-3-7-sonnet';
    } else if (modelArn.includes('claude-3-5-sonnet')) {
      return 'claude-3-5-sonnet-v2';
    }
    return modelArn;
  }

  async processStreamingResponse(stream: any): Promise<string> {
    let fullResponse = '';
    
    try {
      for await (const chunk of stream) {
        if (chunk.chunk?.bytes) {
          const chunkData = JSON.parse(new TextDecoder().decode(chunk.chunk.bytes));
          
          if (chunkData.type === 'content_block_delta' && chunkData.delta?.text) {
            fullResponse += chunkData.delta.text;
          }
        }
      }
    } catch (error) {
      console.error('Error processing streaming response:', error);
      throw error;
    }

    return fullResponse;
  }
}