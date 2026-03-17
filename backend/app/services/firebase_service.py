import os
import json
from pathlib import Path
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

class FirestoreService:
    _mock_db = {
        "reports": {},
        "comments": [],
        "tasks": []
    }

    def __init__(self):
        print("Initializing FirestoreService in MOCK ONLY mode as requested.")
        self.use_mock = True
        self.db = None
        self.storage_root = Path(os.getenv("LOCAL_STORAGE_DIR", "/Users/E2005/projects/bobfrmmktg/backend/storage"))
        self.reports_dir = self.storage_root / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _report_path(self, week_id):
        safe_week_id = str(week_id).replace("/", "_")
        return self.reports_dir / f"{safe_week_id}.json"

    def save_report(self, week_id, data):
        if self.use_mock:
            self.__class__._mock_db["reports"][week_id] = data
            report_path = self._report_path(week_id)
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=True, indent=2)
            return
        self.reports_collection.document(week_id).set(data)

    def get_report(self, week_id):
        if self.use_mock:
            report_path = self._report_path(week_id)
            if report_path.exists():
                with open(report_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return self.__class__._mock_db["reports"].get(week_id)
        doc = self.reports_collection.document(week_id).get()
        return doc.to_dict() if doc.exists else None

    def get_all_reports(self):
        if self.use_mock:
            reports = []
            for report_file in sorted(self.reports_dir.glob("*.json")):
                with open(report_file, "r", encoding="utf-8") as f:
                    reports.append(json.load(f))
            return reports
        docs = self.reports_collection.stream()
        return [doc.to_dict() for doc in docs]

    def add_comment(self, comment_data):
        if self.use_mock:
            self.__class__._mock_db["comments"].append(comment_data)
            return
        self.comments_collection.add(comment_data)

    def get_comments(self, report_id):
        if self.use_mock:
            return [c for c in self.__class__._mock_db["comments"] if c.get('report_id') == report_id]
        docs = self.comments_collection.where('report_id', '==', report_id).stream()
        return [doc.to_dict() for doc in docs]

    def add_task(self, task_data):
        if self.use_mock:
            task_data['id'] = str(len(self.__class__._mock_db["tasks"]) + 1)
            self.__class__._mock_db["tasks"].append(task_data)
            return
        self.tasks_collection.add(task_data)

    def sync_auto_todos(self, report_id, todos):
        if self.use_mock:
            # Replace previously generated auto tasks for this report, keep manual tasks intact.
            existing_manual = [
                t for t in self.__class__._mock_db["tasks"]
                if not (t.get("report_id") == report_id and t.get("is_auto_generated"))
            ]
            auto_tasks = []
            for i, todo in enumerate(todos):
                auto_tasks.append({
                    "id": f"auto-{report_id}-{i+1}",
                    "report_id": report_id,
                    "description": f"[{todo.get('severity', 'medium').upper()}] {todo.get('level', 'entity')}: {todo.get('entity', '')} - {todo.get('recommendation', '')}",
                    "is_completed": False,
                    "is_auto_generated": True,
                    "meta": todo,
                })
            self.__class__._mock_db["tasks"] = existing_manual + auto_tasks
            return
        # TODO: Firestore upsert behavior for auto tasks when real DB mode is enabled.

    def get_tasks(self, report_id):
        if self.use_mock:
            return [t for t in self.__class__._mock_db["tasks"] if t.get('report_id') == report_id]
        docs = self.tasks_collection.where('report_id', '==', report_id).stream()
        return [doc.to_dict() for doc in docs]

    def update_task_status(self, task_id, is_completed):
        if self.use_mock:
            for t in self.__class__._mock_db["tasks"]:
                if t.get('id') == task_id:
                    t['is_completed'] = is_completed
            return
        self.tasks_collection.document(task_id).update({'is_completed': is_completed})
