
import React, { useState } from 'react';
import type { Message } from '../types';
import { Sender } from '../types';
import { UserIcon, DeepseekIcon, ChatGPTIcon } from './icons';

interface MessageProps {
  message: Message;
}

const CodeBlock: React.FC<{ language: string; code: string }> = ({ language, code }) => {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    });
  };

  return (
    <div className="bg-black bg-opacity-40 rounded-lg my-2 font-mono text-sm relative">
      <div className="bg-gray-900 bg-opacity-50 text-gray-400 px-4 py-2 text-xs rounded-t-lg flex justify-between items-center">
        <span>{language || 'code'}</span>
        <button onClick={handleCopy} className="font-semibold hover:text-white transition-colors duration-200 flex items-center">
          {isCopied ? (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
              Copied!
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
              Copy
            </>
          )}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto"><code className="text-white">{code}</code></pre>
    </div>
  );
};

const ContentRenderer: React.FC<{ content: string }> = ({ content }) => {
    const parts = content.split(/(```[\w-]*\n[\s\S]*?\n```)/g);

    return (
        <div className="text-white whitespace-pre-wrap font-sans">
            {parts.map((part, index) => {
                const codeBlockRegex = /^```([\w-]*)?\n([\s\S]*?)\n```$/;
                const match = part.match(codeBlockRegex);

                if (match) {
                    const language = match[1] || '';
                    const code = match[2].trim();
                    return <CodeBlock key={index} language={language} code={code} />;
                } else if (part) {
                    return <span key={index}>{part}</span>;
                }
                return null;
            })}
        </div>
    );
};


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
        <ContentRenderer content={text} />
      </div>
      {isUser && <Avatar />}
    </div>
  );
};

export default MessageComponent;