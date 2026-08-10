import type { RefObject } from 'react';
import Icon from '../common/Icon';
import MessageBubble from './MessageBubble';
import type { Translations } from '../../i18n/translations';
import type { Language, Message } from '../../types';

const TypingDots = () => (
  <div className="typing-dots">
    {[0, 1, 2].map(i => (
      <div key={i} className="typing-dot" style={{ animationDelay: `${i * 0.2}s` }} />
    ))}
  </div>
);

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  suppliersCount: number;
  bidsCount: number;
  chatRef: RefObject<HTMLDivElement>;
  language: Language;
  t: Translations;
}

export default function MessageList({ messages, isLoading, suppliersCount, bidsCount, chatRef, language, t }: MessageListProps) {
  return (
    <div className="chat-messages" ref={chatRef}>
      {messages.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <Icon name="ai" size={26} color="var(--accent2)" />
          </div>
          <h2 className="empty-title">{t.welcome}</h2>
          <p className="empty-desc">{t.welcomeDesc}</p>
          <div className="empty-pills">
            <div className="empty-pill" style={{ color: 'var(--cyan)' }}>
              {suppliersCount || 128} Suppliers
            </div>
            <div className="empty-pill" style={{ color: '#a78bfa' }}>
              {bidsCount || 47} Active Bids
            </div>
            <div className="empty-pill" style={{ color: 'var(--accent2)' }}>
              €2.4M Pipeline
            </div>
          </div>
        </div>
      ) : (
        <>
          {messages.map(msg => (
            <MessageBubble
              key={msg.id}
              message={msg}
              language={language}
              viewReasoningLabel={t.viewReasoning}
              hideReasoningLabel={t.hideReasoning}
            />
          ))}
          {isLoading && (
            <div className="msg-row agent">
              <div className="msg-avatar agent">
                <Icon name="ai" size={14} color="var(--accent2)" />
              </div>
              <div className="msg-content">
                <div className="msg-bubble agent">
                  <TypingDots />
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
