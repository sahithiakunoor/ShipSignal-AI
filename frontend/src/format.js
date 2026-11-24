export const count = n => n == null ? '—' : new Intl.NumberFormat('en-US').format(n);
export const percent = n => n == null ? '—' : `${(n*100).toFixed(1)}%`;
export const days = n => n == null ? '—' : `${n.toFixed(1)} days`;
