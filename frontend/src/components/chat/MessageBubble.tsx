import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Icon from '../common/Icon';
import TracePanel from './TracePanel';
import UsageBadge from './UsageBadge';
import type { Language, Message } from '../../types';

interface MessageBubbleProps {
  message: Message;
  language: Language;
  viewReasoningLabel: string;
  hideReasoningLabel: string;
}

export default function MessageBubble({ message, language, viewReasoningLabel, hideReasoningLabel }: MessageBubbleProps) {
  return (
    <div className={`msg-row ${message.sender}`}>
      <div className={`msg-avatar ${message.sender}`}>
        <Icon
          name={message.sender === 'agent' ? 'ai' : 'user'}
          size={14}
          color={message.sender === 'agent' ? 'var(--accent2)' : 'var(--text2)'}
        />
      </div>
      <div className="msg-content">
        <div className={`msg-bubble ${message.sender}`}>
          {message.sender === 'agent' ? (
            <div className="prose-agent">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
            </div>
          ) : (
            message.text
          )}
          {message.toolUsed && (
            <div className="tool-badge">⚙ {message.toolUsed}</div>
          )}
          {message.usage && <UsageBadge usage={message.usage} />}
        </div>
        {message.trace && message.trace.length > 0 && (
          <TracePanel
            trace={message.trace}
            lang={language}
            viewLabel={viewReasoningLabel}
            hideLabel={hideReasoningLabel}
          />
        )}
        <div className="msg-time">
          {message.timestamp.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}
