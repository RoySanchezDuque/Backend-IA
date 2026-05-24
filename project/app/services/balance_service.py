import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.server import Server
from app.models.traffic_log import TrafficLog
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

class BalanceService:
    def __init__(self):
        self.total_system_load = 0.0  # Track total load across all servers
        # Only redistribute a small fraction so the chart shows variation
        self.load_redistribution_rate = 0.1  # 10% of the added load is redistributed

    def assign_server_round_robin(self, db: Session) -> Server:
        servers = db.query(Server).filter(Server.status == "active").all()

        if not servers:
            raise ValueError("No active servers available")

        last_log = db.query(TrafficLog).order_by(TrafficLog.id.desc()).first()

        if last_log and last_log.assigned_server_id:
            current_index = next(
                (i for i, s in enumerate(servers) if s.id == last_log.assigned_server_id),
                -1
            )
            next_index = (current_index + 1) % len(servers)
            return servers[next_index]

        return servers[0]

    def assign_server_least_load(self, db: Session) -> Server:
        servers = db.query(Server).filter(Server.status == "active").order_by(Server.current_load).all()

        if not servers:
            raise ValueError("No active servers available")

        return servers[0]

    def assign_server_ai(self, metrics: dict, db: Session) -> tuple:
        try:
            prediction = ai_service.predict_server(metrics, db)
            server = db.query(Server).filter(Server.id == prediction["recommended_server_id"]).first()

            if not server:
                logger.warning("AI predicted server not found, falling back to least load")
                server = self.assign_server_least_load(db)
                return server, 0.0

            return server, prediction["confidence"]

        except Exception as e:
            logger.warning(f"AI prediction failed: {str(e)}, falling back to least load")
            server = self.assign_server_least_load(db)
            return server, 0.0

    def log_traffic(self, metrics: dict, server: Server, confidence: float, db: Session) -> TrafficLog:
        if server.status != "active":
            logger.warning(f"Server {server.name} is not active, falling back to least load active server")
            server = self.assign_server_least_load(db)

        traffic_log = TrafficLog(
            traffic_volume=metrics["traffic_volume"],
            network_latency=metrics["network_latency"],
            throughput=metrics["throughput"],
            packet_loss=metrics["packet_loss"],
            signal_strength=metrics["signal_strength"],
            resource_allocation=metrics["resource_allocation"],
            handover_success=metrics["handover_success"],
            assigned_server_id=server.id,
            assigned_server_name=server.name,
            prediction_confidence=confidence if confidence > 0 else None
        )

        db.add(traffic_log)

        # Calculate load increment for the assigned server
        load_increment = metrics["traffic_volume"] / server.max_capacity * 100
        server.current_load = min(server.current_load + load_increment, 100.0)
        
        # Redistribute load from other servers to balance
        self._redistribute_load(server, load_increment, db)
        
        server.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(traffic_log)

        logger.info(f"Traffic logged: ID={traffic_log.id}, Server={server.name}, Load={server.current_load:.2f}%")

        return traffic_log

    def _redistribute_load(self, assigned_server: Server, load_added: float, db: Session):
        """Redistribute load from other servers when one receives new traffic"""
        all_servers = db.query(Server).filter(Server.status == "active").all()
        
        if len(all_servers) <= 1:
            return  # No redistribution needed with only one server
        
        # Other servers (not the one receiving traffic)
        other_servers = [s for s in all_servers if s.id != assigned_server.id]
        
        # Calculate how much load to remove from other servers
        load_to_redistribute = load_added * self.load_redistribution_rate
        load_per_server = load_to_redistribute / len(other_servers)
        
        for server in other_servers:
            # Reduce load proportionally, but don't go below 0
            reduction = min(server.current_load, load_per_server)
            server.current_load = max(0, server.current_load - reduction)
            logger.info(f"Redistributed load: {server.name} reduced by {reduction:.2f}% (now at {server.current_load:.2f}%)")

    def _apply_load_decay(self, server: Server, db: Session):
        """No longer needed - replaced by redistribution"""
        pass

    def get_server_status(self, db: Session):
        servers = db.query(Server).all()
        return [{
            "id": s.id,
            "name": s.name,
            "ip_address": s.ip_address,
            "status": s.status,
            "current_load": round(s.current_load, 2),
            "max_capacity": s.max_capacity,
            "load_percentage": round((s.current_load / s.max_capacity * 100), 2) if s.max_capacity > 0 else 0,
            "updated_at": s.updated_at.isoformat()
        } for s in servers]

    def get_traffic_logs(self, db: Session, limit: int = 100, offset: int = 0):
        logs = db.query(TrafficLog).order_by(TrafficLog.timestamp.desc()).offset(offset).limit(limit).all()
        total = db.query(TrafficLog).count()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": logs
        }

balance_service = BalanceService()
