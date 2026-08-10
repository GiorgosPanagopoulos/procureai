interface IconProps {
  name: string;
  size?: number;
  color?: string;
}

export default function Icon({ name, size = 16, color = 'currentColor' }: IconProps) {
  const icons: Record<string, JSX.Element> = {
    logo:      <svg width={size} height={size} viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="8" height="8" rx="2" fill={color} opacity=".9"/><rect x="13" y="3" width="8" height="8" rx="2" fill={color} opacity=".6"/><rect x="3" y="13" width="8" height="8" rx="2" fill={color} opacity=".6"/><rect x="13" y="13" width="8" height="8" rx="2" fill={color} opacity=".3"/></svg>,
    sun:       <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
    upload:    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>,
    send:      <svg width={size} height={size} viewBox="0 0 24 24" fill={color}><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>,
    ai:        <svg width={size} height={size} viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke={color} strokeWidth="1.5" opacity=".4"/><circle cx="12" cy="12" r="4" fill={color}/><path d="M12 2v4M12 18v4M2 12h4M18 12h4" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity=".6"/></svg>,
    user:      <svg width={size} height={size} viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" fill={color} opacity=".8"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke={color} strokeWidth="2" strokeLinecap="round" fill="none" opacity=".6"/></svg>,
    suppliers: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9,22 9,12 15,12 15,22"/></svg>,
    bids:      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>,
    chart:     <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>,
    check:     <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>,
    sparkle:   <svg width={size} height={size} viewBox="0 0 24 24" fill={color}><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/></svg>,
    close:     <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
    refresh:   <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>,
    search:    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
    globe:     <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>,
    brain:     <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round"><path d="M9.5 2a2.5 2.5 0 014.8.9A3 3 0 0117 6a3 3 0 01-1.5 2.6A3 3 0 0118 11a3 3 0 01-2.5 3A2.5 2.5 0 0114 16.5V22"/><path d="M9.5 2a2.5 2.5 0 00-4.8.9A3 3 0 006 6a3 3 0 001.5 2.6A3 3 0 006 11a3 3 0 002.5 3A2.5 2.5 0 0110 16.5V22"/></svg>,
  };
  return icons[name] ?? null;
}
