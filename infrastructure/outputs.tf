output "cluster_name" {
  value = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "cluster_version" {
  value = aws_eks_cluster.main.version
}

output "configure_kubectl" {
  description = "Run this command to update your local kubeconfig."
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.main.name}"
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "node_group_status" {
  value = aws_eks_node_group.main.status
}

output "dvc_bucket_name" {
  description = "S3 bucket name to use as the DVC remote"
  value       = aws_s3_bucket.dvc_remote.bucket
}

output "dvc_bucket_arn" {
  value = aws_s3_bucket.dvc_remote.arn
}
output "dvc_irsa_role_arn" {
  value       = var.oidc_provider_arn != "" ? aws_iam_role.dvc_irsa[0].arn : null
  description = "Annotate the tourism-dvc-sa ServiceAccount with this ARN once the cluster exists"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.this.repository_url
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions_ecr.arn
}