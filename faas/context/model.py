from dataclasses import dataclass

from faas.context.platform import FunctionReplicaService, NetworkService, TelemetryService, FunctionDeploymentService, \
    NodeService, TraceService, ZoneService


@dataclass
class PlatformContext:
    deployment_service: FunctionDeploymentService
    network_service: NetworkService
    node_service: NodeService
    replica_service: FunctionReplicaService
    telemetry_service: TelemetryService
    trace_service: TraceService
    zone_service: ZoneService
