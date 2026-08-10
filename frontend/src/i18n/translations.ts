import type { Language, TraceStep } from '../types';

export interface Suggestion {
  label: string;
  icon: string;
}

export const STEP_META: Record<TraceStep['type'], { icon: string; label_en: string; label_gr: string }> = {
  thought:     { icon: '🤔', label_en: 'Thought',      label_gr: 'Σκέψη' },
  tool_call:   { icon: '🔧', label_en: 'Tool call',    label_gr: 'Κλήση εργαλείου' },
  observation: { icon: '📋', label_en: 'Observation',  label_gr: 'Παρατήρηση' },
};

export const SUGGESTIONS: Record<Language, Suggestion[]> = {
  en: [
    { label: 'Compare bids for office equipment', icon: 'chart' },
    { label: 'Find suppliers for IT hardware',    icon: 'search' },
    { label: 'Generate procurement report',       icon: 'bids' },
    { label: 'Payment terms in contracts',        icon: 'check' },
    { label: 'Show medical equipment bids',       icon: 'sparkle' },
    { label: 'Find high-rated suppliers',         icon: 'suppliers' },
  ],
  gr: [
    { label: 'Όρια απευθείας ανάθεσης',  icon: 'chart' },
    { label: 'Συνοπτικός διαγωνισμός',   icon: 'search' },
    { label: 'Εγγύηση καλής εκτέλεσης', icon: 'bids' },
    { label: 'Σύγκριση προσφορών',       icon: 'check' },
    { label: 'Εύρεση προμηθευτών IT',    icon: 'sparkle' },
    { label: 'Δημιουργία αναφοράς',      icon: 'suppliers' },
  ],
};

export const TRANSLATIONS = {
  en: {
    connected: 'Connected', disconnected: 'Disconnected',
    welcome: 'Welcome to ProcureAI',
    welcomeDesc: 'Ask me anything about public procurement, bids, suppliers, or contracts. I have access to your full database.',
    placeholder: 'Ask about procurement, bids, suppliers…',
    dataInspector: 'Data Inspector', results: 'Results',
    agentResponses: 'Agent Responses',
    noResults: 'No results yet',
    noResultsDesc: 'Start a conversation to see AI responses here',
    viewReasoning: 'View reasoning',
    hideReasoning: 'Hide reasoning',
    suppliers: 'Suppliers',
    bids: 'Bids',
    loadMore: 'Show more',
    showLess: 'Show less',
    clickToLoad: 'Click to load',
    recordsLoaded: 'records loaded',
    clearBtn: 'Clear',
    dataSynced: 'Data loaded · Last sync: just now',
    databaseRecords: 'Database Records',
    quickStats: 'Quick Stats',
  },
  gr: {
    connected: 'Συνδεδεμένο', disconnected: 'Αποσυνδεδεμένο',
    welcome: 'Καλώς ήρθατε στο ProcureAI',
    welcomeDesc: 'Ρωτήστε για δημόσιες προμήθειες, προσφορές και συμβάσεις βάσει Ν.4412/2016. Έχω πρόσβαση σε ολόκληρη τη βάση δεδομένων σας.',
    placeholder: 'Ρωτήστε για προμήθειες, προσφορές, προμηθευτές…',
    dataInspector: 'Επισκόπηση', results: 'Αποτελέσματα',
    agentResponses: 'Απαντήσεις',
    noResults: 'Δεν υπάρχουν αποτελέσματα',
    noResultsDesc: 'Ξεκινήστε μια συζήτηση για να δείτε απαντήσεις εδώ',
    viewReasoning: 'Εμφάνιση λογικής',
    hideReasoning: 'Απόκρυψη λογικής',
    suppliers: 'Προμηθευτές',
    bids: 'Προσφορές',
    loadMore: 'Εμφάνιση περισσότερων',
    showLess: 'Λιγότερα',
    clickToLoad: 'Κλικ για φόρτωση',
    recordsLoaded: 'εγγραφές φορτώθηκαν',
    clearBtn: 'Εκκαθάριση',
    dataSynced: 'Δεδομένα συγχρονίστηκα',
    databaseRecords: 'Εγγραφές Βάσης Δεδομένων',
    quickStats: 'Γρήγορες Στατιστικές',
  },
};

export type Translations = typeof TRANSLATIONS['en'];
