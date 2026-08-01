resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "${var.cluster_name}-mlflow-artifacts"
}

resource "aws_s3_bucket_versioning" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id
  versioning_configuration { status = "Enabled" }
}