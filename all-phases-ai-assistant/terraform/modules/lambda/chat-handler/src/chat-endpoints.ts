import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import { chatApiHandler } from './chat-api-handler';

// Main handler for all chat API endpoints
export const handler = async (
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> => {
  return await chatApiHandler(event, context);
};