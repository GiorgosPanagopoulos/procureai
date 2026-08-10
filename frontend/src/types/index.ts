export type Language = 'en' | 'gr';

export type RightTab = 'data' | 'results';

export interface TraceStep {
  type: 'thought' | 'tool_call' | 'observation';
  content?: string;
  tool?: string;
  input?: string;
}

export interface UsageInfo {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  cache_creation_tokens?: number;
  cache_read_tokens?: number;
  tool_calls_count?: number;
}

export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  toolUsed?: string;
  trace?: TraceStep[];
  usage?: UsageInfo;
  conversationId?: string;
}

export interface AgentResponse {
  response: string;
  tool_used?: string;
  conversation_id?: string;
  usage?: UsageInfo;
  trace?: TraceStep[];
}

export interface Supplier {
  _id?: string;
  name: string;
  category: string;
  contact: string;
  rating: number;
}

export interface Bid {
  _id?: string;
  supplier_id: string;
  items: Array<{ name: string; quantity: number; unit_price: number }>;
  total_price: number;
  delivery_days: number;
  terms: string;
  status: string;
}
