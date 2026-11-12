/**
 * Auto-BOM Solver & Retrofit Engine (Client-side JS)
 * Calcola l'accoppiamento idraulico ottimale e genera la distinta base per il carrello.
 */

const AutoBOM = (() => {
  const PORTS = {
    "TC15": { nome: "Tri-Clamp 1.5\" (flangia 50.5mm)", cat: "TC" },
    "TC20": { nome: "Tri-Clamp 2.0\" (flangia 64mm)", cat: "TC" },
    "TC10": { nome: "Mini Tri-Clamp 1.0\" (flangia 34mm)", cat: "TC" },
    "BSP12M": { nome: "Filettatura 1/2\" BSP Maschio", cat: "BSP" },
    "BSP12F": { nome: "Filettatura 1/2\" BSP Femmina", cat: "BSP" },
    "BSP34M": { nome: "Filettatura 3/4\" BSP Maschio", cat: "BSP" },
    "BSP34F": { nome: "Filettatura 3/4\" BSP Femmina", cat: "BSP" },
    "BARB12": { nome: "Portagomma 12 mm (1/2\")", cat: "BARB" },
    "CAM_A": { nome: "Camlock Tipo A Maschio", cat: "CAM" },
    "CAM_C": { nome: "Camlock Tipo C Femmina con Barb", cat: "CAM" },
  };

  const RACCORDI = [
    { sku: "FIT-TC15-BSP12M", nome: "Adattatore Tri-Clamp 1.5\" a 1/2\" BSP Maschio", p1: "TC15", p2: "BSP12M", prezzo: 11.50, acc: [["CLAMP-TC15", 1, 4.50], ["GSK-TC15", 1, 1.20]] },
    { sku: "FIT-TC15-BSP12F", nome: "Adattatore Tri-Clamp 1.5\" a 1/2\" BSP Femmina", p1: "TC15", p2: "BSP12F", prezzo: 11.90, acc: [["CLAMP-TC15", 1, 4.50], ["GSK-TC15", 1, 1.20]] },
    { sku: "FIT-TC15-BARB12", nome: "Portagomma Tri-Clamp 1.5\" a 12mm", p1: "TC15", p2: "BARB12", prezzo: 9.90, acc: [["CLAMP-TC15", 1, 4.50], ["GSK-TC15", 1, 1.20]] },
    { sku: "FIT-TC20-TC15", nome: "Riduttore Tri-Clamp 2.0\" a 1.5\"", p1: "TC20", p2: "TC15", prezzo: 17.90, acc: [["CLAMP-TC20", 1, 5.50], ["GSK-TC20", 1, 1.50]] },
    { sku: "FIT-NIP-12M-12M", nome: "Nipples Esagonale 1/2\" BSP Maschio-Maschio", p1: "BSP12F", p2: "BSP12F", prezzo: 3.90, acc: [["TEFLON-PTFE", 1, 1.00]] },
    { sku: "FIT-MAN-12F-12F", nome: "Manicotto 1/2\" BSP Femmina-Femmina", p1: "BSP12M", p2: "BSP12M", prezzo: 4.50, acc: [["TEFLON-PTFE", 1, 1.00]] },
    { sku: "FIT-BARB-12M-12", nome: "Portagomma 1/2\" BSP Maschio a 12 mm", p1: "BSP12F", p2: "BARB12", prezzo: 4.90, acc: [["TEFLON-PTFE", 1, 1.00]] },
    { sku: "FIT-BARB-12F-12", nome: "Portagomma 1/2\" BSP Femmina a 12 mm", p1: "BSP12M", p2: "BARB12", prezzo: 5.20, acc: [["TEFLON-PTFE", 1, 1.00]] },
    { sku: "CAM-TYPE-A", nome: "Camlock Tipo A (Maschio Camlock x 1/2\" BSP Femmina)", p1: "BSP12M", p2: "CAM_A", prezzo: 7.50, acc: [] },
    { sku: "CAM-TYPE-C", nome: "Camlock Tipo C (Femmina Camlock x Portagomma 12mm)", p1: "CAM_A", p2: "BARB12", prezzo: 10.90, acc: [] },
  ];

  const ACCESSORI_INFO = {
    "CLAMP-TC15": "Morsetto Tri-Clamp 1.5\" Inox 304",
    "GSK-TC15": "Guarnizione Silicone Alimentare Tri-Clamp 1.5\"",
    "CLAMP-TC20": "Morsetto Tri-Clamp 2.0\" Inox 304",
    "GSK-TC20": "Guarnizione Silicone Alimentare Tri-Clamp 2.0\"",
    "TEFLON-PTFE": "Nastro PTFE Sigillante Filetti ad Alta Densità",
  };

  function solve(nodoA, nodoB) {
    if (!PORTS[nodoA] || !PORTS[nodoB]) return { error: "Porta non valida" };

    if (nodoA === nodoB) {
      if (nodoA === "TC15") {
        return {
          percorso: ["TC15", "TC15"],
          pezzi: [
            { sku: "CLAMP-TC15", nome: ACCESSORI_INFO["CLAMP-TC15"], qta: 1, prezzo: 4.50 },
            { sku: "GSK-TC15", nome: ACCESSORI_INFO["GSK-TC15"], qta: 1, prezzo: 1.20 }
          ],
          totale: 5.70,
          desc: "Accoppiamento diretto flangia-a-flangia con morsetto e guarnizione inclusi."
        };
      }
      if (nodoA === "BARB12") {
        return {
          percorso: ["BARB12", "BARB12"],
          pezzi: [
            { sku: "FIT-TUBO-CON", nome: "Tubo Silicone Alimentare 12x18mm (1.5m) + Fascette Inox", qta: 1, prezzo: 8.50 }
          ],
          totale: 8.50,
          desc: "Unione tramite tubo in silicone alimentare 12x18 mm ad alta temperatura."
        };
      }
    }

    // BFS Shortest Path
    const grafo = {};
    for (const r of RACCORDI) {
      if (!grafo[r.p1]) grafo[r.p1] = [];
      if (!grafo[r.p2]) grafo[r.p2] = [];
      grafo[r.p1].push({ next: r.p2, fit: r });
      grafo[r.p2].push({ next: r.p1, fit: r });
    }

    const queue = [[nodoA, [], [nodoA]]];
    const visited = new Set([nodoA]);
    let best = null;

    while (queue.length > 0) {
      const [curr, pathFits, pathNodes] = queue.shift();
      if (curr === nodoB) {
        best = { pathFits, pathNodes };
        break;
      }
      if (pathFits.length >= 4) continue;

      for (const edge of (grafo[curr] || [])) {
        if (!visited.has(edge.next)) {
          visited.add(edge.next);
          queue.push([edge.next, [...pathFits, edge.fit], [...pathNodes, edge.next]]);
        }
      }
    }

    if (!best) {
      // Fallback flessibile universale
      return {
        percorso: [nodoA, "BARB12", "BARB12", nodoB],
        pezzi: [
          { sku: "FIT-UNIV-BARB-A", nome: `Adattatore ${nodoA} a Portagomma 12mm`, qta: 1, prezzo: 9.90 },
          { sku: "FIT-TUBO-CON", nome: "Tubo Silicone 12x18mm (1.5m) + Fascette", qta: 1, prezzo: 8.50 },
          { sku: "FIT-UNIV-BARB-B", nome: `Adattatore Portagomma 12mm a ${nodoB}`, qta: 1, prezzo: 9.90 }
        ],
        totale: 28.30,
        desc: "Collegamento universale con linea flessibile siliconica certificata MOCA."
      };
    }

    const itemMap = {};
    for (const fit of best.pathFits) {
      if (!itemMap[fit.sku]) {
        itemMap[fit.sku] = { sku: fit.sku, nome: fit.nome, qta: 1, prezzo: fit.prezzo };
      } else {
        itemMap[fit.sku].qta += 1;
      }
      for (const [accSku, qta, prezzo] of (fit.acc || [])) {
        if (!itemMap[accSku]) {
          itemMap[accSku] = { sku: accSku, nome: ACCESSORI_INFO[accSku] || accSku, qta: qta, prezzo: prezzo };
        } else {
          itemMap[accSku].qta += qta;
        }
      }
    }

    const pezzi = Object.values(itemMap);
    const totale = pezzi.reduce((acc, p) => acc + (p.prezzo * p.qta), 0);

    return {
      percorso: best.pathNodes,
      pezzi: pezzi,
      totale: Number(totale.toFixed(2)),
      desc: `Soluzione meccanica garantita: ${best.pathFits.length} raccordo/i con accessori di tenuta.`
    };
  }

  return {
    PORTS,
    solve
  };
})();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = AutoBOM;
}
