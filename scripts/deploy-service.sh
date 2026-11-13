#!/usr/bin/env bash
# Roll an ECS service onto a task definition and wait for the result.
#
#   scripts/deploy-service.sh <cluster> <service> <task-definition-arn>
#
# Turns on the ECS deployment circuit breaker with rollback: if new tasks keep failing (crash, failed /health/),
# ECS goes back to the previous task definition by itself. This script then exits non-zero, so the workflow shows
# the failure instead of going green on the rolled-back version.
set -euo pipefail

CLUSTER="${1:?usage: deploy-service.sh <cluster> <service> <task-definition-arn>}"
SERVICE="${2:?usage: deploy-service.sh <cluster> <service> <task-definition-arn>}"
TASK_DEFINITION="${3:?usage: deploy-service.sh <cluster> <service> <task-definition-arn>}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-1800}"

deployment_id=$(aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --task-definition "$TASK_DEFINITION" \
  --deployment-configuration "deploymentCircuitBreaker={enable=true,rollback=true},maximumPercent=200,minimumHealthyPercent=100" \
  --query "service.deployments[?status=='PRIMARY'] | [0].id" --output text)
echo "Deploying $TASK_DEFINITION to $SERVICE (deployment $deployment_id)"

deadline=$(( $(date +%s) + TIMEOUT_SECONDS ))
while true; do
  read -r state reason < <(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
    --query "services[0].deployments[?id=='$deployment_id'] | [0].[rolloutState, rolloutStateReason]" --output text)
  case "$state" in
    COMPLETED) echo "Deployment completed."; exit 0 ;;
    FAILED) echo "Deployment failed and was rolled back: $reason" >&2; exit 1 ;;
    None|"") echo "Deployment $deployment_id was replaced or rolled back." >&2; exit 1 ;;
  esac
  if (( $(date +%s) > deadline )); then
    echo "Timed out after ${TIMEOUT_SECONDS}s (state: $state)" >&2
    exit 1
  fi
  echo "  $state..."
  sleep 15
done
