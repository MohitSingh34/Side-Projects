export enum Sender {
  User = 'user',
  Deepseek = 'deepseek',
  ChatGPT = 'chatgpt',
  System = 'system',
}

export interface Message {
  id: number;
  text: string;
  sender: Sender;
}