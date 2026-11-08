/* GPL-3.0-only. Self reports are never network presence or proof of dispatch. */
export const CHECKIN_MAX_AGE=4*60*60*1000;
export const checkinLabel=s=>({ready:'Spreman/na',support:'Potrebna podrška',off_shift:'Van smene'}[s]||'Bez prijave');
export const taskLabel=s=>({assigned:'Dodeljeno',accepted:'Prihvaćeno',blocked:'Zastoj',completed:'Završeno',cancelled:'Otkazano'}[s]||'Nepoznato');
export function isFresh(at,now=Date.now()){const t=Date.parse(at);return Number.isFinite(t)&&Number.isFinite(now)&&t<=now+60000&&now-t<CHECKIN_MAX_AGE;}
export function stockLow(stock){return Number.isFinite(Number(stock.quantity))&&Number.isFinite(Number(stock.minimum))&&Number(stock.quantity)<Number(stock.minimum);}
