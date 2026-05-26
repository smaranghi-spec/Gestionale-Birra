import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    user="stefanomaranghi",
    host="localhost"
)
cur = conn.cursor()

nome = "Pale Ale Base"
tipo = "All Grain"
volume_target_litri = 20.0
efficienza = 75.0
versione = 1
note = "Ricetta di prova"

cur.execute("""
    INSERT INTO ricette (nome, tipo, volume_target_litri, efficienza, versione, note)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
""", (nome, tipo, volume_target_litri, efficienza, versione, note))

ricetta_id = cur.fetchone()[0]

ingredienti = [
    ("Malto Pale", "Fermentabile", 4.500, "kg", "Mash", ""),
    ("Cascade", "Luppolo", 30.0, "g", "Boil", ""),
    ("Lievito Ale", "Lievito", 1.0, "pkg", "Fermentazione", "")
]

for ingrediente_nome, categoria, quantita, unita, momento, nota in ingredienti:
    cur.execute("""
        INSERT INTO ingredienti_ricetta
        (ricetta_id, ingrediente_nome, categoria, quantita, unita, momento, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (ricetta_id, ingrediente_nome, categoria, quantita, unita, momento, nota))

conn.commit()
cur.close()
conn.close()

print(f"Ricetta creata con id {ricetta_id}")
