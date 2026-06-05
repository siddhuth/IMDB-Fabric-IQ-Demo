import { SavedQuestion } from './SavedQuestion.js';
import { ChatTurn } from './ChatTurn.js';

export type ImdbAppSchema = {
  SavedQuestion: SavedQuestion;
  ChatTurn: ChatTurn;
};

export const schema = [SavedQuestion, ChatTurn];
