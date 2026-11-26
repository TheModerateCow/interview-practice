// App-wide state shared by every feature: which screen is shown, the set list, the open set, the toast.
import { api } from './lib/api.js';

export const app = $state({
  view: '',            // '' (loading) | 'home' | 'ready' | 'round'
  sets: [],            // the picker and Home
  cur: null,           // the open set's name
  nav: 0,              // bumped by every navigation: an older async step that sees a newer value stops, so the latest wins
  settings: false,     // the Settings panel is open over the current screen
  dropErr: '',         // last import error, shown on Home
  over: false,         // a file is being dragged over the page
  importing: '',       // file name of a zip being imported
  flash: { text: '', bad: false, on: false, n: 0 },
});

export const fetchSets = async () => (await api('/sets')).sets;

let flashT;
export function showFlash(text, bad) {
  app.flash = { text, bad: !!bad, on: true, n: app.flash.n + 1 };   // a new n re-creates the toast, so a repeat visibly re-shows
  clearTimeout(flashT); flashT = setTimeout(() => { app.flash.on = false; }, bad ? 10000 : 5000);
}
