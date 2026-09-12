// `datos-por-cuadro.csv` no tiene comillas ni comas dentro de los valores: sólo
// números, enteros y celdas vacías (los NaN se escriben vacíos). Un split alcanza.

export interface Tabla {
  columnas: string[];
  filas: (number | null)[][];
}

export function parseCsv(texto: string): Tabla {
  const lineas = texto.split(/\r?\n/).filter((l) => l.length > 0);
  if (lineas.length === 0) return { columnas: [], filas: [] };
  const columnas = lineas[0].split(",");
  const filas = lineas.slice(1).map((l) =>
    l.split(",").map((c) => {
      if (c === "" || c === "None") return null;
      const v = Number(c);
      return Number.isFinite(v) ? v : null;
    }),
  );
  return { columnas, filas };
}
