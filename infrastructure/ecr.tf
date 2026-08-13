resource "aws_ecr_repository" "this" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

# Keep only the last 10 images to control storage cost
resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# GitHub OIDC provider (skip this resource if it already exists in your account)
# ---------------------------------------------------------------------------
# resource "aws_iam_openid_connect_provider" "github" {
#   url             = "https://token.actions.githubusercontent.com"
#   client_id_list  = ["sts.amazonaws.com"]
#   thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
# }

# # ---------------------------------------------------------------------------
# # IAM role assumed by GitHub Actions via OIDC
# # ---------------------------------------------------------------------------
# data "aws_iam_policy_document" "github_trust" {
#   statement {
#     effect  = "Allow"
#     actions = ["sts:AssumeRoleWithWebIdentity"]

#     principals {
#       type        = "Federated"
#       identifiers = [aws_iam_openid_connect_provider.github.arn]
#     }

#     condition {
#       test     = "StringEquals"
#       variable = "token.actions.githubusercontent.com:aud"
#       values   = ["sts.amazonaws.com"]
#     }

#     condition {
#       test     = "StringLike"
#       variable = "token.actions.githubusercontent.com:sub"
#       values   = ["repo:${var.github_org}/${var.github_repo}:*"]
#     }
#   }
# }

# resource "aws_iam_role" "github_actions_ecr" {
#   name               = "github-actions-ecr-push"
#   assume_role_policy = data.aws_iam_policy_document.github_trust.json
# }

# data "aws_iam_policy_document" "ecr_push" {
#   statement {
#     effect = "Allow"
#     actions = [
#       "ecr:GetAuthorizationToken",
#     ]
#     resources = ["*"]
#   }

#   statement {
#     effect = "Allow"
#     actions = [
#       "ecr:BatchCheckLayerAvailability",
#       "ecr:PutImage",
#       "ecr:InitiateLayerUpload",
#       "ecr:UploadLayerPart",
#       "ecr:CompleteLayerUpload",
#       "ecr:BatchGetImage",
#       "ecr:GetDownloadUrlForLayer",
#     ]
#     resources = [aws_ecr_repository.this.arn]
#   }
# }

# resource "aws_iam_role_policy" "ecr_push" {
#   name   = "ecr-push-policy"
#   role   = aws_iam_role.github_actions_ecr.id
#   policy = data.aws_iam_policy_document.ecr_push.json
# }


# ---------------------------------------------------------------------------
# IAM user for GitHub Actions CI (OIDC blocked by sandbox SCP — using
# long-lived access keys instead)
# ---------------------------------------------------------------------------
resource "aws_iam_user" "github_actions_ci" {
  name = "github-actions-ci"
}

resource "aws_iam_access_key" "github_actions_ci" {
  user = aws_iam_user.github_actions_ci.name
}

data "aws_iam_policy_document" "ci_permissions" {
  statement {
    sid       = "EcrAuth"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "EcrPush"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.this.arn]
  }

  statement {
    sid    = "DvcRemoteBucket"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.dvc_remote.arn}/*"]
  }

  statement {
    sid       = "DvcRemoteBucketList"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.dvc_remote.arn]
  }

  statement {
    sid    = "MlflowArtifactBucket"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.mlflow_artifacts.arn}/*"]
  }

  statement {
    sid       = "MlflowArtifactBucketList"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.mlflow_artifacts.arn]
  }
}

resource "aws_iam_user_policy" "ci_permissions" {
  name   = "github-actions-ci-permissions"
  user   = aws_iam_user.github_actions_ci.name
  policy = data.aws_iam_policy_document.ci_permissions.json
}
