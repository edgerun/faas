zone_label = "ether.edgerun.io/zone"
pod_type_label = "ether.edgerun.io/type"
function_label = "ether.edgerun.io/function"
api_gateway_type_label = 'api-gateway'
function_type_label = 'fn'
client_role_label = 'node-role.kubernetes.io/client'
worker_role_label = 'node-role.kubernetes.io/worker'
controller_role_label = 'node-role.kubernetes.io/controller'
hostname_label = 'kubernetes.io/hostname'

# Pod status constants
pod_not_running = 'Not Running'
pod_running = 'Running'
pod_unknown = "Unknown"
pod_failed = "Failed"
pod_succeeded = "Succeeded"
pod_pending = "Pending"

# Observer events
function_replica_add = 'function-replica-add'
function_replica_delete = 'function-replica-delete'
function_replica_shutdown = 'function-replica-shutdown'
function_replica_scale_up = 'function-replica-scale-up'
function_replica_scale_down = 'function-replica-scale-down'
function_replica_state_change = 'function-replica-state-change'
