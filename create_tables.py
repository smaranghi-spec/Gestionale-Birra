from app.db import Base, engine
import app.models

Base.metadata.create_all(bind=engine)

print("Tabelle create correttamente")
