import logging
from app.database import SessionLocal
from app.services.ai_service import ai_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    db = SessionLocal()
    try:
        # Provide a lightweight servers_override to avoid DB model import issues
        S = lambda _id, name: type('Srv', (), {'id': _id, 'name': name})
        servers_override = [S(1, 'srv1'), S(2, 'srv2'), S(3, 'srv3')]

        result = ai_service.train_model("6G_dataset_final.csv", "random_forest", db, label_column=None, use_heuristic=True, servers_override=servers_override, persist_db=False)
        logger.info(f"Train result: {result}")
        print("TRAIN_RESULT:\n", result)
    except Exception as e:
        logger.exception("Training failed")
    finally:
        db.close()

if __name__ == "__main__":
    main()
