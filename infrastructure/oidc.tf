# Registers the EKS cluster's own OIDC issuer as an IAM identity provider.
# This replaces the manual `eksctl utils associate-iam-oidc-provider` step —
# EKS clusters don't do this automatically, but Terraform can create it directly
# once the cluster (and therefore its OIDC issuer) exists.

data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
}
