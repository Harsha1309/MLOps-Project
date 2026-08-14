#!/usr/bin/env bash
# Renders every gitops/**/*.yaml.tmpl into its real .yaml counterpart,
# substituting values pulled live from `terraform output`.
#
# Run this any time the sandbox AWS account changes (or infra is re-applied)
# instead of hand-editing vpcId / account IDs / role ARNs in gitops/.
#
# Usage: scripts/render-gitops.sh
# Requires: terraform (already init'd against infrastructure/), envsubst (gettext)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/infrastructure"

echo "Reading terraform outputs..."
tf_out() { terraform output -raw "$1"; }

export AWS_REGION
export CLUSTER_NAME
export VPC_ID
export ACCOUNT_ID
export ALB_CONTROLLER_ROLE_ARN
export MLFLOW_IRSA_ROLE_ARN
export DVC_IRSA_ROLE_ARN
export MLFLOW_DB_SECRET_ARN
export ECR_REPOSITORY_URL

AWS_REGION="$(tf_out aws_region 2>/dev/null || echo us-west-2)"
CLUSTER_NAME="$(tf_out cluster_name)"
VPC_ID="$(tf_out vpc_id)"
ACCOUNT_ID="$(tf_out account_id)"
ALB_CONTROLLER_ROLE_ARN="$(tf_out alb_controller_role_arn)"
MLFLOW_IRSA_ROLE_ARN="$(tf_out mlflow_irsa_role_arn)"
DVC_IRSA_ROLE_ARN="$(tf_out dvc_irsa_role_arn)"
MLFLOW_DB_SECRET_ARN="$(tf_out mlflow_db_secret_arn)"
ECR_REPOSITORY_URL="$(tf_out ecr_repository_url)"

cd "$REPO_ROOT"

VARS='$AWS_REGION $CLUSTER_NAME $VPC_ID $ACCOUNT_ID $ALB_CONTROLLER_ROLE_ARN $MLFLOW_IRSA_ROLE_ARN $DVC_IRSA_ROLE_ARN $MLFLOW_DB_SECRET_ARN $ECR_REPOSITORY_URL'

find gitops -name '*.yaml.tmpl' | while read -r tmpl; do
  out="${tmpl%.tmpl}"
  envsubst "$VARS" < "$tmpl" > "$out"
  echo "rendered: $out"
done

echo "Done. Diff with 'git diff gitops/' before committing if running locally."
