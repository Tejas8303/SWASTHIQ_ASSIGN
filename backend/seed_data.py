import os
import json
import glob
from pathlib import Path
from app.db.database import init_db
from app.core.ingestion import parse_and_validate_billing_log
from app.db.repository import save_visits_batch, save_ingestion_audit

def seed_sample_datasets():
    init_db()
    
    # Locate dataset directory
    base_dir = Path(__file__).resolve().parent.parent
    dataset_dir = base_dir / "swasthiq_sample_billing_dataset"
    if not dataset_dir.exists():
        dataset_dir = base_dir.parent / "swasthiq_sample_billing_dataset"
    
    if not dataset_dir.exists():
        print(f"Dataset directory not found at {dataset_dir}")
        return

    pattern = str(dataset_dir / "billing_log_*.json")
    files = sorted(glob.glob(pattern))
    print(f"Found {len(files)} sample dataset files to seed: {files}")

    for file_path in files:
        filename = os.path.basename(file_path)
        # Extract date from filename: billing_log_YYYY-MM-DD.json
        date_part = filename.replace("billing_log_", "").replace(".json", "")
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                raw_data = json.load(f)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                continue

        valid_records, errors = parse_and_validate_billing_log(raw_data)
        clinic_id = valid_records[0].clinic_id if valid_records else "CLN-KNP-014"
        
        print(f"Seeding {filename}: {len(valid_records)} valid records, {len(errors)} rejected rows")
        if valid_records:
            save_visits_batch(valid_records, clinic_id, date_part)

        save_ingestion_audit(
            clinic_id=clinic_id,
            visit_date=date_part,
            filename=filename,
            total_rows=len(raw_data),
            valid_count=len(valid_records),
            rejected_count=len(errors),
            errors=[e.model_dump() for e in errors]
        )

if __name__ == "__main__":
    seed_sample_datasets()
