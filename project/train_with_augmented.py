import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.services.ai_service import ai_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORIG = "6G_dataset_final.csv"
AUG = "6G_dataset_augmented.csv"

# create augmented dataset by appending out-of-distribution rows
def make_augmented(orig_path=ORIG, out_path=AUG, n_new=100):
    df = pd.read_csv(orig_path)
    # determine last timestamp
    try:
        last_ts = pd.to_datetime(df['Timestamp']).max()
    except Exception:
        last_ts = datetime.utcnow()

    new_rows = []
    for i in range(n_new):
        ts = last_ts + timedelta(seconds=i + 1)
        # out-of-distribution values (much higher traffic and latency, lower throughput)
        traffic = np.random.uniform(50, 120)  # Mbps
        latency = np.random.uniform(200, 800)  # ms
        throughput = np.random.uniform(0.5, 5)  # Mbps
        packet_loss = np.random.uniform(5, 20)  # %
        signal = np.random.uniform(-120, -100)  # dBm (very weak)
        resource = np.random.uniform(5, 30)  # %
        handover = np.random.choice([0, 1])
        new_rows.append({
            'Timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
            'Traffic Volume (Mbps)': round(traffic, 3),
            'Network Latency (ms)': round(latency, 3),
            'Throughput (Mbps)': round(throughput, 3),
            'Packet Loss (%)': round(packet_loss, 3),
            'Signal Strength (dBm)': round(signal, 3),
            'Resource Allocation (%)': round(resource, 3),
            'Handover Success (0/1)': int(handover)
        })

    df_new = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    df_new.to_csv(out_path, index=False)
    logger.info(f"Augmented dataset saved to {out_path} ({len(df_new)} rows)")
    return out_path


def main():
    augmented = make_augmented(n_new=100)
    db = SessionLocal()
    try:
        # provide servers_override like before to avoid DB mapping issues
        S = lambda _id, name: type('Srv', (), {'id': _id, 'name': name})
        servers_override = [S(1, 'srv1'), S(2, 'srv2'), S(3, 'srv3')]

        result = ai_service.train_model(augmented, "random_forest", db, label_column=None, use_heuristic=True, servers_override=servers_override, persist_db=False)
        logger.info(f"Train result: {result}")
        print("TRAIN_RESULT:\n", result)
    except Exception as e:
        logger.exception("Training failed")
    finally:
        db.close()

if __name__ == '__main__':
    main()
