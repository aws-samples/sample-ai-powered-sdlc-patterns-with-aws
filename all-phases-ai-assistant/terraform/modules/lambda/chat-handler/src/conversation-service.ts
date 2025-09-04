import { DeleteItemCommand, DynamoDBClient, PutItemCommand, QueryCommand, UpdateItemCommand } from '@aws-sdk/client-dynamodb';
import { marshall, unmarshall } from '@aws-sdk/util-dynamodb';
import { v4 as uuidv4 } from 'uuid';
import { ConversationContext, ConversationMessage, DocumentSource } from './types';

export class ConversationService {
  private dynamoClient: DynamoDBClient;
  private tableName: string;

  constructor() {
    // AWS Lambda automatically sets AWS_REGION, but it's a reserved environment variable
    const region = process.env.AWS_DEFAULT_REGION || process.env.AWS_REGION || 'us-west-2';
    
    // Configure DynamoDB client with proper credentials for testing
    const clientConfig: any = { region };
    
    // In test environment, use the aidlc_main profile
    if (process.env.NODE_ENV === 'test' || process.env.AWS_PROFILE) {
      clientConfig.credentials = undefined; // Let AWS SDK handle profile-based credentials
    }
    
    this.dynamoClient = new DynamoDBClient(clientConfig);
    this.tableName = process.env.DOCUMENTS_TABLE || 'ai-assistant-dev-documents';
    
    // Validate table name
    if (!this.tableName || this.tableName.trim() === '') {
      throw new Error('DOCUMENTS_TABLE environment variable is required and cannot be empty');
    }
  }

  async createConversation(userId: string): Promise<string> {
    const conversationId = uuidv4();
    const now = new Date().toISOString();

    const conversation: ConversationContext = {
      conversationId,
      userId,
      messages: [],
      createdAt: now,
      lastActivity: now
    };

    await this.dynamoClient.send(new PutItemCommand({
      TableName: this.tableName,
      Item: marshall({
        PK: `CONV#${conversationId}`,
        SK: 'METADATA',
        ...conversation,
        GSI1PK: `USER#${userId}`,
        GSI1SK: `CONV#${now}`
      }, { removeUndefinedValues: true })
    }));

    return conversationId;
  }

  async getConversation(conversationId: string): Promise<ConversationContext | null> {
    try {
      const response = await this.dynamoClient.send(new QueryCommand({
        TableName: this.tableName,
        KeyConditionExpression: 'PK = :pk',
        ExpressionAttributeValues: marshall({
          ':pk': `CONV#${conversationId}`
        }, { removeUndefinedValues: true })
      }));

      if (!response.Items || response.Items.length === 0) {
        return null;
      }

      // Find metadata item
      const metadataItem = response.Items.find(item => {
        const unmarshalled = unmarshall(item);
        return unmarshalled.SK === 'METADATA';
      });

      if (!metadataItem) {
        return null;
      }

      const conversation = unmarshall(metadataItem) as ConversationContext;

      // Get all messages
      const messageItems = response.Items.filter(item => {
        const unmarshalled = unmarshall(item);
        return unmarshalled.SK.startsWith('MSG#');
      });

      conversation.messages = messageItems
        .map(item => unmarshall(item) as ConversationMessage)
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

      return conversation;
    } catch (error) {
      console.error('Error getting conversation:', error);
      return null;
    }
  }

  async addMessage(
    conversationId: string,
    type: 'user' | 'assistant',
    content: string,
    sources?: DocumentSource[]
  ): Promise<ConversationMessage> {
    const messageId = uuidv4();
    const timestamp = new Date().toISOString();

    const message: ConversationMessage = {
      messageId,
      type,
      content,
      timestamp,
      sources
    };

    // Add message to conversation
    await this.dynamoClient.send(new PutItemCommand({
      TableName: this.tableName,
      Item: marshall({
        PK: `CONV#${conversationId}`,
        SK: `MSG#${timestamp}#${messageId}`,
        ...message
      }, { removeUndefinedValues: true })
    }));

    // Update conversation last activity
    await this.dynamoClient.send(new UpdateItemCommand({
      TableName: this.tableName,
      Key: marshall({
        PK: `CONV#${conversationId}`,
        SK: 'METADATA'
      }, { removeUndefinedValues: true }),
      UpdateExpression: 'SET lastActivity = :timestamp',
      ExpressionAttributeValues: marshall({
        ':timestamp': timestamp
      }, { removeUndefinedValues: true })
    }));

    return message;
  }

  async getUserConversations(userId: string, limit: number = 10): Promise<ConversationContext[]> {
    try {
      const response = await this.dynamoClient.send(new QueryCommand({
        TableName: this.tableName,
        IndexName: 'GSI1',
        KeyConditionExpression: 'GSI1PK = :pk',
        ExpressionAttributeValues: marshall({
          ':pk': `USER#${userId}`
        }, { removeUndefinedValues: true }),
        ScanIndexForward: false, // Most recent first
        Limit: limit
      }));

      if (!response.Items) {
        return [];
      }

      const conversations: ConversationContext[] = [];
      
      for (const item of response.Items) {
        const conversation = unmarshall(item) as ConversationContext;
        
        // Get recent messages for preview (last 5 messages)
        const messagesResponse = await this.dynamoClient.send(new QueryCommand({
          TableName: this.tableName,
          KeyConditionExpression: 'PK = :pk AND begins_with(SK, :sk)',
          ExpressionAttributeValues: marshall({
            ':pk': `CONV#${conversation.conversationId}`,
            ':sk': 'MSG#'
          }, { removeUndefinedValues: true }),
          ScanIndexForward: false,
          Limit: 5
        }));

        if (messagesResponse.Items) {
          conversation.messages = messagesResponse.Items
            .map(msgItem => unmarshall(msgItem) as ConversationMessage)
            .reverse(); // Reverse to get chronological order
        } else {
          conversation.messages = [];
        }

        conversations.push(conversation);
      }

      return conversations;
    } catch (error) {
      console.error('Error getting user conversations:', error);
      return [];
    }
  }

  async deleteConversation(conversationId: string): Promise<void> {
    try {
      // Get all items for this conversation
      const response = await this.dynamoClient.send(new QueryCommand({
        TableName: this.tableName,
        KeyConditionExpression: 'PK = :pk',
        ExpressionAttributeValues: marshall({
          ':pk': `CONV#${conversationId}`
        }, { removeUndefinedValues: true })
      }));

      if (!response.Items) {
        return;
      }

      // Delete all items
      const deletePromises = response.Items.map(item => {
        const key = {
          PK: item.PK,
          SK: item.SK
        };
        
        return this.dynamoClient.send(new DeleteItemCommand({
          TableName: this.tableName,
          Key: key
        }));
      });

      await Promise.all(deletePromises);
    } catch (error) {
      console.error('Error deleting conversation:', error);
      throw error;
    }
  }

  async getConversationHistory(conversationId: string, limit: number = 50): Promise<ConversationMessage[]> {
    try {
      const response = await this.dynamoClient.send(new QueryCommand({
        TableName: this.tableName,
        KeyConditionExpression: 'PK = :pk AND begins_with(SK, :sk)',
        ExpressionAttributeValues: marshall({
          ':pk': `CONV#${conversationId}`,
          ':sk': 'MSG#'
        }, { removeUndefinedValues: true }),
        ScanIndexForward: true, // Chronological order
        Limit: limit
      }));

      if (!response.Items) {
        return [];
      }

      return response.Items.map(item => unmarshall(item) as ConversationMessage);
    } catch (error) {
      console.error('Error getting conversation history:', error);
      return [];
    }
  }
}