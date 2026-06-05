import { getRayfinClient, isLocalBackend } from './rayfinClient';

export interface SavedQuestionItem {
  id: string;
  question: string;
  isFavorite: boolean;
  createdAt: Date;
}

// Local-dev fallback so the sample is fully functional without a database.
let inMemory: SavedQuestionItem[] = [];

export async function getSavedQuestions(): Promise<SavedQuestionItem[]> {
  if (isLocalBackend()) {
    return [...inMemory].sort(
      (a, b) => b.createdAt.getTime() - a.createdAt.getTime()
    );
  }

  const client = getRayfinClient();
  const results = await client.data.SavedQuestion.select([
    'id',
    'question',
    'isFavorite',
    'createdAt',
  ])
    .orderBy({ createdAt: 'desc' })
    .execute();
  return results as SavedQuestionItem[];
}

export async function saveQuestion(
  question: string
): Promise<SavedQuestionItem> {
  if (isLocalBackend()) {
    const item: SavedQuestionItem = {
      id: crypto.randomUUID(),
      question,
      isFavorite: false,
      createdAt: new Date(),
    };
    inMemory.push(item);
    return item;
  }

  const client = getRayfinClient();
  const session = client.auth.getSession();
  if (!session.isAuthenticated || !session.user) {
    throw new Error('Cannot save question: user is not authenticated.');
  }
  const item = await client.data.SavedQuestion.create({
    question,
    isFavorite: false,
    createdAt: new Date(),
    user_id: session.user.id,
  });
  return item as SavedQuestionItem;
}

export async function toggleFavorite(
  id: string,
  isFavorite: boolean
): Promise<void> {
  if (isLocalBackend()) {
    const item = inMemory.find((q) => q.id === id);
    if (item) item.isFavorite = isFavorite;
    return;
  }

  const client = getRayfinClient();
  await client.data.SavedQuestion.update({ id }, { isFavorite });
}

export async function deleteSavedQuestion(id: string): Promise<void> {
  if (isLocalBackend()) {
    inMemory = inMemory.filter((q) => q.id !== id);
    return;
  }

  const client = getRayfinClient();
  await client.data.SavedQuestion.delete({ id });
}
