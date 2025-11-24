
import React, { useRef, useEffect } from 'react';
import type { Message } from '../types';
import MessageComponent from './Message';

interface ChatWindowProps {
  messages: Message[];
}

const ChatWindow: React.FC<ChatWindowProps> = ({ messages }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div ref={scrollRef} className="flex-grow p-6 overflow-y-auto">
      {messages.map((msg) => (
        <MessageComponent key={msg.id} message={msg} />
      ))}
    </div>
  );
};

export default ChatWindow;
