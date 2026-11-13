# Deployment checklist

The step-by-step version, with console paths, is sections 6–8 of the
[Complete Guide](https://claude.ai/artifact/PhjGRDisisMXHirVtyn8Ct). Build staging first, then repeat for
production (`staging` → `prod` in names). Region: `ap-south-1`.

## AWS (once per environment)

- [ ] Root MFA, IAM Identity Center admin user, $150/month budget alert
- [ ] VPC `backend-<env>`: 2 AZs, 2 public + 2 private subnets, 1 NAT gateway
- [ ] Security groups: `alb-sg` (80/443 from anywhere), `app-sg` (8000 from alb-sg), `db-sg` (5432 from app-sg),
      `redis-sg` (6379 from app-sg)
- [ ] RDS PostgreSQL 16, private, `db-sg`, database `app`, encrypted
- [ ] ElastiCache (Redis OSS or Valkey), `cache.t4g.micro`, private subnets, `redis-sg`, encryption in transit on
- [ ] S3 `backend-<env>-files` (Block Public Access on, versioning on) + CloudFront with origin path `/static`
- [ ] SES: verify your sending domain (DKIM records); request production access to leave the sandbox
- [ ] ECR repository `backend` (scan on push) — shared by both environments
- [ ] Secret `backend/<env>` with `DJANGO_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL` (`rediss://<endpoint>:6379/0`),
      `SENTRY_DSN`
- [ ] Roles `backend-<env>-execution` (task execution + read the secret) and `backend-<env>-task`
      (S3 on the bucket, plus `ses:SendEmail` and `ses:SendRawEmail`)
- [ ] ACM certificate, target group (IP, port 8000, health check `/health/`, deregistration delay 30 s),
      ALB (443 → target group, 80 → 443, idle timeout 60 s)
- [ ] Log group `/ecs/backend-<env>`, cluster `backend-<env>`
- [ ] Fill in `deploy/taskdef-<environment>.json` and `deploy/taskdef-<environment>-worker.json`
      (ACCOUNT_ID, secret ARN suffix, domains, bucket, CDN_DOMAIN, from-address). Staging sets
      `API_DOCS_PUBLIC=true`; production leaves it out, so Swagger is staff-only there
- [ ] First image push, register both task definitions, `scripts/run-oneoff.sh` migrate + collectstatic
- [ ] Services: `backend-<env>` (web, behind the ALB) and `backend-<env>-worker` (no load balancer), both in the
      private subnets with `app-sg`; turn on "Deployment circuit breaker" with rollback
- [ ] DNS → ALB; `https://<domain>/health/` returns `{"status": "ok"}`

## GitHub Actions (once)

- [ ] IAM OIDC provider `token.actions.githubusercontent.com`
- [ ] Roles `github-build`, `github-deploy-staging`, `github-deploy-production`
- [ ] Repository variables: `AWS_REGION`, `AWS_BUILD_ROLE_ARN`, `ECR_REPOSITORY`
- [ ] Environments `staging` and `production` with `AWS_REGION`, `AWS_DEPLOY_ROLE_ARN`, `ECS_CLUSTER`,
      `ECS_SERVICE`, `ECS_WORKER_SERVICE`, `SUBNET_IDS`, `SECURITY_GROUP_IDS`; required reviewers on `production`
- [ ] Repository variable `DEPLOY_ENABLED=true`

## How a release runs

`deploy.yml` builds the image once (tag = commit SHA) and calls `_release.yml` for staging, then for production
after approval. `_release.yml` registers the web and worker task definitions, runs `migrate` and `collectstatic`
as a one-off task (a failure stops the release before traffic moves), then rolls out web and worker with
`scripts/deploy-service.sh`. If new tasks keep failing, ECS rolls back by itself and the job fails.

## Housekeeping

Expired JWT refresh tokens pile up in the database. Once a week, run
`scripts/run-oneoff.sh backend-<env> "python manage.py flushexpiredtokens"` (or schedule it with EventBridge
Scheduler).
