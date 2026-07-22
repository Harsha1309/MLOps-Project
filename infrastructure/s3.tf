resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "dvc_remote" {
  bucket = "${var.project_name}-dvc-${random_id.bucket_suffix.hex}"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "dvc-remote-storage"
  }
}

resource "aws_s3_bucket_versioning" "dvc_remote" {
  bucket = aws_s3_bucket.dvc_remote.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dvc_remote" {
  bucket = aws_s3_bucket.dvc_remote.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "dvc_remote" {
  bucket = aws_s3_bucket.dvc_remote.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle: expire noncurrent DVC-cached versions after 90 days to control cost
resource "aws_s3_bucket_lifecycle_configuration" "dvc_remote" {
  bucket = aws_s3_bucket.dvc_remote.id

  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}


