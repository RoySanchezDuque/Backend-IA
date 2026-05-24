from app.database import SessionLocal
from app.services.ai_service import ai_service

# quick runner to call the new evaluate_dataset method

def main():
    db = SessionLocal()
    try:
        # avoid DB mapper issues locally by providing a simple servers_override
        S = lambda _id, name: type('Srv', (), {'id': _id, 'name': name})
        servers_override = [S(1, 'srv1'), S(2, 'srv2'), S(3, 'srv3')]

        res = ai_service.evaluate_dataset("6G_dataset_augmented.csv", label_column=None, use_heuristic=True, db=None, servers_override=servers_override)
        print("EVALUATION RESULT:\n", res)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    main()
