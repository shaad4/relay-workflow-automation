
#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# Relay — GitHub Codespaces Development Startup
# ============================================================
# Development-only workaround for Docker legacy/nftables
# firewall conflicts. NOT intended for production.
#
# Usage:
#   ./scripts/dev-up.sh
# ============================================================

cd "$(dirname "$0")/.."

NETWORK="relay-workflow-automation_default"
KAFKA_CONTAINER="relay-kafka"
KAFKA_TOPIC="workflow.triggered"

echo "========================================"
echo " Starting Relay Development Environment"
echo "========================================"

# ------------------------------------------------------------
# 1. Start infrastructure
# ------------------------------------------------------------

echo "[1/8] Starting PostgreSQL and Kafka..."

docker compose up -d \
  auth-postgres \
  workflow-postgres \
  integration-postgres \
  action-postgres \
  execution-postgres \
  kafka

# ------------------------------------------------------------
# 2. Detect Docker bridge
# ------------------------------------------------------------

echo "[2/8] Detecting Docker network..."

NETWORK_ID=$(docker network inspect \
  -f '{{.Id}}' "$NETWORK")

BRIDGE="br-${NETWORK_ID:0:12}"

SUBNET=$(docker network inspect \
  -f '{{(index .IPAM.Config 0).Subnet}}' "$NETWORK")

if ! ip link show "$BRIDGE" >/dev/null 2>&1; then
  echo "ERROR: Docker bridge $BRIDGE not found"
  exit 1
fi

echo "Bridge: $BRIDGE"
echo "Subnet: $SUBNET"

# ------------------------------------------------------------
# 3. Configure Codespaces firewall
# ------------------------------------------------------------

echo "[3/8] Applying Docker networking workaround..."

add_rule() {
  local table="$1"
  local chain="$2"
  shift 2

  if ! sudo iptables-legacy -t "$table" \
    -C "$chain" "$@" 2>/dev/null; then
    sudo iptables-legacy -t "$table" \
      -I "$chain" 1 "$@"
  fi
}

# Allow container-to-container traffic.
add_rule filter FORWARD \
  -i "$BRIDGE" -o "$BRIDGE" \
  -j ACCEPT

# Allow outbound traffic from containers.
add_rule filter FORWARD \
  -i "$BRIDGE" ! -o "$BRIDGE" \
  -j ACCEPT

# Allow established return traffic.
add_rule filter FORWARD \
  -o "$BRIDGE" \
  -m conntrack --ctstate RELATED,ESTABLISHED \
  -j ACCEPT

# NAT for outbound connections.
add_rule nat POSTROUTING \
  -s "$SUBNET" ! -o "$BRIDGE" \
  -j MASQUERADE

echo "Docker firewall rules configured."

# ------------------------------------------------------------
# 4. Wait for Kafka
# ------------------------------------------------------------

echo "[4/8] Waiting for Kafka..."

KAFKA_READY=false

for attempt in $(seq 1 30); do
  STATUS=$(docker inspect \
    -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' \
    "$KAFKA_CONTAINER")

  if [ "$STATUS" = "healthy" ]; then
    KAFKA_READY=true
    break
  fi

  sleep 2
done

if [ "$KAFKA_READY" != "true" ]; then
  echo "ERROR: Kafka did not become healthy."
  exit 1
fi

echo "Kafka is healthy."

# ------------------------------------------------------------
# 5. Initialize Kafka topics
# ------------------------------------------------------------

echo "[5/8] Ensuring Kafka topics exist..."

docker exec "$KAFKA_CONTAINER" \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create \
  --if-not-exists \
  --topic "$KAFKA_TOPIC" \
  --partitions 1 \
  --replication-factor 1

# Verify topic metadata is available before starting consumers.
docker exec "$KAFKA_CONTAINER" \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic "$KAFKA_TOPIC"

echo "Kafka topic $KAFKA_TOPIC is ready."

# ------------------------------------------------------------
# 6. Start application services
# ------------------------------------------------------------

echo "[6/8] Starting Relay application services..."

docker compose up -d

# ------------------------------------------------------------
# 7. Wait for application readiness
# ------------------------------------------------------------

echo "[7/8] Waiting for service readiness..."

wait_for_http() {
  local name="$1"
  local host="$2"

  echo "Waiting for $name..."

  for attempt in $(seq 1 30); do

    if docker compose exec -T api-gateway \
      python -c "
import httpx
response = httpx.get('http://${host}:8000/docs', timeout=3)
response.raise_for_status()
" >/dev/null 2>&1; then

      echo "$name: READY"
      return 0
    fi

    sleep 2
  done

  echo "ERROR: $name did not become ready."
  return 1
}

wait_for_http "Auth Service" "auth-service"
wait_for_http "Workflow Service" "workflow-service"
wait_for_http "Integration Service" "integration-service"
wait_for_http "Action Service" "action-service"
wait_for_http "Execution Service" "execution-service"

# ------------------------------------------------------------
# 8. Verify network connectivity
# ------------------------------------------------------------

echo "[8/8] Verifying network connectivity..."

# Kafka TCP connectivity
docker compose exec -T api-gateway python -c '
import socket
with socket.create_connection(("kafka", 9092), 5):
    print("Kafka TCP: OK")
'

# Outbound internet connectivity
docker compose exec -T auth-service python -c '
import socket
with socket.create_connection(("8.8.8.8", 443), 5):
    print("Outbound Internet TCP: OK")
'

# External DNS resolution
docker compose exec -T auth-service python -c '
import socket
print("External DNS: OK (" + socket.gethostbyname("smtp.gmail.com") + ")")
'

echo ""
echo "========================================"
echo " Relay Container Status"
echo "========================================"

docker compose ps

echo ""
echo "========================================"
echo " Relay Development Environment Ready"
echo "========================================"
echo "API Gateway: http://localhost:8001"
echo "Frontend: cd frontend && npm run dev"
echo "========================================"
