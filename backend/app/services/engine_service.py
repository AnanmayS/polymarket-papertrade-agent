"""Workflow orchestration across scanner, signals, risk, execution, and settlement."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.analytics_service import AnalyticsService
from app.services.execution_service import PaperExecutionService
from app.services.risk_service import RiskService
from app.services.scanner_service import ScannerService
from app.services.settlement_service import SettlementService
from app.services.signal_service import SignalService


class EngineService:
    """Coordinates end-to-end paper trading workflows."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def run_scan(self):
        return ScannerService(self.session, self.settings).run()

    def run_signals(self, mode: str | None = None):
        result = SignalService(self.session, self.settings).run(mode=mode)
        risk_result = RiskService(self.session, self.settings).evaluate_signals()
        return result, risk_result

    def run_paper_trades(self):
        result = PaperExecutionService(self.session, self.settings).run()
        AnalyticsService(self.session, self.settings).persist_snapshot()
        return result

    def settle_paper_trades(self):
        result = SettlementService(self.session, self.settings).run()
        AnalyticsService(self.session, self.settings).persist_snapshot()
        return result

    def run_cycle(self):
        scan_result = self.run_scan()
        signal_result, risk_result = self.run_signals()
        trade_result = self.run_paper_trades()
        settlement_result = self.settle_paper_trades()
        return {
            "scan": scan_result,
            "signals": signal_result,
            "risk": risk_result,
            "trades": trade_result,
            "settlement": settlement_result,
        }
