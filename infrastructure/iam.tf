# --- EKS cluster (control plane) role ---

resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# --- Worker node role ---

resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "node_worker_policy" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "node_cni_policy" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "node_ecr_readonly" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}




data "aws_iam_policy_document" "dvc_s3_access" {
  statement {
    sid    = "DvcBucketList"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [aws_s3_bucket.dvc_remote.arn]
  }

  statement {
    sid    = "DvcObjectReadWrite"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.dvc_remote.arn}/*"]
  }
}

resource "aws_iam_policy" "dvc_s3_access" {
  name        = "${var.project_name}-dvc-s3-access"
  description = "Read/write access to the DVC remote S3 bucket"
  policy      = data.aws_iam_policy_document.dvc_s3_access.json
}

# IRSA trust policy. Sourced from the Terraform-managed aws_iam_openid_connect_provider.eks
# (oidc.tf) rather than manually-supplied vars — no second apply pass needed, since both
# the provider and this role are created from the same aws_eks_cluster.main resource.
data "aws_iam_policy_document" "irsa_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.eks.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }
  }
}

resource "aws_iam_role" "dvc_irsa" {
  name               = "${var.project_name}-dvc-irsa"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust.json
}

resource "aws_iam_role_policy_attachment" "dvc_irsa_attach" {
  role       = aws_iam_role.dvc_irsa.name
  policy_arn = aws_iam_policy.dvc_s3_access.arn
}

# --- MLflow S3 (artifact store) access ---

data "aws_iam_policy_document" "mlflow_s3_access" {
  statement {
    sid       = "MlflowBucketList"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.mlflow_artifacts.arn]
  }

  statement {
    sid    = "MlflowObjectReadWrite"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.mlflow_artifacts.arn}/*"]
  }
}

resource "aws_iam_policy" "mlflow_s3_access" {
  name        = "${var.project_name}-mlflow-s3-access"
  description = "Read/write access to the MLflow artifact S3 bucket"
  policy      = data.aws_iam_policy_document.mlflow_s3_access.json
}

# Separate trust policy from dvc_irsa — that one is pinned to a single
# namespace/SA pair via var.namespace/var.service_account_name.
data "aws_iam_policy_document" "mlflow_irsa_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.eks.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:sub"
      values   = ["system:serviceaccount:mlflow:mlflow-sa"]
    }
  }
}

resource "aws_iam_role" "mlflow_irsa" {
  name               = "${var.project_name}-mlflow-irsa"
  assume_role_policy = data.aws_iam_policy_document.mlflow_irsa_trust.json
}

resource "aws_iam_role_policy_attachment" "mlflow_irsa_attach" {
  role       = aws_iam_role.mlflow_irsa.name
  policy_arn = aws_iam_policy.mlflow_s3_access.arn
}


resource "aws_iam_role_policy" "mlflow_secrets_read" {
  name = "mlflow-secretsmanager-read"
  role = aws_iam_role.mlflow_irsa.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = aws_secretsmanager_secret.mlflow_db.arn
    }]
  })
}