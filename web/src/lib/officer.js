// The officer access code is kept for this browser tab only (sessionStorage),
// so closing the tab signs the officer out. Storage can be blocked (private
// mode), so every access is guarded.

const KEY = "claimsat-officer-code";

export function getOfficerCode() {
  try {
    return window.sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setOfficerCode(code) {
  try {
    window.sessionStorage.setItem(KEY, code);
  } catch {
    // Without storage the officer re-enters the code on each page.
  }
}

export function clearOfficerCode() {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    // Nothing stored.
  }
}
