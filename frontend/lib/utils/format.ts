export const fmtNum = (n: number | null | undefined, d = 2) =>
  n == null || Number.isNaN(n) ? "—" : Number(n).toFixed(d);

export const fmtInt = (n: number | null | undefined) =>
  n == null || Number.isNaN(n) ? "—" : Math.trunc(Number(n)).toLocaleString();

export const fmtTs = (n: number | null | undefined) =>
  n == null ? "—" : Number(n).toLocaleString();
