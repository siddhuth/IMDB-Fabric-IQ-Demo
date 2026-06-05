import { getRayfinClient, isLocalBackend } from './rayfinClient';

export interface ChatTurnItem {
  id: string;
  question: string;
  answer: string;
  latencyMs: number;
  createdAt: Date;
}

// Local-dev fallback so history works without a database.
const inMemory: ChatTurnItem[] = [];

export async function getChatTurns(): Promise<ChatTurnItem[]> {
  if (isLocalBackend()) {
    return [...inMemory].sort(
      (a, b) => b.createdAt.getTime() - a.createdAt.getTime()
    );
  }

  const client = getRayfinClient();
  const results = await client.data.ChatTurn.select([
    'id',
    'question',
    'answer',
    'latencyMs',
    'createdAt',
  ])
    .orderBy({ createdAt: 'desc' })
    .execute();
  return results as ChatTurnItem[];
}

export async function addChatTurn(input: {
  question: string;
  answer: string;
  latencyMs: number;
}): Promise<ChatTurnItem> {
  if (isLocalBackend()) {
    const item: ChatTurnItem = {
      id: crypto.randomUUID(),
      createdAt: new Date(),
      ...input,
    };
    inMemory.push(item);
    return item;
  }

  const client = getRayfinClient();
  const session = client.auth.getSession();
  if (!session.isAuthenticated || !session.user) {
    throw new Error('Cannot record history: user is not authenticated.');
  }
  const item = await client.data.ChatTurn.create({
    ...input,
    createdAt: new Date(),
    user_id: session.user.id,
  });
  return item as ChatTurnItem;
}
