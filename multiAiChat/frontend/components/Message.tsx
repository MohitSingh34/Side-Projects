
import React from 'react';
import type { Message } from '../types';
import { Sender } from '../types';
import { UserIcon, DeepseekIcon, ChatGPTIcon } from './icons';

interface MessageProps {
  message: Message;
}

const MessageComponent: React.FC<MessageProps> = ({ message }) => {
  const { text, sender } = message;

  const isUser = sender === Sender.User;
  const isSystem = sender === Sender.System;

  const alignment = isUser ? 'justify-end' : 'justify-start';
  const bubbleColor = isUser ? 'bg-msg-user' : 'bg-msg-ai';
  const bubblePosition = isUser ? 'rounded-br-none' : 'rounded-bl-none';

  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <p className="text-sm text-gray-400 px-4 py-1 bg-gray-700 rounded-full">{text}</p>
      </div>
    );
  }

  const Avatar = () => {
    switch (sender) {
      case Sender.User:
        return <UserIcon />;
      case Sender.Deepseek:
        return <DeepseekIcon />;
      case Sender.ChatGPT:
        return <ChatGPTIcon />;
      default:
        return null;
    }
  };

  return (
    <div className={`flex items-end gap-3 my-4 ${alignment}`}>
      {!isUser && <Avatar />}
      <div className={`max-w-xs md:max-w-md lg:max-w-2xl px-4 py-3 rounded-2xl ${bubbleColor} ${bubblePosition}`}>
        <p className="text-white whitespace-pre-wrap">{text}</p>
      </div>
      {isUser && <Avatar />}
    </div>
  );
};

export default MessageComponent;
