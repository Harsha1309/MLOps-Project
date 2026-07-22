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

# IRSA trust policy — only created once the EKS OIDC provider exists.
data "aws_iam_policy_document" "irsa_trust" {
  count = var.oidc_provider_arn != "" ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }
  }
}

resource "aws_iam_role" "dvc_irsa" {
  count              = var.oidc_provider_arn != "" ? 1 : 0
  name               = "${var.project_name}-dvc-irsa"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust[0].json
}

resource "aws_iam_role_policy_attachment" "dvc_irsa_attach" {
  count      = var.oidc_provider_arn != "" ? 1 : 0
  role       = aws_iam_role.dvc_irsa[0].name
  policy_arn = aws_iam_policy.dvc_s3_access.arn
}


