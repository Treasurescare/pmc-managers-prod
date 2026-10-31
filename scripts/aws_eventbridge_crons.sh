#!/usr/bin/env bash
# PMC Managers — schedule the backend cron endpoints on AWS (EventBridge → API destination).
# Run once in AWS CloudShell (same account/region as the Elastic Beanstalk app):
#   bash aws_eventbridge_crons.sh
# Requires the SSM parameter /pmc/prod/WEBHOOK_CRON_SECRET (same value the app reads as WEBHOOK_CRON_SECRET).
set -euo pipefail

SITE="${SITE:-https://www.pmcmanagers.com}"
REGION="${AWS_REGION:-$(aws configure get region)}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
SECRET="$(aws ssm get-parameter --name /pmc/prod/WEBHOOK_CRON_SECRET --with-decryption --query Parameter.Value --output text)"
CONN=pmc-cron-connection
ROLE=pmc-eventbridge-cron-role

echo "Region $REGION · account $ACCOUNT · site $SITE"

if ! aws events describe-connection --name "$CONN" >/dev/null 2>&1; then
  aws events create-connection --name "$CONN" --authorization-type API_KEY \
    --auth-parameters "{\"ApiKeyAuthParameters\":{\"ApiKeyName\":\"Authorization\",\"ApiKeyValue\":\"Bearer ${SECRET}\"}}" >/dev/null
else
  aws events update-connection --name "$CONN" --authorization-type API_KEY \
    --auth-parameters "{\"ApiKeyAuthParameters\":{\"ApiKeyName\":\"Authorization\",\"ApiKeyValue\":\"Bearer ${SECRET}\"}}" >/dev/null
fi
CONN_ARN="$(aws events describe-connection --name "$CONN" --query ConnectionArn --output text)"
echo "Waiting for connection to authorise…"; sleep 15

if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" --assume-role-policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"events.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
fi
aws iam put-role-policy --role-name "$ROLE" --policy-name invoke-api-destinations --policy-document \
  "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"events:InvokeApiDestination\",\"Resource\":\"arn:aws:events:${REGION}:${ACCOUNT}:api-destination/pmc-*\"}]}"
ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/${ROLE}"
sleep 10

# name | EventBridge schedule (UTC) | endpoint path
JOBS=(
  "pmc-partner-statements|cron(0 7 1 * ? *)|/api/v1/cron/partner-monthly-statements"
  "pmc-marketing-digest|cron(0 8 ? * MON *)|/api/v1/cron/marketing-weekly-digest"
  "pmc-category-pay-remind|cron(0 9 * * ? *)|/api/v1/cron/category-payment-reminders"
)

for job in "${JOBS[@]}"; do
  IFS='|' read -r NAME SCHED PATHX <<< "$job"
  if aws events describe-api-destination --name "$NAME" >/dev/null 2>&1; then
    aws events update-api-destination --name "$NAME" --connection-arn "$CONN_ARN" \
      --invocation-endpoint "${SITE}${PATHX}" --http-method POST >/dev/null
  else
    aws events create-api-destination --name "$NAME" --connection-arn "$CONN_ARN" \
      --invocation-endpoint "${SITE}${PATHX}" --http-method POST --invocation-rate-limit-per-second 1 >/dev/null
  fi
  DEST_ARN="$(aws events describe-api-destination --name "$NAME" --query ApiDestinationArn --output text)"
  aws events put-rule --name "$NAME" --schedule-expression "$SCHED" --state ENABLED >/dev/null
  aws events put-targets --rule "$NAME" --targets \
    "[{\"Id\":\"1\",\"Arn\":\"${DEST_ARN}\",\"RoleArn\":\"${ROLE_ARN}\",\"Input\":\"{\\\"event\\\":\\\"schedule.triggered\\\",\\\"schedule_id\\\":\\\"${NAME}\\\",\\\"data\\\":null}\"}]" >/dev/null
  echo "✔ $NAME  $SCHED  →  ${SITE}${PATHX}"
done

echo
echo "Test one now (should print {\"ok\":true}):"
echo "  curl -s -X POST ${SITE}/api/v1/cron/partner-monthly-statements -H \"Authorization: Bearer \$(aws ssm get-parameter --name /pmc/prod/WEBHOOK_CRON_SECRET --with-decryption --query Parameter.Value --output text)\""
