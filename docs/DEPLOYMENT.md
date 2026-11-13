# Deployment checklist

The step-by-step version, with console paths, is sections 6–8 of the
[Complete Guide](https://claude.ai/artifact/PhjGRDisisMXHirVtyn8Ct). Build staging first, then repeat for
production (`staging` → `prod` in names). Region: `ap-south-1`.

## AWS (once per environment)

- [ ] Root MFA, IAM Identity Center admin user, $150/month budget alert
- [ ] VPC `backend-<env>`: 2 AZs, 2 public + 2 private subnets, 1 NAT gateway
- [ ] Security groups: `alb-sg` (80/443 from anywhere), `app-sg` (8000 from alb-sg), `db-sg` (5432 from app-sg)
- [ ] RDS PostgreSQL 16, private, `db-sg`, database `app`, encrypted
- [ ] S3 `backend-<env>-files` (Block Public Access on, versioning on) + CloudFront with origin path `/static`
- [ ] ECR repository `backend` (scan on push) — shared by both environments
- [ ] Secret `backend/<env>` with `DJANGO_SECRET_KEY`, `DATABASE_URL`, `SENTRY_DSN`
- [ ] Roles `backend-<env>-execution` (task execution + read the secret) and `backend-<env>-task` (S3 on the bucket)
- [ ] ACM certificate, target group (IP, port 8000, health check `/health/`), ALB (443 → target group, 80 → 443)
- [ ] Log group `/ecs/backend-<env>`, cluster `backend-<env>`
- [ ] Fill in `deploy/taskdef-<environment>.json` (ACCOUNT_ID, secret ARN suffix, domain, bucket, CDN_DOMAIN)
- [ ] First image push, register task definition, `scripts/run-oneoff.sh` migrate + collectstatic, create service
- [ ] DNS → ALB; `https://<domain>/health/` returns `{"status": "ok"}`

## GitHub Actions (once)

- [ ] IAM OIDC provider `token.actions.githubusercontent.com`
- [ ] Roles `github-build`, `github-deploy-staging`, `github-deploy-production`
- [ ] Repository variables: `AWS_REGION`, `AWS_BUILD_ROLE_ARN`, `ECR_REPOSITORY`
- [ ] Environments `staging` and `production` with `AWS_REGION`, `AWS_DEPLOY_ROLE_ARN`, `ECS_CLUSTER`,
      `ECS_SERVICE`, `SUBNET_IDS`, `SECURITY_GROUP_IDS`; required reviewers on `production`
- [ ] Repository variable `DEPLOY_ENABLED=true`

## How a release runs

`deploy.yml` builds the image once (tag = commit SHA) and calls `_release.yml` for staging, then for production
after approval. `_release.yml` registers the task definition, runs `migrate` and `collectstatic` as a one-off
task (a failure stops the release before traffic moves), then updates the service and waits for it to be stable.
