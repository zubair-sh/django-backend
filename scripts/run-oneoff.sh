#!/usr/bin/env bash
# Run a one-off command (migrate, collectstatic, createsuperuser, ...) as an ECS task and wait for it.
#
#   ECS_CLUSTER=backend-staging SUBNET_IDS=subnet-a,subnet-b SECURITY_GROUP_IDS=sg-123 \
#     scripts/run-oneoff.sh backend-staging "python manage.py migrate --noinput"
#
# Arg 1: task definition (family, family:revision, or full ARN). Arg 2: shell command.
# Exits non-zero if the command fails, so CI stops before any traffic moves.
set -euo pipefail

TASK_DEFINITION="${1:?usage: run-oneoff.sh <task-definition> <command>}"
COMMAND="${2:?usage: run-oneoff.sh <task-definition> <command>}"
: "${ECS_CLUSTER:?set ECS_CLUSTER}"
: "${SUBNET_IDS:?set SUBNET_IDS (comma-separated private subnets)}"
: "${SECURITY_GROUP_IDS:?set SECURITY_GROUP_IDS (app-sg)}"
CONTAINER_NAME="${CONTAINER_NAME:-web}"

overrides=$(python3 -c 'import json,sys; print(json.dumps({"containerOverrides":[{"name":sys.argv[1],"command":["sh","-c",sys.argv[2]]}]}))' \
  "$CONTAINER_NAME" "$COMMAND")

echo "Starting one-off task on $ECS_CLUSTER: $COMMAND"
task_arn=$(aws ecs run-task \
  --cluster "$ECS_CLUSTER" \
  --task-definition "$TASK_DEFINITION" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SECURITY_GROUP_IDS],assignPublicIp=DISABLED}" \
  --overrides "$overrides" \
  --query 'tasks[0].taskArn' --output text)

if [[ -z "$task_arn" || "$task_arn" == "None" ]]; then
  echo "Failed to start the task" >&2
  exit 1
fi
echo "Task: $task_arn (logs: CloudWatch, stream prefix ecs/$CONTAINER_NAME)"

aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER" --tasks "$task_arn"

read -r exit_code reason < <(aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$task_arn" \
  --query "tasks[0].[containers[?name=='$CONTAINER_NAME'] | [0].exitCode, stoppedReason]" --output text)

if [[ "$exit_code" != "0" ]]; then
  echo "One-off task failed (exit code: $exit_code, reason: $reason)" >&2
  exit 1
fi
echo "One-off task succeeded."
