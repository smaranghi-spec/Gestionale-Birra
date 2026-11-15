/**
 * Auto-BOM Solver, Smart Connection Suggestion Engine & Web Hardware Catalog
 * Supporta:
 * 1. Calcolo multi-opzione per collegare qualsiasi coppia di porte (Camlock Rapido, Tri-Clamp, Tubo + Fascetta, Push-Fit Duotight)
 * 2. Calcolo lunghezza reale tubo 3D in base alla distanza euclidea nello spazio Three.js
 * 3. Catalogo universale ricercabile + Importatore intelligente di qualsiasi pezzo dal Web (URL o ricerca libera)
 */

const AutoBOM = (() => {
  const PORTS = {
    "TC15":   { nome: "Tri-Clamp 1.5\" (flangia 50.5mm)", cat: "TC", short: "TC 1.5\"" },
    "TC20":   { nome: "Tri-Clamp 2.0\" (flangia 64mm)", cat: "TC", short: "TC 2.0\"" },
    "TC10":   { nome: "Mini Tri-Clamp 1.0\" (flangia 34mm)", cat: "TC", short: "TC 1.0\"" },
    "BSP12M": { nome: "Filettatura 1/2\" BSP Maschio", cat: "BSP", short: "1/2\" BSP M" },
    "BSP12F": { nome: "Filettatura 1/2\" BSP Femmina", cat: "BSP", short: "1/2\" BSP F" },
    "BSP34M": { nome: "Filettatura 3/4\" BSP Maschio", cat: "BSP", short: "3/4\" BSP M" },
    "BSP34F": { nome: "Filettatura 3/4\" BSP Femmina", cat: "BSP", short: "3/4\" BSP F" },
    "BSP38M": { nome: "Filettatura 3/8\" BSP Maschio", cat: "BSP", short: "3/8\" BSP M" },
    "BARB12": { nome: "Portagomma 12 mm (1/2\")", cat: "BARB", short: "Barb 12mm" },
    "BARB10": { nome: "Portagomma 10 mm (3/8\")", cat: "BARB", short: "Barb 10mm" },
    "BARB15": { nome: "Portagomma 15 mm (5/8\")", cat: "BARB", short: "Barb 15mm" },
    "CAM_A":  { nome: "Camlock Maschio (Tipo A/F)", cat: "CAM", short: "Camlock M" },
    "CAM_C":  { nome: "Camlock Femmina (Tipo C/D)", cat: "CAM", short: "Camlock F" },
    "JG8":    { nome: "Innesto Rapido Duotight / John Guest 8mm", cat: "JG", short: "Duotight 8mm" },
    "DIN25":  { nome: "Bocchettone Enologico DIN 25 Inox", cat: "DIN", short: "DIN 25" }
  };

  // Catalogo esteso di pezzi reali presenti sul web (ricercabili per nome, marca, tipo o URL)
  const WEB_CATALOG = [
    // TINI & PENTOLE
    {
      id: "web-polsinelli-50",
      sku: "WEB-POL-50L",
      nome: "Pentola Ammostamento/Bollitura Polsinelli 50L Inox 304",
      brand: "Polsinelli Enologia",
      categoria: "kettle",
      categoriaLabel: "Tini & Pentole",
      prezzo: 145.00,
      capacita_l: 50,
      dims: { radius: 0.42, height: 0.92 },
      colore: 0xd4d8dd,
      ports: [
        { id: "out_fondo", label: "Valvola Scarico Fondo", std: "BSP12M", side: "front_bottom" },
        { id: "in_ricircolo", label: "Ingresso Ricircolo / Whirlpool", std: "BSP12F", side: "front_top" }
      ],
      tags: "pentola tino mash boil polsinelli 50l inox rubinetto 1/2"
    },
    {
      id: "web-polsinelli-100",
      sku: "WEB-POL-100L",
      nome: "Tino Motorizzato Mash/Boil Polsinelli 100L Fondo Filtrante Halo",
      brand: "Polsinelli Enologia",
      categoria: "kettle",
      categoriaLabel: "Tini & Pentole",
      prezzo: 389.00,
      capacita_l: 100,
      dims: { radius: 0.54, height: 1.12 },
      colore: 0xd4d8dd,
      ports: [
        { id: "out_fondo", label: "Scarico Mosto Principale", std: "BSP34M", side: "front_bottom" },
        { id: "in_ricircolo", label: "Ritorno Sparge Superiore", std: "BSP12M", side: "front_top" },
        { id: "in_whirlpool", label: "Ingresso Tangenziale Whirlpool", std: "BSP12M", side: "right_mid" }
      ],
      tags: "pentola tino motorizzato 100l polsinelli mash filtro halo"
    },
    {
      id: "web-ssbrewtech-kettle-75",
      sku: "WEB-SSB-75L",
      nome: "SS Brewtech Brew Kettle 20 Gal (75L) Tri-Clamp Edition",
      brand: "SS Brewtech",
      categoria: "kettle",
      categoriaLabel: "Tini & Pentole",
      prezzo: 469.00,
      capacita_l: 75,
      dims: { radius: 0.48, height: 1.02 },
      colore: 0xe2e8f0,
      ports: [
        { id: "out_tc", label: "Valvola a Sfera Tri-Clamp Fondo", std: "TC15", side: "front_bottom" },
        { id: "in_tc_top", label: "Porta Vorlauf / Ricircolo TC", std: "TC15", side: "front_top" },
        { id: "whirlpool_tc", label: "Porta Whirlpool Tangenziale TC", std: "TC15", side: "right_mid" }
      ],
      tags: "ss brewtech kettle pentola tri-clamp tc 75l 20gal inox"
    },
    {
      id: "web-hlt-sparge-40",
      sku: "WEB-HLT-40L",
      nome: "Scalda Acqua di Sparge (HLT) Elettrico 40L con Termostato",
      brand: "BrewFerm / KegLand",
      categoria: "hlt",
      categoriaLabel: "Tini & Pentole",
      prezzo: 159.00,
      capacita_l: 40,
      dims: { radius: 0.36, height: 0.85 },
      colore: 0xcbd5e1,
      ports: [
        { id: "out_acqua", label: "Uscita Acqua Calda Sparge", std: "BSP12M", side: "front_bottom" },
        { id: "in_herms", label: "Ingresso Serpentina HERMS", std: "BSP12M", side: "left_mid" },
        { id: "out_herms", label: "Uscita Serpentina HERMS", std: "BSP12M", side: "right_mid" }
      ],
      tags: "hlt sparge acqua calda bollitore herms 40l"
    },
    // ALL-IN-ONE
    {
      id: "web-brewmonk-b50",
      sku: "WEB-BM-B50",
      nome: "BrewMonk B50 All-in-One WiFi 50L (3000W) con Cestello Malto",
      brand: "BrewMonk",
      categoria: "all_in_one",
      categoriaLabel: "All-in-One",
      prezzo: 549.00,
      capacita_l: 50,
      dims: { radius: 0.42, height: 0.98 },
      colore: 0xd1d5db,
      ports: [
        { id: "out_valvola", label: "Valvola Scarico Mosto 1/2\"", std: "BSP12M", side: "front_bottom" },
        { id: "in_camlock_top", label: "Tubo Ricircolo Telescopico Camlock", std: "CAM_A", side: "left_top" }
      ],
      tags: "brewmonk b50 b40 all in one klarstein maischfest 50l"
    },
    {
      id: "web-grainfather-g40",
      sku: "WEB-GF-G40",
      nome: "Grainfather G40 Wireless All-in-One System 40L",
      brand: "Grainfather",
      categoria: "all_in_one",
      categoriaLabel: "All-in-One",
      prezzo: 1190.00,
      capacita_l: 40,
      dims: { radius: 0.40, height: 0.94 },
      colore: 0x94a3b8,
      ports: [
        { id: "out_pompa", label: "Mandata Pompa Integrata G40", std: "BSP12M", side: "front_bottom" },
        { id: "in_ricircolo", label: "Ingresso Ricircolo Anello Conico", std: "BARB12", side: "front_top" }
      ],
      tags: "grainfather g30 g40 g70 all in one bluetooth"
    },
    {
      id: "web-brewzilla-gen4",
      sku: "WEB-KL-BZ65",
      nome: "KegLand BrewZilla 65L Gen 4.1 con RAPT WiFi e Fondo Concavo",
      brand: "KegLand",
      categoria: "all_in_one",
      categoriaLabel: "All-in-One",
      prezzo: 699.00,
      capacita_l: 65,
      dims: { radius: 0.44, height: 1.04 },
      colore: 0xcbd5e1,
      ports: [
        { id: "out_drain", label: "Scarico Centrale Concavo 1/2\"", std: "BSP12M", side: "front_bottom" },
        { id: "in_lid", label: "Braccio Ricircolo Superiore", std: "BARB12", side: "front_top" }
      ],
      tags: "kegland brewzilla robobrew 35l 65l gen4 rapt"
    },
    // FERMENTATORI
    {
      id: "web-fermzilla-conico-55",
      sku: "WEB-FZ-55L",
      nome: "FermZilla Tri-Conical 55L Isobarico (2.4 Bar) con Kit Pressione",
      brand: "KegLand",
      categoria: "fermenter",
      categoriaLabel: "Fermentatori",
      prezzo: 189.00,
      capacita_l: 55,
      dims: { radius: 0.40, height: 1.15 },
      colore: 0xbae6fd,
      ports: [
        { id: "in_mosto", label: "Valvola Farfalla Tri-Clamp 2\"", std: "TC20", side: "front_bottom" },
        { id: "in_liquid_balllock", label: "Attacco Liquido Duotight 8mm / Ball-Lock", std: "JG8", side: "front_top" },
        { id: "in_gas_spunding", label: "Attacco Gas CO2 / Spunding 8mm", std: "JG8", side: "right_top" }
      ],
      tags: "fermentatore isobarico fermzilla all rounder 27l 55l kegland"
    },
    {
      id: "web-unitank-inox-60",
      sku: "WEB-UNI-60L",
      nome: "Fermentatore Tronco-Conico Inox Coibentato Unitank 60L Tri-Clamp",
      brand: "SS Brewtech / Polsinelli",
      categoria: "fermenter",
      categoriaLabel: "Fermentatori",
      prezzo: 890.00,
      capacita_l: 60,
      dims: { radius: 0.44, height: 1.25 },
      colore: 0xe2e8f0,
      ports: [
        { id: "racking_arm", label: "Braccio Pescante (Racking Arm) TC 1.5\"", std: "TC15", side: "front_bottom" },
        { id: "dump_fondo", label: "Scarico Totale Lieviti Fondo TC 1.5\"", std: "TC15", side: "back_bottom" },
        { id: "cip_top", label: "Sfera Lavaggio CIP / Dry Hop TC 2\"", std: "TC20", side: "front_top" },
        { id: "glicole_in", label: "Ingresso Camicia Glicole 1/2\"", std: "BSP12M", side: "left_mid" },
        { id: "glicole_out", label: "Uscita Camicia Glicole 1/2\"", std: "BSP12M", side: "right_mid" }
      ],
      tags: "fermentatore conico inox unitank isobarico 60l 100l"
    },
    // POMPE
    {
      id: "web-pompa-mp15",
      sku: "WEB-PUMP-MP15",
      nome: "Pompa Magnetica Trascinamento MP-15RM Testa Inox 304 (120°C)",
      brand: "Chugger / Polsinelli",
      categoria: "pump",
      categoriaLabel: "Pompe",
      prezzo: 74.90,
      capacita_l: 0,
      dims: { radius: 0.18, height: 0.25 },
      colore: 0x0284c7,
      ports: [
        { id: "in_aspirazione", label: "Aspirazione Pompa 1/2\" BSP", std: "BSP12M", side: "left_mid" },
        { id: "out_mandata", label: "Mandata Pompa 1/2\" BSP", std: "BSP12M", side: "top_mid" }
      ],
      tags: "pompa magnetica mp-15rm chugger march novax 20b"
    },
    {
      id: "web-pompa-riptide-tc",
      sku: "WEB-PUMP-RIPTIDE",
      nome: "Blichmann RipTide Brewing Pump Testa Sanitaria Tri-Clamp 1.5\"",
      brand: "Blichmann Engineering",
      categoria: "pump",
      categoriaLabel: "Pompe",
      prezzo: 249.00,
      capacita_l: 0,
      dims: { radius: 0.20, height: 0.28 },
      colore: 0x0ea5e9,
      ports: [
        { id: "in_tc", label: "Aspirazione Tri-Clamp 1.5\"", std: "TC15", side: "left_mid" },
        { id: "out_tc", label: "Mandata Regolabile Tri-Clamp 1.5\"", std: "TC15", side: "top_mid" }
      ],
      tags: "pompa blichmann riptide tri-clamp inox"
    },
    {
      id: "web-pompa-novax-20b",
      sku: "WEB-PUMP-NOVAX",
      nome: "Elettropompa Autoadescante Rover Novax 20-B (95°C) Bisenso",
      brand: "Rover Pompe",
      categoria: "pump",
      categoriaLabel: "Pompe",
      prezzo: 118.00,
      capacita_l: 0,
      dims: { radius: 0.22, height: 0.28 },
      colore: 0xf59e0b,
      ports: [
        { id: "in_portagomma", label: "Attacco Aspirazione 3/4\" BSP", std: "BSP34M", side: "left_mid" },
        { id: "out_portagomma", label: "Attacco Mandata 3/4\" BSP", std: "BSP34M", side: "right_mid" }
      ],
      tags: "pompa rover novax 20b travaso mosto calda"
    },
    // SCAMBIATORI & CHILLER
    {
      id: "web-chiller-40p",
      sku: "WEB-CHILL-40P",
      nome: "Scambiatore di Calore Saldobrasato a 40 Piastre Inox 316 + Rame",
      brand: "Zilmet / Polsinelli",
      categoria: "chiller",
      categoriaLabel: "Scambiatori & Chiller",
      prezzo: 89.00,
      capacita_l: 0,
      dims: { radius: 0.24, height: 0.35 },
      colore: 0xb45309,
      ports: [
        { id: "wort_in", label: "Ingresso Mosto Caldo", std: "BSP34M", side: "left_top" },
        { id: "wort_out", label: "Uscita Mosto Freddo", std: "BSP34M", side: "left_bottom" },
        { id: "water_in", label: "Ingresso Acqua Rete", std: "BSP34M", side: "right_bottom" },
        { id: "water_out", label: "Scarico Acqua Calda", std: "BSP34M", side: "right_top" }
      ],
      tags: "scambiatore piastre 30 40 50 piastre chiller raffreddamento"
    },
    {
      id: "web-controflusso-inox",
      sku: "WEB-CFC-INOX",
      nome: "Scambiatore Controflusso Tubolare Convoluto Inox 304 Tri-Clamp",
      brand: "KegLand / Exchilerator",
      categoria: "counterflow",
      categoriaLabel: "Scambiatori & Chiller",
      prezzo: 165.00,
      capacita_l: 0,
      dims: { radius: 0.30, height: 0.38 },
      colore: 0x94a3b8,
      ports: [
        { id: "wort_in", label: "Ingresso Mosto TC 1.5\"", std: "TC15", side: "front_top" },
        { id: "wort_out", label: "Uscita Mosto Freddo TC 1.5\"", std: "TC15", side: "front_bottom" },
        { id: "water_in", label: "Ingresso Acqua Fredda 1/2\"", std: "BSP12M", side: "right_bottom" },
        { id: "water_out", label: "Uscita Acqua Calda 1/2\"", std: "BSP12M", side: "right_top" }
      ],
      tags: "controflusso counterflow chiller serpentina inox"
    },
    {
      id: "web-glycol-chiller-icemaster",
      sku: "WEB-GLYCOL-G20",
      nome: "KegLand IceMaster G20.1 Glycol Chiller (2 Linee Indipendenti)",
      brand: "KegLand",
      categoria: "glycol",
      categoriaLabel: "Scambiatori & Chiller",
      prezzo: 649.00,
      capacita_l: 25,
      dims: { radius: 0.35, height: 0.72 },
      colore: 0x1e293b,
      ports: [
        { id: "glycol_out", label: "Mandata Glicole Freddo (-4°C)", std: "BARB12", side: "front_bottom" },
        { id: "glycol_in", label: "Ritorno Glicole da Fermentatore", std: "BARB12", side: "front_top" }
      ],
      tags: "glicole refrigeratore icemaster chiller freddo"
    },
    // RIMS, FILTRI, HOPBACK & VALVOLE
    {
      id: "web-rims-tube-tc",
      sku: "WEB-RIMS-TC15",
      nome: "Tubo RIMS Inox Tri-Clamp 1.5\" con Resistenza 2500W Ultra-Low Density",
      brand: "BrewHardware / KegLand",
      categoria: "rims",
      categoriaLabel: "Filtri & RIMS",
      prezzo: 139.00,
      capacita_l: 2,
      dims: { radius: 0.14, height: 0.55 },
      colore: 0xe2e8f0,
      ports: [
        { id: "in_mosto", label: "Ingresso Mosto Basso TC 1.5\"", std: "TC15", side: "front_bottom" },
        { id: "out_mosto", label: "Uscita Mosto Riscaldato TC 1.5\"", std: "TC15", side: "front_top" }
      ],
      tags: "rims tube resistenza pid ricircolo mash"
    },
    {
      id: "web-hopback-inline-filter",
      sku: "WEB-FILT-TC15",
      nome: "Filtro In-Line / HopBack Sanitario Tri-Clamp 1.5\" Rete 150 Micron",
      brand: "Brouwland / BrewFerm",
      categoria: "filter",
      categoriaLabel: "Filtri & RIMS",
      prezzo: 64.00,
      capacita_l: 1.5,
      dims: { radius: 0.15, height: 0.38 },
      colore: 0x38bdf8,
      ports: [
        { id: "in_filter", label: "Ingresso Filtro / HopBack", std: "TC15", side: "left_mid" },
        { id: "out_filter", label: "Uscita Mosto Filtrato", std: "TC15", side: "right_mid" }
      ],
      tags: "filtro in-line hopback hop rocket luppolo trub"
    },
    {
      id: "web-sightglass-oxebar",
      sku: "WEB-SG-TC15",
      nome: "Spia Visiva (Sight Glass) Vetro Borosilicato + Pietra Ossigenazione TC 1.5\"",
      brand: "SS Brewtech",
      categoria: "valve",
      categoriaLabel: "Valvole & Spie",
      prezzo: 49.00,
      capacita_l: 0.5,
      dims: { radius: 0.12, height: 0.28 },
      colore: 0x7dd3fc,
      ports: [
        { id: "in_sg", label: "Ingresso Spia Visiva TC 1.5\"", std: "TC15", side: "left_mid" },
        { id: "out_sg", label: "Uscita Spia Visiva TC 1.5\"", std: "TC15", side: "right_mid" }
      ],
      tags: "spia visiva sight glass ossigenazione valvola sfera farfalla"
    }
  ];

  // Costruisce gli adattatori per portare una porta verso uno standard target
  function getAdaptersTo(porta, target) {
    if (porta === target) return [];
    const pName = (PORTS[porta] && PORTS[porta].nome) || porta;

    if (target === "CAM_A") {
      if (porta === "BSP12M") return [
        { sku: "CAM-TYPE-A", nome: "Camlock Tipo A (Maschio Camlock x 1/2\" BSP Femmina Inox)", qta: 1, prezzo: 7.50 },
        { sku: "TEFLON-PTFE", nome: "Nastro PTFE Sigillante MOCA", qta: 1, prezzo: 1.00 }
      ];
      if (porta === "BSP12F") return [
        { sku: "CAM-TYPE-F", nome: "Camlock Tipo F (Maschio Camlock x 1/2\" BSP Maschio Inox)", qta: 1, prezzo: 7.90 },
        { sku: "TEFLON-PTFE", nome: "Nastro PTFE Sigillante MOCA", qta: 1, prezzo: 1.00 }
      ];
      if (porta === "BSP34M") return [
        { sku: "FIT-RED-34F-12M", nome: "Riduzione Inox 3/4\" BSP F a 1/2\" BSP M", qta: 1, prezzo: 5.80 },
        { sku: "CAM-TYPE-A", nome: "Camlock Tipo A (Maschio Camlock x 1/2\" BSP Femmina Inox)", qta: 1, prezzo: 7.50 }
      ];
      if (porta === "TC15") return [
        { sku: "FIT-TC15-CAM-A", nome: "Flangia Tri-Clamp 1.5\" con Innesto Rapido Camlock M", qta: 1, prezzo: 13.50 },
        { sku: "CLAMP-TC15", nome: "Morsetto Tri-Clamp 1.5\" Inox 304", qta: 1, prezzo: 4.50 },
        { sku: "GSK-TC15", nome: "Guarnizione Silicone Tri-Clamp 1.5\"", qta: 1, prezzo: 1.20 }
      ];
      return [
        { sku: `CAM-ADAPT-${porta}`, nome: `Adattatore Camlock Maschio per ${pName}`, qta: 1, prezzo: 9.50 }
      ];
    }

    if (target === "TC15") {
      if (porta === "BSP12M") return [
        { sku: "FIT-TC15-BSP12F", nome: "Adattatore Tri-Clamp 1.5\" a 1/2\" BSP Femmina Inox", qta: 1, prezzo: 11.90 },
        { sku: "TEFLON-PTFE", nome: "Nastro PTFE Sigillante MOCA", qta: 1, prezzo: 1.00 }
      ];
      if (porta === "BSP12F") return [
        { sku: "FIT-TC15-BSP12M", nome: "Adattatore Tri-Clamp 1.5\" a 1/2\" BSP Maschio Inox", qta: 1, prezzo: 11.50 },
        { sku: "TEFLON-PTFE", nome: "Nastro PTFE Sigillante MOCA", qta: 1, prezzo: 1.00 }
      ];
      if (porta === "TC20") return [
        { sku: "FIT-TC20-TC15", nome: "Riduttore Conico Tri-Clamp 2.0\" a 1.5\" Inox", qta: 1, prezzo: 17.90 },
        { sku: "CLAMP-TC20", nome: "Morsetto Tri-Clamp 2.0\" Inox 304", qta: 1, prezzo: 5.50 },
        { sku: "GSK-TC20", nome: "Guarnizione Silicone Tri-Clamp 2.0\"", qta: 1, prezzo: 1.50 }
      ];
      return [
        { sku: `TC15-ADAPT-${porta}`, nome: `Flangia Adattatrice Tri-Clamp 1.5" per ${pName}`, qta: 1, prezzo: 12.50 }
      ];
    }

    if (target === "BARB12") {
      if (porta === "TC15") return [
        { sku: "FIT-TC15-BARB12", nome: "Portagomma Tri-Clamp 1.5\" a 12mm Inox 304", qta: 1, prezzo: 9.90 },
        { sku: "CLAMP-TC15", nome: "Morsetto Tri-Clamp 1.5\" Inox 304", qta: 1, prezzo: 4.50 },
        { sku: "GSK-TC15", nome: "Guarnizione Silicone Tri-Clamp 1.5\"", qta: 1, prezzo: 1.20 }
      ];
      if (porta === "BSP12M") return [
        { sku: "FIT-BARB-12F-12", nome: "Portagomma 1/2\" BSP Femmina a 12mm Inox 304", qta: 1, prezzo: 5.20 },
        { sku: "TEFLON-PTFE", nome: "Nastro PTFE Sigillante MOCA", qta: 1, prezzo: 1.00 }
      ];
      if (porta === "BSP12F") return [
        { sku: "FIT-BARB-12M-12", nome: "Portagomma 1/2\" BSP Maschio a 12mm Inox 304", qta: 1, prezzo: 4.90 },
        { sku: "TEFLON-PTFE", nome: "Nastro PTFE Sigillante MOCA", qta: 1, prezzo: 1.00 }
      ];
      if (porta === "BSP34M") return [
        { sku: "FIT-BARB-34F-12", nome: "Portagomma 3/4\" BSP Femmina a 12mm Inox 304", qta: 1, prezzo: 6.50 },
        { sku: "TEFLON-PTFE", nome: "Nastro PTFE Sigillante MOCA", qta: 1, prezzo: 1.00 }
      ];
      if (porta === "CAM_A") return [
        { sku: "CAM-TYPE-C", nome: "Camlock Tipo C Femmina x Portagomma 12mm Inox", qta: 1, prezzo: 10.90 }
      ];
      return [
        { sku: `BARB12-ADAPT-${porta}`, nome: `Portagomma Inox 12mm per ${pName}`, qta: 1, prezzo: 6.90 }
      ];
    }

    return [];
  }

  function mergeItems(list) {
    const map = {};
    for (const item of list) {
      if (!map[item.sku]) {
        map[item.sku] = { ...item };
      } else {
        map[item.sku].qta += item.qta;
      }
    }
    const items = Object.values(map);
    const totale = Number(items.reduce((acc, p) => acc + p.prezzo * p.qta, 0).toFixed(2));
    return { items, totale };
  }

  /**
   * Genera le 4 opzioni di collegamento suggerite tra portaA e portaB
   * tenendo conto della distanza reale 3D (in metri).
   */
  function suggestOptions(nodoA, nodoB, distanceMeters = 1.5) {
    const nomeA = (PORTS[nodoA] && PORTS[nodoA].nome) || nodoA;
    const nomeB = (PORTS[nodoB] && PORTS[nodoB].nome) || nodoB;
    const hoseLen = Math.max(0.5, Number((distanceMeters * 1.15).toFixed(1)));
    const hosePrice = Number((hoseLen * 5.20).toFixed(2));

    // 1. Raccordo Rapido Camlock Inox + Tubo Silicone
    const rawCam = [
      ...getAdaptersTo(nodoA, "CAM_A"),
      ...getAdaptersTo(nodoB, "CAM_A"),
      { sku: "CAM-TYPE-C", nome: "Accoppiatore Rapido Camlock Tipo C Femmina x Portagomma 12mm Inox", qta: 2, prezzo: 10.90 },
      { sku: `TUBO-SIL-${Math.round(hoseLen * 10)}`, nome: `Tubo Silicone Alimentare Platinum 12x18mm (${hoseLen} m)`, qta: 1, prezzo: hosePrice },
      { sku: "FASCETTA-W4-12", nome: "Fascetta Stringitubo Inox W4 (12-22mm)", qta: 2, prezzo: 1.20 }
    ];
    const camMerged = mergeItems(rawCam);

    // 2. Clamp Sanitario Tri-Clamp 1.5" + Guarnizione
    const rawTc = [
      ...getAdaptersTo(nodoA, "TC15"),
      ...getAdaptersTo(nodoB, "TC15"),
      { sku: "FIT-TC15-BARB12", nome: "Portagomma Sanitario Tri-Clamp 1.5\" a 12mm Inox 304", qta: 2, prezzo: 9.90 },
      { sku: "CLAMP-TC15", nome: "Morsetto Tri-Clamp 1.5\" ad aletta Inox 304", qta: 2, prezzo: 4.50 },
      { sku: "GSK-TC15", nome: "Guarnizione Silicone Alimentare Tri-Clamp 1.5\"", qta: 2, prezzo: 1.20 },
      { sku: `TUBO-SIL-${Math.round(hoseLen * 10)}`, nome: `Tubo Silicone Alimentare Platinum 12x18mm (${hoseLen} m)`, qta: 1, prezzo: hosePrice },
      { sku: "FASCETTA-W4-12", nome: "Fascetta Stringitubo Inox W4 (12-22mm)", qta: 2, prezzo: 1.20 }
    ];
    const tcMerged = mergeItems(rawTc);

    // 3. Tubo con Portagomma e Fascetta Inox (Economico)
    const rawBarb = [
      ...getAdaptersTo(nodoA, "BARB12"),
      ...getAdaptersTo(nodoB, "BARB12"),
      { sku: `TUBO-SIL-${Math.round(hoseLen * 10)}`, nome: `Tubo Silicone Alimentare Alta Temp 12x18mm (${hoseLen} m)`, qta: 1, prezzo: hosePrice },
      { sku: "FASCETTA-W4-12", nome: "Fascetta Stringitubo a Vite Inox W4 (12-22mm)", qta: 2, prezzo: 1.20 }
    ];
    const barbMerged = mergeItems(rawBarb);

    // 4. Innesto Rapido Push-Fit (John Guest / Duotight)
    const rawJg = [
      { sku: `JG-ADAPT-${nodoA}`, nome: `Innesto Rapido Push-Fit Duotight 8mm per ${nomeA}`, qta: 1, prezzo: 4.50 },
      { sku: `JG-ADAPT-${nodoB}`, nome: `Innesto Rapido Push-Fit Duotight 8mm per ${nomeB}`, qta: 1, prezzo: 4.50 },
      { sku: `TUBO-EVA-${Math.round(hoseLen * 10)}`, nome: `Tubo Semirigido EVABarrier 8mm (${hoseLen} m)`, qta: 1, prezzo: Number((hoseLen * 2.80).toFixed(2)) },
      { sku: "CLIP-JG-8", nome: "Clip Sicurezza Antisfilamento 8mm", qta: 2, prezzo: 0.50 }
    ];
    const jgMerged = mergeItems(rawJg);

    return [
      {
        id: "camlock_rapido",
        titolo: "⚡ Raccordo Rapido Camlock Inox + Tubo Silicone",
        badge: "Consigliato · Sgancio Rapido",
        colore3D: 0xf97316,
        coloreHex: "#f97316",
        descrizione: `Converte entrambi i lati in attacchi rapidi Camlock Inox a leva + ${hoseLen}m di tubo silicone. Sgancio istantaneo in 2 secondi.`,
        pezzi: camMerged.items,
        totale: camMerged.totale,
        lunghezza_m: hoseLen
      },
      {
        id: "triclamp_sanitario",
        titolo: "🏥 Clamp Sanitario Tri-Clamp 1.5\" + Guarnizione",
        badge: "Standard Birrificio · Igiene CIP",
        colore3D: 0x38bdf8,
        coloreHex: "#38bdf8",
        descrizione: `Flange sanitarie Tri-Clamp 1.5" con morsetto a farfalla e guarnizione EPDM/Silicone + ${hoseLen}m di linea flessibile.`,
        pezzi: tcMerged.items,
        totale: tcMerged.totale,
        lunghezza_m: hoseLen
      },
      {
        id: "tubo_fascetta",
        titolo: "🔧 Portagomma + Tubo con Fascetta Stringitubo Inox",
        badge: "Più Economico · Universale",
        colore3D: 0x10b981,
        coloreHex: "#10b981",
        descrizione: `Portagomma Inox da 12mm + ${hoseLen}m di tubo silicone alimentare bloccato con 2 fascette stringitubo Inox W4.`,
        pezzi: barbMerged.items,
        totale: barbMerged.totale,
        lunghezza_m: hoseLen
      },
      {
        id: "pushfit_duotight",
        titolo: "🔌 Innesto Rapido Push-Fit (John Guest / Duotight)",
        badge: "Acqua / Gas / Linea Fredda",
        colore3D: 0xa855f7,
        coloreHex: "#a855f7",
        descrizione: `Innesti rapidi a pressione Duotight/John Guest 8mm con doppio O-ring e ${hoseLen}m di tubo EVABarrier.`,
        pezzi: jgMerged.items,
        totale: jgMerged.totale,
        lunghezza_m: hoseLen
      }
    ];
  }

  function solve(nodoA, nodoB, distanceMeters = 1.5) {
    if (!PORTS[nodoA] || !PORTS[nodoB]) return { error: "Porta non valida" };
    const opts = suggestOptions(nodoA, nodoB, distanceMeters);
    const best = opts[0];
    return {
      percorso: [nodoA, "CAMLOCK", nodoB],
      pezzi: best.pezzi,
      totale: best.totale,
      desc: best.descrizione,
      opzioni: opts
    };
  }

  /**
   * Parser intelligente per creare/importare qualsiasi pezzo dal Web (da URL o descrizione testuale)
   */
  function parseWebPart(inputUrlOrName, overrides = {}) {
    const raw = (inputUrlOrName || "").trim();
    const low = raw.toLowerCase();

    // Estrai nome leggibile se l'utente ha incollato un URL (es. https://www.polsinelli.it/pentola-inox-75l-P123.htm)
    let cleanName = overrides.nome || raw;
    let sourceDomain = "Web Custom";
    if (raw.startsWith("http://") || raw.startsWith("https://") || raw.includes("www.")) {
      try {
        const u = new URL(raw.startsWith("http") ? raw : "https://" + raw);
        sourceDomain = u.hostname.replace("www.", "");
        const slug = u.pathname.split("/").filter(Boolean).pop() || "componente-web";
        if (!overrides.nome) {
          cleanName = slug
            .replace(/\.(html?|php|asp)$/i, "")
            .replace(/[-_]+/g, " ")
            .replace(/\b\w/g, c => c.toUpperCase());
        }
      } catch (e) {
        sourceDomain = "Catalogo Web";
      }
    }

    // Rileva automaticamente categoria e dimensioni dal testo/URL se non specificate
    let cat = overrides.categoria || "kettle";
    if (!overrides.categoria) {
      if (low.includes("pompa") || low.includes("pump") || low.includes("novax") || low.includes("riptide") || low.includes("mp-15")) cat = "pump";
      else if (low.includes("ferment") || low.includes("conic") || low.includes("unitank") || low.includes("fermzilla")) cat = "fermenter";
      else if (low.includes("scambiatore") || low.includes("piastre") || low.includes("plate") || low.includes("chiller")) cat = "chiller";
      else if (low.includes("controflusso") || low.includes("counterflow") || low.includes("serpentina")) cat = "counterflow";
      else if (low.includes("rims") || low.includes("herms") || low.includes("resistenza")) cat = "rims";
      else if (low.includes("filtro") || low.includes("filter") || low.includes("hop") || low.includes("bazooka")) cat = "filter";
      else if (low.includes("valvola") || low.includes("spia") || low.includes("sight") || low.includes("rubinetto")) cat = "valve";
      else if (low.includes("brewmonk") || low.includes("grainfather") || low.includes("brewzilla") || low.includes("braumeister")) cat = "all_in_one";
    }

    // Estrai litraggio se presente nel testo (es. "75L", "100 litri")
    let cap = Number(overrides.capacita_l) || 50;
    const matchLitri = low.match(/(\d{1,4})\s*(l|lt|litri|gal)/i);
    if (matchLitri && !overrides.capacita_l) {
      cap = parseInt(matchLitri[1], 10);
      if (matchLitri[2].toLowerCase().startsWith("gal")) cap = Math.round(cap * 3.785);
    }

    const p1Std = overrides.port1Std || (low.includes("tri-clamp") || low.includes("tc") ? "TC15" : "BSP12M");
    const p2Std = overrides.port2Std || p1Std;
    const price = Number(overrides.prezzo) || (cat === "pump" ? 85 : cat === "chiller" ? 95 : cat === "valve" ? 45 : 190);

    // Calcola geometria 3D proporzionata alla categoria e capacità
    let dims = { radius: 0.42, height: 0.92 };
    if (cat === "kettle" || cat === "all_in_one" || cat === "hlt") {
      const scale = Math.max(0.65, Math.min(1.6, Math.cbrt(cap / 50)));
      dims = { radius: Number((0.40 * scale).toFixed(2)), height: Number((0.90 * scale).toFixed(2)) };
    } else if (cat === "fermenter") {
      const scale = Math.max(0.65, Math.min(1.6, Math.cbrt(cap / 55)));
      dims = { radius: Number((0.40 * scale).toFixed(2)), height: Number((1.18 * scale).toFixed(2)) };
    } else if (cat === "pump") {
      dims = { radius: 0.20, height: 0.26 };
    } else if (cat === "chiller" || cat === "counterflow") {
      dims = { radius: 0.26, height: 0.36 };
    } else if (cat === "rims" || cat === "filter" || cat === "valve") {
      dims = { radius: 0.15, height: 0.42 };
    }

    return {
      id: "web-custom-" + Date.now() + "-" + Math.floor(Math.random() * 999),
      sku: "WEB-CUST-" + Math.floor(1000 + Math.random() * 9000),
      nome: cleanName || "Componente Personalizzato dal Web",
      brand: overrides.brand || sourceDomain,
      url: raw.startsWith("http") ? raw : "",
      categoria: cat,
      categoriaLabel: "Importato dal Web",
      prezzo: price,
      capacita_l: cap,
      dims: dims,
      colore: 0xd4d8dd,
      ports: [
        { id: "port_out", label: overrides.port1Label || "Uscita / Scarico Principale", std: p1Std, side: "front_bottom" },
        { id: "port_in", label: overrides.port2Label || "Ingresso / Ritorno", std: p2Std, side: "front_top" }
      ],
      tags: low
    };
  }

  return {
    PORTS,
    WEB_CATALOG,
    suggestOptions,
    solve,
    parseWebPart
  };
})();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = AutoBOM;
}
