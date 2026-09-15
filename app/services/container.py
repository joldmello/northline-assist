"""Services: a single container so routes get all business logic from one place."""
from __future__ import annotations

from app.database.store import Database
from app.services.case_service import CaseService
from app.services.conversation_service import ConversationService
from app.services.coverage_service import CoverageService
from app.services.dispatch_service import DispatchService
from app.services.llm_service import LLMService
from app.services.notify_service import NotifyService


class Services:
    def __init__(self, db: Database):
        self.db = db
        self.llm = LLMService()
        self.conversation = ConversationService(self.llm)
        self.coverage = CoverageService(self.llm)
        self.dispatch = DispatchService(db)
        self.notify = NotifyService(db)
        self.cases = CaseService(
            db,
            conversation=self.conversation,
            coverage=self.coverage,
            dispatch=self.dispatch,
            notify=self.notify,
        )
